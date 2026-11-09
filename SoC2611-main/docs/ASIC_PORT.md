# DGrid-SoC1 — RTL preparation for ASIC

Status of the RTL after the ASIC-preparation pass (branch `worktree-asic-rtl-prep`,
October 2026). This document records what in the FPGA-proven design was not
acceptable for an ASIC flow, what was changed, how each change was verified,
and what remains for the chip-level / physical hand-off.

Entry points: [`HW/asic/README.md`](../HW/asic/README.md) (flow files),
`HW/asic/scripts/analyze.sh asic` (GHDL analyse + elaborate gate).

---

## 1. Starting point

The repository held a working Artix-7 build (YOLOv5n at ~500 ms, see README).
A survey of `HW/` found the design to be plain VHDL-93/2008 using only `ieee`
libraries, with the vendor-specific parts already isolated behind a
`HW/platform/{Xilinx,Altera,simulation}` layer. The ASIC blockers were:

| # | Blocker | Where | Severity |
|---|---|---|---|
| 1 | Platform primitives exist only as Xilinx XPM / Altera `altsyncram` / non-synthesizable simulation models | `HW/platform/*` | must fix |
| 2 | Double-pumped memories use the **core clock as a data signal** (`wren <= wren_r and clock`, `... when clock='0'`) and a **transparent latch** (`SYNC_LATCH`) to capture one read result | `util/ramw.vhd`, `util/ramw2.vhd`, `util/ram2r1w.vhd` | must fix |
| 3 | **Internal tri-state buses**: PCORE→cell→core read buses, DP/FPU host read bus, SRAM read bus, APB responses, `soc_base` APB `inout` ports | `pcore.vhd`, `cell.vhd`, `core.vhd`, `dp_fetch.vhd`, `fpu.vhd`, `sram.vhd`, peripherals, `soc_base.vhd` | must fix |
| 4 | **No usable reset**: `clk_reset`/`SDRAM_reset` tied high in the board top, TIMER/GPIO/UART instantiated with `reset_in=>'1'`, VGA/camera have no reset port, ~35 signals rely on bitstream power-up initialisers | `soc_base.vhd`, peripherals, `fp_floor.vhd` | must fix |
| 5 | FP32 multiply/add available only as Xilinx `floating_point` IP (sim model uses `real`) | `HW/platform/*/FP32_*` | must fix (FPU is disabled in the current config, but the RTL must synthesize) |
| 6 | Bidirectional camera I2C data pin driven with `'Z'` inside the core | `camera.vhd` | must fix (pad-ring concern) |
| 7 | Board top is Verilog around Xilinx IP (MIG DDR3 controller, `clk_wiz` MMCM) | `HW/examples/GHRD/main.v` | replaced by an ASIC top |
| 8 | Dead `COMPONENT altsyncram` declarations and `library altera_mf` clauses | 8 core files, 3 simulation models | cosmetic |

Clock structure found: core clock `clk_main` (125 MHz) plus a 2× clock
`clk_x2_main` used **only** by the double-pumped memories (no process in
`HW/src` is clocked by `clock_x2`); independent `clk_camera`, `clk_vga`,
DDR-controller AXI clock, and the camera pixel clock. CDC is done with
`CCD_SYNC` (bit synchronisers) and `afifo` (gray-coded pointers). All core
flops use asynchronous active-low reset (`if reset_in='0' ... elsif
rising_edge`).

---

## 2. What was changed

### 2.1 `HW/platform/asic/` — vendor-free platform primitives (new)

| Entity | Implementation | Notes |
|---|---|---|
| `DPRAM`, `DPRAM_BE` | 1W1R, common clock, 1-cycle registered read, byte lanes | **SRAM macro swap point** (2-port macro, write mask for `_BE`) |
| `SPRAM`, `SPRAM_BE` | 1 port, read-first on write, 1-cycle registered read | swap point (1-port macro) |
| `DPRAM_DUAL_CLOCK` | write on `clock_a`, registered read on `clock_b` | only used by `afifo`; small — flop-based or dual-clock macro |
| `CCD_SYNC` | N-stage (default 3) synchroniser **in the destination clock**, async reset, `async_reg` attribute | the simulation model synchronised in the *source* clock (wrong); the Xilinx one used `xpm_cdc_array_single` |
| `SHIFT_LEFT_L/A`, `SHIFT_RIGHT_L/A` | `numeric_std` shifts | follow the Verilog (`SHIFT.v`) semantics validated on hardware, not the sim model's VHDL `sla` |
| `FP32_MUL`, `FP32_ADDSUB` | IEEE-754 binary32, RNE, DAZ/FTZ, 2 real pipeline stages + `delayv` tail, generic `LATENCY>=2` | matches the Xilinx IP defaults; see §3 for verification |

