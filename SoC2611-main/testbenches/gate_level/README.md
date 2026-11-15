# Gate-level test bench of SoC2611

These files are the bench as run on 13 and 14 November 2026, with the paths made configurable, the top module
renamed to SoC2611 and the firmware banners renamed; they were not run again in this form.

The firmware images of `quick.c` and `capture.c` built from these files are byte for byte the images of the
published runs. The `smoke.c` image differs only by its shorter banner.

## What the bench does

`tb_chip_gl.sv` simulates the routed netlist of the chip pad to pad. It touches the chip at its pads only:

- the input clock on the clock pad (10 ns by default; the system clock runs at half this rate),
- the reset pad, low from 200 ns to 1.2 us,
- the boot strap on the button pads (value 9: start the image in the external memory),
- a HyperRAM model (`hyperram_model.v`) on the HyperBus pads, loaded with the firmware image,
- a UART receiver on the TX pad, and one byte (`K`) to the RX pad when the firmware asks for it,
- optionally camera frames on the camera pads.

The processor boots from the HyperRAM model, runs the firmware checks and reports on the UART. The bench prints
every UART line, the LED pattern, the memory transactions and a last line `GLSIM VERDICT: PASS` or `FAIL`. PASS
needs the expected summary line, no FAIL line, no error flag in the memory model and never two drivers on a
HyperBus wire at the same time.

The UART bit is 1085 system clock cycles, so one character costs 21,700 input clock cycles. This is why the short
firmware prints only a few characters.

The same firmware suite runs on the RTL with `../cocotb/test_fw.py` and `../vhdl/tb_soc2611_hb.vhd`.

## Tests

| Firmware | What it checks | UART output when it passes | Extra arguments |
|---|---|---|---|
| `quick` | six checks: accelerator ident, external memory, LEDs and buttons, timer, UART receive, accelerator status | `W`, `Q3f`, `P6F0` | none |
| `smoke` | the same six checks with full text (the full suite, 6 of 6) | one `Tnn ... PASS` line per check, `SUMMARY pass=6 fail=0` | none |
| `capture` | a camera frame goes through the camera block into the external memory; the CPU reads it back and compares a checksum with `cam_expect.py` | `C<checksum>`, `P1F0` | `+cam=1000 +expect=1` |

Random start values: `XINIT=unique SEED=<n>` gives every register a random start value (Verilator mode only). The
default `XINIT=0` starts every register at 0. In the mode with delays every flip-flop starts at 0.

Run-time arguments of the bench: `+expect=<n>` (checks that must pass, 6), `+timeout_ms=<ms>` (400),
`+cam=<frames>` (0), `+tick_us=<us>` (a progress line every n microseconds). The scripts pass the image as `+mem=`.

## Two modes

1. Without delays, with Verilator: `run_gl.sh`. It runs on the released netlist alone. Steps: the firmware is
   built and written as a memory file (`ihex2mem.py`); the netlist is unpacked to the work folder;
   `strip_netlist.py --split-pads` removes the cells without logic and splits the bidirectional pads (models in
   `pads_split.v`); `netlist_floating.py` checks that every input pin has a driver (it prints two counts, both 0
   in the published runs); `flatten_netlist.py` writes every standard cell as one line of logic; Verilator
   compiles it with the SRAM models of the PDK; the simulator runs.
2. With the cell and wire delays, with Icarus Verilog: `make_delay_netlist.sh` writes `chip_delay.v`, then
   `run_delay.sh` runs it at a chosen clock period. This needs the delay netlist, and the delay netlist needs the
   routed OpenROAD database and the parasitics (SPEF) of its routed wires from the build flow, plus three scripts
   of the build flow (`write_v_only.tcl`, `sta_chip.tcl`, `sta_write_sdf.tcl`). None of these is in this
   repository, which has the routed netlist only. This mode cannot be rerun from this repository alone.

## Tools

These are the versions of the runs.

- Verilator 5.053 (development build, rev v5.052-640-g8c14ab842) and Icarus Verilog 14.0 (development build
  s20260301-776-g699144553), both from the OSS CAD Suite build of 29 October 2026.
- xPack GNU RISC-V Embedded GCC 15.2.0, prefix `riscv-none-elf-` (`-march=rv32im -mabi=ilp32`).
- Python 3.10 (standard library only).
- g++ 11.4 and GNU make, which Verilator calls to build the simulator.
- GNU coreutils (`realpath -m`, `stdbuf`) and gzip.
- The IHP-Open-PDK with `ihp-sg13cmos5l`, at the commit given in `dependencies/README.md` of this repository.
  The bench reads `sg13cmos5l_stdcell/lib/sg13cmos5l_stdcell_typ_1p20V_25C.lib` and
  `sg13cmos5l_sram/verilog/RM_IHPSG13_*.v`.
- Mode with delays only: OpenROAD (build of 17 February 2026) and the build flow named above.

## Environment variables

The scripts change into the work folder. Give folders as absolute paths.