Timing semantics of the RAM models follow the Xilinx XPM configurations
used by the FPGA build (`READ_LATENCY=1`, `read_first`), i.e. what a real
SRAM macro does. Read-during-write collisions across ports return old data;
the FPGA primitive gives no guarantee there either, so nothing depends on it.

`SYNC_LATCH` has **no** ASIC implementation on purpose: it is no longer
instantiated (see 2.2). The simulation platform keeps it only for the
legacy copies used by the equivalence testbench.

### 2.2 Double-pumped memories without clock-as-data or latches

`ramw`, `ramw2` and `ram2r1w` time-multiplex two accesses per core cycle
on a memory clocked at `clock_x2`. The mux select is now the flag from the
new `HW/src/util/x2_phase.vhd`:

```
t_r toggles on clock_in            (core domain)
s_r <= t_r on clock_x2_in          (x2 domain, ordinary related-clock path)
phase = t_r xor s_r                ('1' in the first half of the core period)
```

and the first-half read result is captured by a `clock_x2` flop enabled by
`phase` instead of a transparent latch. The scheme is independent of the
flops' power-up state (self-aligns after one x2 edge, no reset needed) and
is equally valid on the FPGA. Core-clock-domain behaviour is unchanged:
`HW/asic/scripts/run_tb_ramw.sh` drives the legacy and new versions with
identical random stimulus and compares all outputs at every core clock edge
(the only sampling point in the design) — **19,994 cycles, 0 mismatches**
for all three blocks, and `phase` equals the core clock level after every
x2 edge.

Constraint consequence: `clk_main` must be declared as a `-divide_by 2`
generated clock of `clk_x2` (done in the SDC) so that `t_r -> s_r`, the
muxes and the capture flops are timed as normal synchronous paths.

### 2.3 Tri-state buses → zeros + OR

Every driver that produced `'Z'` when not selected now produces `'0'`, and
each former multi-driver net is an explicit OR of per-source signals:

* `pcore.vhd` → per-PCORE arrays in `cell.vhd` (4 buses, incl. the
  not-generated PCORE slots, which are tied to zero) → OR-reduce;
* `cell.vhd` → per-cell arrays in `core.vhd` (9 buses) → OR-reduce;
* `dp_fetch.vhd` / `fpu.vhd` → `host_dp_readdata` / `host_fpu_readdata`
  OR-ed in `ztachip.vhd` (FPU side is zero when `FPU_ENABLED=FALSE`);
* `sram.vhd` read data (single driver) → zeros;
* APB: `time`, `gpio`, `uart`, `axi_stream_read`, `axi_stream_write` drive
  zeros when not addressed (`time.vhd` had two concurrent drivers on
  `apb_prdata`; merged into one conditional assignment); `soc_base` now has
  one response signal per slave and ORs them together with the external
  response inputs.
* `soc_base` APB ports are now directional: `PADDR/PENABLE/PWRITE/PWDATA`
  out, `PREADY/PRDATA/PSLVERROR` in (tie to `'0'` without an external
  slave). `HW/examples/GHRD/main.v` and `HW/simulation/main.vhd` updated.

The OR form is exact because the enables are one-hot by construction (the
old tri-state nets would have resolved to `'X'` otherwise).

### 2.4 Camera I2C data pin

`camera.vhd` exports `SIOD` + `SIOD_OE`; `soc_base` exports `CAMERA_SDR`
+ `CAMERA_SDR_OE`. The open-drain behaviour is built in the pad
(`main.v`: `assign CAMERA_SDR = CAMERA_SDR_OE ? CAMERA_SDR_O : 1'bz;`).

### 2.5 Reset hygiene

See the reset pass summary at the end of this document (§6) — TIMER/GPIO/UART
on `clk_reset`, VGA and camera given a `reset_in`, signal initialisers
removed, `fp_floor` lookup table made a constant, dead `altsyncram`
declarations removed.

### 2.5b Findings of the GHDL 7 synthesizer (DGSEV2 export)

The Verilog export for the DGSEV2 engine (GHDL 7, stricter than the GHDL 1.0
used for the first gate) surfaced two more classes of ASIC problems, fixed on
the branch (details in `HW/asic/dgse/RUN-ihp-synth-01.md`):

* **reset-only bits** of clocked registers (cleared in the reset branch,
  never written on a clock edge) are inferred as latches: `dp_fetch`
  `new_cmd_is_safe_r` (unused 4th row/column of `safe_mask_t`) and
  `condition_vm{0,1}_busy_r` bit 2, `pcore` `dp_writedata_r` top word,
  `fifow` `data_r` padding — now written every clock;
* **undriven nets** (pad bits of byte-aligned register lanes in
  `iregister_file`/`xregister_file`, `igpio[15:8]` in `soc_base`, never-written
  fields of the `dp_gen` template records) came out as `'bZ` — now driven.

### 2.6 ASIC integration (`HW/asic/`)

* `rtl/dgrid_soc1_asic_top.vhd`: `soc_base` + `clk_div2` (core clock =
  clk_x2/2, guarantees the edge alignment 2.2 relies on) + four
  `reset_sync` instances (clk_main, clk_camera, clk_vga, clk_ddr;
  asynchronous assert, synchronous release). The 128-bit AXI4 master to
  the DDR controller and the APB hook are exported; all pins are
  unidirectional.
* `rtl/config.vhd`: ASIC configuration, **8 PCOREs** (`pid_gen_max_c=8`,
  per the March/April 2026 architecture decision), 128-bit external
  memory bus, FPU off, 125 MHz core clock constant.
* `constraints/dgrid_soc1.sdc`: primary clocks, generated clocks
  (`clk_main`, camera `MCLK`), asynchronous clock groups, reset and CDC
  exceptions, placeholder I/O delays.
* `filelist.f`: ordered compile list (VHDL-2008, library `work`).
* `scripts/analyze.sh`: GHDL analyse + elaborate (+ `ghdl --synth`) gate.
* The Vivado project scripts were updated to read `util/x2_phase.vhd` so
  the FPGA build keeps working with the shared RTL changes.

---

## 3. Verification performed

| Check | Command | Result |
|---|---|---|
| Whole design analyses (VHDL-2008) and `dgrid_soc1_asic_top` elaborates with the ASIC platform, ASIC config and the VexRiscv VHDL | `HW/asic/scripts/analyze.sh asic` | `ok=94 fail=0`, elaborate OK |
| Same with the simulation platform / FPGA config (`soc_base`) | `HW/asic/scripts/analyze.sh simulation` | `ok=92 fail=0`, elaborate OK |
| Double-pumped memories equivalent to legacy | `HW/asic/scripts/run_tb_ramw.sh` | PASS, 19,994 cycles, 0 mismatches |
| FP32 units bit-exact vs. an integer reference (44,979 vectors × LATENCY 2/4/6, random + directed corners) and latch-free under `ghdl --synth` | `HW/asic/scripts/run_tb_fp32.sh` | 134,937/134,937 passed; synth OK |
| `ghdl --synth` of the full top (synthesizability / latch report / memory inference) | `SYNTH=1 HW/asic/scripts/analyze.sh asic` | OK: 166k-line vendor-free netlist, **0 latches**, 54 RAM configurations inferred (§4). Residual notes: 1 unbound output (`dp_core.writemaster3_filler_data_out`, unused), `sram_rid` never assigned in `soc_base` (unused), the rest inside the generated VexRiscv |
| Firmware-level simulation of `dgrid_soc1_asic_top` (boot from DDR model, AXI fabric, APB peripherals, accelerator host bus, reset release) — §7 | `make -C HW/asic/cocotb` (cocotb + GHDL) | firmware `SUMMARY pass=6 fail=0` (T01–T06), cocotb `test_firmware_suite` PASS |

Firmware-level simulation of the whole ASIC top is in §7 (cocotb). Not done:
the YOLO workload itself (needs the ztachip kernel compiler and a very long
simulation); a regression on the FPGA board after this branch is merged
remains the right confidence step for that.

---

## 4. Memory inventory (SRAM macro candidates)

Memories are all behind the `DPRAM*` / `SPRAM*` entities. The
`clock_x2`-clocked ones are the double-pumped register files (2× core
frequency — e.g. 250 MHz for a 125 MHz core — must be within the macro's
range or the core clock lowered).

Counted by walking the hierarchy of the `ghdl --synth` netlist of
`dgrid_soc1_asic_top` (ASIC config: 8 PCOREs, 128-bit external bus, FPU
off). Each row is one SRAM-primitive configuration; "Instances" is the
chip-level count.