| Variable | Used by | Meaning |
|---|---|---|
| `OSS_CAD_SUITE` | `run_gl.sh`, `run_delay.sh` | folder with `bin/verilator`, `bin/iverilog`, `bin/vvp` (required) |
| `RISCV_PREFIX` | `run_gl.sh` | prefix of the RISC-V GCC, e.g. `riscv-none-elf-` or `/opt/riscv/bin/riscv-none-elf-` (required) |
| `PDK_ROOT` | all three scripts | folder that contains `ihp-sg13cmos5l/libs.ref` (required) |
| `WORK` | `run_gl.sh`, `make_delay_netlist.sh` | work folder, default `./work/<tag>` |
| `XINIT`, `SEED` | `run_gl.sh` | start values of the registers: `0` (default) or `unique` (random, seed `SEED`, default 1) |
| `JOBS` | `run_gl.sh` | compile jobs of Verilator, default 16 |
| `FW_CFLAGS`, `GPARAMS` | `run_gl.sh` | extra firmware compiler flags; extra Verilator `-G` parameters |
| `RWDS_NS`, `TAG` | `run_delay.sh` | board delay of the memory strobe (default 0); name of the run (default `p<period>`) |
| `DB_DIR`, `FLOW_SCRIPTS`, `OPENROAD`, `SDC` | `make_delay_netlist.sh` | build flow folder with `<name>.odb` and `<name>_routed.spef`; build flow folder with the three scripts; the `openroad` binary; the constraints, e.g. `SoC2611-main/constraints/design.sdc` (all required) |

## Example commands

Without delays, from this folder:

```sh
export OSS_CAD_SUITE=/opt/oss-cad-suite
export RISCV_PREFIX=/opt/riscv/bin/riscv-none-elf-
export PDK_ROOT=/opt/IHP-Open-PDK
NET=../../../release/v.3.0.2/netlist/SoC2611.v.gz

bash run_gl.sh $NET s1 quick                              # build the simulator once, then run the quick suite
bash run_gl.sh $NET s1 smoke run                          # full suite on the same simulator
bash run_gl.sh $NET s1 capture run +cam=1000 +expect=1    # camera capture
XINIT=unique SEED=2 bash run_gl.sh $NET s1 quick          # random start values (a second build, in obj_unique)
```

The log of each run is `work/s1/run_<firmware>_<xinit>_<seed>.log`.

With delays (needs the build flow):

```sh
export DB_DIR=/path/to/routed/database FLOW_SCRIPTS=/path/to/build/flow/scripts OPENROAD=/path/to/openroad
export SDC=$PWD/../../constraints/design.sdc
bash make_delay_netlist.sh <name> s1 typ 8                # writes work/s1_sdf_typ/chip_delay.v
bash run_gl.sh $NET s1 quick run                          # writes the image work/s1/fw/quick.mem
bash run_delay.sh work/s1_sdf_typ work/s1/fw/quick.mem 11.0 all +tick_us=50
```

`run_delay.sh` uses the image that `run_gl.sh` writes in its first step. Called with `run` before the Verilator
simulator exists, `run_gl.sh` writes the image and its run step then ends with exit code 127. The published runs
used the corners slow, typ and fast at input clock periods of 17.1, 11.0 and 7.8 ns, and a control run at 6.0 ns
(typ), which must fail.

## Run times

From the comments of the scripts: one UART character costs 21,700 input clock cycles, and the simulation with
delays advances a few hundred microseconds of chip time per hour.

From the logs of the published runs:

- Verilator build: 33 to 37 minutes with 16 jobs.
- quick: about 2 to 3 minutes (summary at 3.7 ms of chip time).
- smoke: about 65 minutes (summary at 85.8 ms).
- capture: about 22 to 34 minutes (summary at 34.0 ms).
- With delays: under 1 minute for the Icarus compile, then 7 h 20 min to 7 h 28 min per corner for the quick
  suite (summary at 2.9 to 6.4 ms).

## Results

The published results are in `release/v.3.0.0/checks/simulation_summary.txt` of this repository, carried to
v.3.0.2 in `release/v.3.0.2/checks/simulation_summary.txt`.

## Files

| File | Purpose |
|---|---|
| `run_gl.sh` | mode without delays: firmware, netlist preparation, Verilator build, run |
| `tb_chip_gl.sv` | the test bench (pads, HyperRAM model, UART, camera, verdict) |
| `hyperram_model.v` | HyperRAM model (HyperBus 1.0) with protocol checks |
| `pads_split.v` | pad models without tri-state, for the netlist with split pads |
| `strip_netlist.py` | removes the cells without logic and splits the bidirectional pads |
| `netlist_floating.py` | reports input pins without a driver |
| `flatten_netlist.py` | writes every standard cell as logic, from the timing library |
| `ihex2mem.py` | Intel HEX to the memory file of the HyperRAM model |
| `cam_expect.py` | expected checksum of the capture test |
| `make_delay_netlist.sh` | mode with delays: delay netlist from the build flow's database (build flow only) |
| `flatten_delay.py` | writes every standard cell as logic with the delays of an SDF file |
| `run_delay.sh` | mode with delays: Icarus Verilog compile and run |
| `fw/` | firmware: `start.S`, `link.ld`, `quick.c`, `smoke.c`, `capture.c` |