| Primitive | Width | Depth | Kbit each | Instances | Kbit total | Clock |
|---|---:|---:|---:|---:|---:|---|
| `DPRAM_BE` | 136 | 512 | 68.0 | 8 | 544.0 | clk_x2 |
| `DPRAM_BE` | 128 | 256 | 32.0 | 16 | 512.0 | clk_x2 |
| `DPRAM_BE` | 64 | 2048 | 128.0 | 2 | 256.0 | clk_main |
| `DPRAM` | 133 | 512 | 66.5 | 3 | 199.5 | clk_main |
| `SPRAM` | 24 | 512 | 12.0 | 16 | 192.0 | clk_main |
| `DPRAM` | 380 | 512 | 190.0 | 1 | 190.0 | clk_main |
| `SPRAM_BE` | 128 | 1024 | 128.0 | 1 | 128.0 | clk_main |
| `DPRAM_BE` | 32 | 4096 | 128.0 | 1 | 128.0 | clk_x2 |
| `DPRAM` | 64 | 512 | 32.0 | 4 | 128.0 | clk_main |
| `DPRAM` | 132 | 512 | 66.0 | 1 | 66.0 | clk_main |
| `DPRAM` | 65 | 1024 | 65.0 | 1 | 65.0 | clk_main |
| `DPRAM` | 64 | 1024 | 64.0 | 1 | 64.0 | clk_main |
| `DPRAM_BE` | 72 | 64 | 4.5 | 8 | 36.0 | clk_x2 |
| `DPRAM` | 58 | 32 | 1.8 | 12 | 21.8 | clk_main |
| `DPRAM` | 73 | 256 | 18.2 | 1 | 18.2 | clk_main |
| `DPRAM` | 67 | 256 | 16.8 | 1 | 16.8 | clk_main |
| `DPRAM` | 132 | 128 | 16.5 | 1 | 16.5 | clk_main |
| `DPRAM` | 58 | 256 | 14.5 | 1 | 14.5 | clk_main |
| `DPRAM` | 388 | 32 | 12.1 | 1 | 12.1 | clk_x2 |
| `DPRAM` | 132 | 32 | 4.1 | 2 | 8.2 | clk_main |
| `DPRAM` | 58 | 64 | 3.6 | 2 | 7.2 | clk_main |
| `DPRAM` | 5 | 256 | 1.2 | 4 | 5.0 | clk_main |
| `DPRAM_DUAL_CLOCK` | 145 | 32 | 4.5 | 1 | 4.5 | clk_a/clk_b |
| `DPRAM` | 35 | 128 | 4.4 | 1 | 4.4 | clk_main |
| `DPRAM_DUAL_CLOCK` | 132 | 32 | 4.1 | 1 | 4.1 | clk_a/clk_b |
| `DPRAM` | 8 | 256 | 2.0 | 2 | 4.0 | clk_main |
| `DPRAM_DUAL_CLOCK` | 58 | 32 | 1.8 | 2 | 3.6 | clk_a/clk_b |
| `DPRAM` | 37 | 32 | 1.2 | 3 | 3.5 | clk_main |
| `DPRAM` | 6 | 256 | 1.5 | 2 | 3.0 | clk_main |
| `DPRAM` | 73 | 32 | 2.3 | 1 | 2.3 | clk_main |
| `DPRAM` | 36 | 32 | 1.1 | 2 | 2.2 | clk_main |
| `DPRAM_DUAL_CLOCK` | 65 | 32 | 2.0 | 1 | 2.0 | clk_a/clk_b |
| `DPRAM_DUAL_CLOCK` | 64 | 32 | 2.0 | 1 | 2.0 | clk_a/clk_b |
| `DPRAM` | 32 | 64 | 2.0 | 1 | 2.0 | clk_main |
| `DPRAM` | 33 | 16 | 0.5 | 3 | 1.5 | clk_main |
| `DPRAM` | 24 | 64 | 1.5 | 1 | 1.5 | clk_main |
| `DPRAM` | 4 | 256 | 1.0 | 1 | 1.0 | clk_main |
| `DPRAM` | 33 | 8 | 0.3 | 3 | 0.8 | clk_main |
| `DPRAM` | 3 | 256 | 0.8 | 1 | 0.8 | clk_main |
| `DPRAM` | 38 | 16 | 0.6 | 1 | 0.6 | clk_main |
| `DPRAM` | 3 | 32 | 0.1 | 4 | 0.4 | clk_main |
| `DPRAM` | 32 | 8 | 0.2 | 1 | 0.2 | clk_main |
| `DPRAM_DUAL_CLOCK` | 3 | 32 | 0.1 | 1 | 0.1 | clk_a/clk_b |
| `DPRAM` | 1 | 8 | 0.0 | 1 | 0.0 | clk_main |
| **accelerator + SoC fabric** | | | | **123** | **2673** (334 KB) | |
| VexRiscv `banks_0` | 32 | 1024 | 32.0 | 1 | 32.0 | clk_main |
| VexRiscv `banks_1` | 32 | 1024 | 32.0 | 1 | 32.0 | clk_main |
| VexRiscv `ways_0_data_symbol0` | 8 | 2048 | 16.0 | 1 | 16.0 | clk_main |
| VexRiscv `ways_0_data_symbol1` | 8 | 2048 | 16.0 | 1 | 16.0 | clk_main |
| VexRiscv `ways_0_data_symbol2` | 8 | 2048 | 16.0 | 1 | 16.0 | clk_main |
| VexRiscv `ways_0_data_symbol3` | 8 | 2048 | 16.0 | 1 | 16.0 | clk_main |
| VexRiscv `ways_0_tags` | 21 | 256 | 5.2 | 1 | 5.2 | clk_main |
| VexRiscv `ways_0_tags` | 22 | 128 | 2.8 | 1 | 2.8 | clk_main |
| VexRiscv `ways_1_tags` | 22 | 128 | 2.8 | 1 | 2.8 | clk_main |
| VexRiscv `regfileplugin_regfile` | 32 | 32 | 1.0 | 1 | 1.0 | clk_main |
| **VexRiscv (caches, regfile, boot RAM)** | | | | | **140** (17 KB) | |
| **chip total** | | | | | **2813 Kbit (352 KB)** | |

Notes for macro selection:

* The `clk_x2` rows are the double-pumped register files (`ramw`,
  `ramw2`, `ram2r1w`): 2-port (1W1R), byte/half-word write mask, 2x core
  frequency. They dominate the bit count (1.2 Mbit) and set the macro
  speed requirement.
* Odd widths (380, 388, 136, 133, 132, 73, 67, 65, 58, 37, 36, 35, 33) are
  data+tag/flag words; tile from standard macro widths or round up.
* Entries of depth <= 32 and the `DPRAM_DUAL_CLOCK` FIFOs are better left as
  flop-based register files (synthesised from the same RTL) than as macros.
* The `SPRAM_BE 128x1024` is the PCORE instruction ROM (`rom.vhd`, loaded at
  run time), `DPRAM_BE 32x4096` the host TCM, `DPRAM_BE 64x2048` the
  accelerator SRAM scratchpad (`sram.vhd`).
* VexRiscv rows are plain arrays inside the generated core (I/D cache data
  and tags, boot RAM banks, register file); map them the same way.

---

## 5. Clock, reset and CDC plan

| Clock | Source | Used by | Relationship |
|---|---|---|---|
| `clk_x2` | PLL (pad `clk_x2_in`) | double-pumped memories, `x2_phase`, capture flops | master |
| `clk_main` | `clk_div2` (`clk_x2`/2) | everything else in the core, APB, UART, GPIO, timer | generated, edge-aligned with `clk_x2` |
| `clk_ddr` | DDR controller | AXI master side of the DDR path (`afifo`/`CCD_SYNC` crossings) | asynchronous |
| `clk_camera` | PLL | camera control, `MCLK` = /2 toggle flop (generated clock) | asynchronous |
| `cam_pclk` | camera sensor pad | camera DVP capture flops → `afifo` | asynchronous |
| `clk_vga` | PLL | VGA timing | asynchronous |

Reset: one `porst_n_in` pad; `reset_sync` per domain. `soc_base.clk_reset`
is the `clk_main`-synchronised reset; `SDRAM_reset` the `clk_ddr` one.
Camera and VGA currently receive `clk_reset` too (asynchronous assert is
fine; release is synchronised to `clk_main`, not to their own clocks — a
pure RTL change to use `rst_cam_n` / `rst_vga_n` from the top once the
peripherals' reset ports are wired through `soc_base`; listed in §9).

CDC inventory: `afifo` (gray pointers through `CCD_SYNC`, data through
`DPRAM_DUAL_CLOCK`) on the DDR, camera and VGA stream paths;
`axi_stream_write` ready flag through a 1-bit `CCD_SYNC`; reset
synchronisers. No other cross-domain paths exist — the SDC declares the
groups asynchronous and bounds the synchroniser inputs.

---

## 6. Reset pass summary

Done in this pass (verified by `analyze.sh` on both platforms):

* `soc_base.vhd`: `TIMER`, `gpio`, `UART` now on `clk_reset` (were tied to
  `'1'`); `vga` and `camera` gained `reset_in` ports (declared in
  `ztachip_pkg.vhd`) wired to `clk_reset`.
* `uart.vhd`: the RX/TX processes did not use `reset_in` at all; they do now.
  `vga.vhd`, `camera.vhd`, `uart.vhd`: all signal initialisers removed, every
  flop has a reset value (the former initialiser value, else zero). Flops
  that had no initialiser and now reset to `'0'`: camera `SIOC` (I2C clock,
  goes high on the first clock after reset), VGA `HS/VS` registers, camera
  `sreg`. Change to idle-high if the board bring-up prefers it.
* `gpio.vhd`, `time.vhd`: `reset_in` added to the process sensitivity lists
  (the body already tested it, so RTL simulation only saw the reset on a
  clock edge).
* `fp_floor.vhd`: `mantissa_mask` table is a `constant`.
* Dead `COMPONENT altsyncram` declarations removed from 7 files;
  `library altera_mf` removed from the simulation RAM models.
* `grep -rnE '^\s*signal\b[^;]*:=' HW/src` is empty. Remaining
  initialisers: two variables inside a pure function in `ztachip_pkg.vhd`
  (fine) and one signal in the generated `HW/riscv/sim/riscv.vhd` (§9).
* Deliberately reset-free: `x2_phase` (`t_r`/`s_r`) and `clk_div2`
  (`div_r`) — correct for any start state, but gate-level simulation needs
  an initial deposit on those three flops (or add a reset port later).
* FPGA board top (`main.v`): `clk_reset`/`SDRAM_reset` are now driven by
  `sys_resetn & MMCM locked` instead of `1'b1`, since the bitstream
  power-up values no longer stand in for a reset.

---

## 7. Firmware-level verification (cocotb)

Same approach as the dg32-max firmware catalogue, on the SoC's own CPU:
`HW/asic/fw/smoke.c` (bare metal, RV32IM, linked at the VexRiscv reset vector
0x4000 in external memory) runs on `dgrid_soc1_asic_top` inside
`HW/asic/tb/tb_dgrid_soc1_fw.vhd` (ASIC top + `HW/simulation/mem128.vhd` DDR
model preloaded from the firmware's Intel HEX). cocotb
(`HW/asic/cocotb/test_fw.py`, GHDL backend) drives reset, push-buttons and the
UART RX byte, decodes UART TX and watches the LEDs. One line per test:

| ID | test | proves | pass criterion |
|---|---|---|---|
| T01 | `ident` | CPU boots from DDR through the AXI fabric; host bus reaches the accelerator; accelerator in reset state | `INSTRUCTION_FIFO_AVAIL` = 127 (`dp_fifo_max_c`), `READ_INDICATION_AVAIL` = 0 |
| T02 | `ddr` | External-memory path (AXI 128-bit, `axi_merge`/`axi_split`, write strobes): LFSR word pattern + complement, half-word and byte writes | 0 mismatches |
| T03 | `gpio` | APB write (LED walk 1,2,4,8,0xA observed by cocotb) and APB read (push-buttons driven to 0x9) | `pb` = 0x9 and LED order |
| T04 | `timer` | TIMER APB slave counts | `time`/`time2` advance |
| T05 | `uart_rx` | UART receive path (cocotb sends `'K'` after the `WAIT` line) | byte = `'K'` |
| T06 | `zta_status` | Remaining accelerator read registers (sync flag, log) | both 0 |
| — | `SUMMARY pass= fail=` | | cocotb asserts 6/6, LED ends at 0 |

Run: `make -C HW/asic/cocotb` (knobs: `FW=<name>`, `FAST_UART=1` for a
sim-only 12.5 MHz `main_clock_c` that makes the UART 10x faster,
`SUITE_TIMEOUT_MS`, `COCOTB_TESTCASE`). Reference results, identical for
the real ASIC config (125 MHz `main_clock_c`, 34.1 ms simulated, 69 min
wall under GHDL) and for `FAST_UART=1` (3.4 ms simulated, ~7 min): firmware
`SUMMARY pass=6 fail=0`; T01 `fifo_avail=0x7f`, T02 `mismatches=0`, T03
`pb=0x9` with the LED walk observed in order, T04 `time2` advancing, T05
`byte='K'`, T06 `sync=0 log=0`; cocotb `test_firmware_suite` PASS.
`HW/asic/cocotb/test_debug.py` holds the hierarchy probes (CPU PC/CSRs, UART
FIFO) used while bringing the bench up.

A note for anyone extending the firmware: the accelerator's host read mux
only answers the readable registers (`READ_INDICATION*`, `READ_SYNC`,
`INSTRUCTION_FIFO_AVAIL`, `READ_LOG*`); reading a write-only register such as
`REG_DP_MAX_PCORE` never returns and stalls the CPU (same on the FPGA).

Scope note: this proves boot, fabric, peripherals, reset release and the
accelerator's host interface on the ASIC configuration (8 PCOREs). It does
not run PCORE kernels — that needs the ztachip `.m/.p` compiler
(`SW/compiler`) and the `ztalib` runtime; wiring those into `HW/asic/fw` is
the natural next test (`T07 kernel`).

## 8. DGSEV2 engine on IHP SG13G2

Target flow: `github.com/aravindgp/DGSE` branch `DGSEV2` with `pdk:
ihp-sg13g2`. Project files follow the Dg-KianV layout: `dgse_project.json`
and `config/base.json` at the repo root, notes and the Verilog export script
in `HW/asic/dgse/`. Two facts drive the plan:

1. The engine reads `rtl/*.v|*.sv` only → `HW/asic/dgse/export_verilog.sh`
   (GHDL ≥ 3, `--synth --out=verilog`) must run on the DGSE machine before a
   run; the GHDL 1.0 available here cannot export Verilog.
2. IHP-Open-PDK provides 1P and 2P (1W1R) SRAM macros, the 2P ones up to
   32 wide × 1024 deep. `HW/asic/dgse/plan_macros.py` maps the §4
   inventory onto them: **277 macros, 27.3 mm²** for the 8-PCORE
   configuration, plus ~87 Kbit left in flops — more than 30 mm² of memory
   on SG13G2 before any logic (≈ 36–40 mm² of core with the ≈ 7 mm² of logic).
   IHP has no fixed MPW block size — the commercial SG13G2 MPW is priced per
   mm² and the free open-source runs prefer < 2 mm² — so the full SoC1
   configuration is a budget/eligibility problem and should be scaled down
   (PCORE count / register-file depth) for a first 130 nm test chip. Mapping table and order of work:
   `HW/asic/dgse/README.md`.

First configuration: `clk_x2` 100 MHz / core 50 MHz (half the FPGA numbers),
`skip_firmware` (the engine's PicoRV32 harness is for blocks; §7 is the
firmware test for this SoC).

**Target node is SG13CMOS5L** (IHP quote, open-silicon run 9 Nov 2026): the
CMOS-only variant of SG13G2 in the same IHP-Open-PDK (`PDK=ihp-sg13cmos5l`,
dev branch). Same 84 standard cells with identical areas, same SRAM macro
files (symlink to `sg13g2_sram`; LEFs use Metal1–4 only), but a reduced
backend (M1–M4–TM1: 4 thin + 1 thick metal instead of 5 + 2) and no MIM.
All SG13G2 area/macro numbers in this document transfer; the DGSE platform
needs a CMOS5L entry (tech LEF, 5-layer PDN on Metal4/TopMetal1,
`sg13cmos5l_io` pads). Details: `HW/asic/dgse/RUN-ihp-synth-01.md`.

**Chosen configuration (2026-10-30, revised the same evening): 8-PCORE lean
with camera (video-camera product, VGA off), open source, QFN64, 40 dies,
external HyperRAM, target run 14 Mar 2027; memories on IHP macros through
`HW/platform/ihp` (1W1R on 1P macros time-multiplexed at `clk_x2`, 1W2R on
2P): synthesized 274 macros / 17.7 mm², 903 k std cells, die ≈ 41 mm²
(6.4 mm, QFN64 limit 6.6). Build with `MEM=ihp` / `HW/asic/filelist_ihp.f`;
the 4-PCORE paragraph below is kept as the measured intermediate step.**

**4-PCORE lean (intermediate, 2026-10-30):** The lean knobs are config
constants (`video_enabled_c`, `tcm_depth_c`, `sram_bank_depth_c`,
`dp_data_fifo_depth_c`, `ddr_read_pend_depth_c`, `axi_rdata_fifo_depth_c`,
`dp_instr_fifo_depth_c`; FPGA values unchanged). Measured: 737 k cells,
logic 4.99 mm², 195 macros / 15.3 mm², die ≈ 37 mm² (6.1 mm edge, inside the
6.6 mm QFN64 limit), firmware suite 6/6 PASS. Camera/VGA are absent from the
test chip (`GEN_*VIDEO*` generates in `soc_base.vhd`); the §4 inventory above
is the 8-PCORE one. Pad budget: `HW/asic/dgse/padlist_qfn64.md`; software
consequences: `HW/asic/dgse/lean_sw_notes.md`.

## 9. Open items for the chip-level hand-off

1. **SRAM macros**: done for IHP in `HW/platform/ihp/` (1P time-multiplexed / 2P wrappers, macro models with PDK names, tiler; equivalence TB `HW/asic/scripts/run_tb_ihp_mem.sh`). Open: BIST hookup (BIST ports tied off), dual-clock FIFOs still flops, macro timing at the slow corner in STA.
2. **PLL / clock tree**: `clk_x2`, `clk_camera`, `clk_vga` from a PLL; keep `clk_main` as `clk_x2`/2 (divider flop at the tree root, balanced trees) or a PLL /2 output with the same generated-clock definition.
3. **Main memory**: done — `HW/asic/rtl/hyperbus/` (AXI4 → HyperBus, 2 × HyperRAM, CK = core/2) inside the chip top `HW/asic/rtl/dgrid_soc1_chip_top.vhd`; firmware suite runs through the HyperRAM device model (`make CHIP=hb`). **Boot path done**: the ASIC core (`HW/riscv/asic/riscv.vhd`) resets to 0x0 = TCM; `tcm.vhd` copies the boot ROM (`HW/asic/rtl/boot_rom_pkg.vhd`, generated from `HW/asic/fw/bootrom`, 396 bytes) into the RAM at power-up while holding the CPU; the ROM jumps to 0x4000 when strap `gpio_in(3)` is high, otherwise runs a UART loader (`test_bootrom.py`). Open: HyperBus register-space access (CR0) if a non-default latency is wanted.
4. **Pads**: QFN64 pin set and pad cells in `HW/asic/dgse/padlist_qfn64.md` (45 signal + 19 supply); open-drain camera SDA and the HyperBus DQ/RWDS as `_in/_out/_oe` triples; constraints `HW/asic/constraints/dgrid_soc1_chip.sdc`. Open: JTAG pins, pad-ring instantiation in the DGSE flow.
5. **Per-domain reset release** for camera/VGA (`rst_cam_n`, `rst_vga_n` are already generated in the top).
6. **RISC-V host**: the ASIC build uses `HW/riscv/asic/riscv.vhd` (the sim core with the reset vector moved to 0x0; synchronous reset). The Xilinx variant (`xilinx_jtag/riscv.v`) uses `BSCANE2` and must not be used. **JTAG debug**: requires regenerating the core from `HW/riscv/sim/riscv.scala` with `DebugPlugin` + `JtagBridge` (raw TCK/TMS/TDI/TDO) — needs a Java/sbt toolchain and the VexRiscv sources (not available on the prep machine; pin budget: 4 pins = HyperRAM CS#1 + 3 GPIOs, or 4 supply pins). One signal initialiser remains in the generated VexRiscv file (regenerate with reset-initialised registers or accept as undefined power-up).
7. **Timing**: SDC periods mirror the FPGA (125/250 MHz); re-target with `main_clock_c` (firmware timer/UART constants depend on it) and the I/O budgets.
8. **DFT**: scan insertion (all flops are async-reset D flops — compatible), memory BIST, boundary scan; `x2_phase`/`clk_div2` need the usual scan-mode clock muxing.
9. **Power**: no clock gating / power domains yet; the accelerator's enable structure (`enable_in` per PCORE) is a natural gating point.
10. **FPGA regression** on the board after merging (shared RTL changed: wrappers, buses, resets).
11. **Architecture work (not part of this pass)**: the 3-D tensor cube (`vector_depth_c` 3→6) analysed in April 2026 is a separate change on top of this RTL.
