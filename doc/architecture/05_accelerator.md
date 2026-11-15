# The ztachip accelerator

SoC2611 carries the ztachip AI accelerator next to the VexRiscv CPU. This page shows the inside of the accelerator
as it is built in release v.3.0.2: one cell of four PCOREs with 16 threads each, the data path that moves tensors,
the stream processors, the scratchpad and the three AXI ports. Block names are the names used in the RTL of the
design repository and in the routed netlist of the release.

![Block diagram of the ztachip accelerator: AXI-lite bridge, data path with dp_fetch, dp_gen_core and the dp_source and dp_sink ports, scratchpad, main-memory DMA, and the PCORE array with instr, stream processors, cell 0 with PCORE 0 to 3 and the inside of one PCORE](figures/05_ztachip.svg)

*The accelerator instance soc_i/ztachip_inst: data path on top, PCORE array below, the inside of one PCORE on the right.*

## Configuration of this chip

| Item | Value | Set by |
|---|---|---|
| PCOREs | 4, in one cell: cell 0 with PCORE 0 to 3 | `pid_gen_max_c = 4` in `HW/asic/rtl/config.vhd`, `pid_max_c = 4` per cell in `HW/src/ztachip_pkg.vhd` |
| Threads per PCORE | 16 | `tid_max_c` |
| Data word inside the PCOREs | 12 bits | `register_width_c` |
| Vector | 8 lanes | `vector_depth_c = 3` |
| Accumulator | 32 bits | `accumulator_width_c` |
| VLIW instruction | 128 bits | `instruction_width_c` |
| Instruction memory | 1,024 words of 128 bits | `HW/src/pcore/rom.vhd` |
| Register bank pages per PCORE | 1 | `hart_enabled_c = FALSE` in `HW/asic/rtl/config.vhd` |
| Data-path threads | 2 | `dp_max_thread_c` |
| Scratchpad | 2 banks of 1,024 words of 64 bits, 16 KiB | `sram_bank_depth_c = 13`, `HW/src/top/sram.vhd` |
| Data-path buses | 64 bits: 8 elements of 8 bits | `ddr_data_width_c` |
| Floating point unit | not built | `fpu_enabled_c = FALSE` |

The routed netlist agrees: its PCORE instances are `gen_cell[0]_cell_i/gen_reg[0..3]_gen1_pcore_i`, and no
second cell exists. The cell count follows from `core.vhd`: one cell per started group of four PCOREs.

## Interfaces

| Port | Signals | Width | Connected in the SoC to |
|---|---|---|---|
| Host control | `axilite_*` | 24-bit address, 32-bit data | CPU data bus, accelerator register window at `0x8000_0000` |
| Data master | `axi_*` | 32-bit address, 64-bit data, 4-bit burst length | AXI interconnect (`axi_merge_inst`), then the HyperRAM main memory |
| Scratchpad read port | `axislave_*` | 32-bit address, 32-bit data, read only | a port of the CPU data-bus split (`axi_split_dbus_i`) |

The host registers are listed in `doc/RegisterMap.md` section 3. Register 22, `REG_DP_MAX_PCORE`, is defined in
`ztachip_pkg.vhd`, but no RTL decodes it. The FPU registers 26 to 28 and 31 have no hardware behind them in this
chip, because the FPU is not built: `ztachip.vhd` ties its host read data, wait and busy signals to zero.

## Data path

The data path is `dp_core` (`HW/src/dp/`). It executes the tensor instructions that the CPU writes over the
AXI-lite port. `axilite` turns AXI-lite into the internal host bus.

- `dp_fetch` queues the tensor instructions. Each instruction belongs to one of two hardware threads. Data
  operations go to `dp_gen_core`. Operator execution goes to the PCORE array on the task signals: start address,
  PCORE selection, thread mask.
- `dp_gen_core` holds two `dp_gen` units, so two data operations can run at the same time. They generate the
  addresses of a transfer.
- `dp_source` issues the reads of a transfer and hands the data to the `dp_sink` of the destination, which issues
  the writes. There is one source and one sink per bus.
- Bus 1 reaches the memory inside the PCOREs, bus 2 the scratchpad, bus 3 the main memory through `ddr_rx` (reads)
  and `ddr_tx` (writes). All three buses carry 64 bits.
- The scratchpad, `sram_core`, has two banks of 1,024 words of 64 bits. The CPU can read it directly over the
  scratchpad read port (`axi_ram_read`).

`HardwareDesign.md` describes two register-bank pages per PCORE, one per data-path thread, so that a transfer for
one thread can run while the PCOREs compute for the other. In this chip the second page is not generated:
`register_bank.vhd` builds the second `register_file` only when `hart_enabled_c` is TRUE, and the chip
configuration sets it to FALSE.

## PCORE array

The PCORE array is `core` (`HW/src/pcore/core.vhd`).

- `instr` is the master processor of the array. `instr_fetch` schedules the 16 threads round robin. The `rom`
  holds the VLIW code, 1,024 words of 128 bits, loaded at run time. One instruction is fetched per clock for all
  PCOREs, which run in lock step.
- The VLIW pipeline is 14 clocks deep. Because each pipeline stage holds a different thread, every PCORE completes
  one VLIW instruction per clock.
- The cell groups four PCOREs to ease the fan-out of the buses. With four PCOREs there is one cell.
- Data enter the array as 8-bit elements and are widened to 12 bits, with or without sign. On the way out they are
  cut back to 8 bits (`short2int`, `ushort2int`, `int2short` in `core.vhd`).
- The stream processors map data on the way in and out: eight on the write path and eight on the read path, one
  per vector lane. Each has a lookup table of 512 entries of 24 bits, a 12-bit base and a 12-bit slope. The
  address is the 2-bit stream id and the upper 7 bits of the 12-bit value, and the lower 5 bits interpolate
  between table points (`stream.vhd`). The 2-bit id selects one of four mapping functions. AI code uses them for
  activation functions. A transfer uses the stream processors only when it asks for them; otherwise the data
  bypass them.

## Inside a PCORE

- `instr_decoder2` decodes the 128-bit VLIW instruction. Its MU field drives the vector ALUs, its IMU field the
  integer ALU. Branches are taken by `instr` for all PCOREs at once.
- `instr_dispatch2` moves the operands from the register bank to the ALUs and the results back.
- `register_bank` is the internal memory of the PCORE. All arithmetic works on it directly, without load and store.
  One page holds 256 words of 8 lanes. It gives two reads and one write per clock: the two reads share a 2-port
  macro at the double clock `clk_x2` (`ram2r1w.vhd`). Private data of the 16 threads are interleaved; shared data
  fill from the bottom.
- `alu`, eight of them, one per lane: 12 x 12 bit multiply, add to a 32-bit accumulator, shift, compare against
  zero, and clip the result back to 12 bits.
- `xregister_file` holds the 32-bit accumulators.
- `ialu` with `iregister_file` does the integer work of a VLIW instruction: loop counters, array indexes and
  addresses. It has the registers R0 to R7, 13 bits wide, and VMASK, which switches vector lanes on and off.

## Memories of the accelerator

205 of the 298 SRAM macros of the chip belong to the accelerator. The split per block comes from the instance
names in the routed netlist. The counts per macro type over the whole chip are the ones in
`SoC2611-main/synthesis/inventory.md`. Macro names below are written without the `RM_IHPSG13_` prefix and the
`_c2`, `_c3` and `_bm_bist` suffixes.

| Block | SRAM macros | Count |
|---|---|---:|
| PCORE register bank, `register_file` | 4 x 2P_256x32 per PCORE | 16 |
| PCORE integer registers, `iregister_file` | 4 x 1P_256x32 and 1 x 1P_256x16 per PCORE | 20 |
| PCORE accumulators, `xregister_file` | 8 x 1P_256x32 and 1 x 1P_256x16 per PCORE | 36 |
| Stream processor lookup tables, 16 processors | 16 x 1P_512x16 and 16 x 1P_512x8 | 32 |
| Instruction memory, `instr` rom | 4 x 1P_1024x32 | 4 |
| Scratchpad, `sram_core`, 2 banks | 4 x 1P_1024x32 | 4 |
| `dp_fetch` template memory | 49 x 1P_64x16 | 49 |
| `dp_fetch` instruction FIFO | 12 x 1P_256x32 | 12 |
| `dp_fetch` indication FIFO | 2 x 1P_256x32 and 1 x 1P_256x8 | 3 |
| `dp_sink` data FIFOs, 3 sinks | 18 x 1P_256x32 and 3 x 1P_256x8 | 21 |
| `axilite` write address and data FIFOs | 4 x 1P_64x16 | 4 |
| `ddr_rx` read data and record FIFOs | 3 x 1P_256x32 and 1 x 1P_256x8 | 4 |
| **Accelerator total** | | **205** |

The memories with two accesses per system clock run at the double clock `clk_x2`
(`SoC2611-main/docs/ASIC_PORT.md` section 4). The position of every macro on the die is in
`06_physical.md`.

## Sources

- `SoC2611-main/docs/HardwareDesign.md`: roles of the blocks, threads, pipeline, VLIW format, ALU and stream
  functions.
- `SoC2611-main/docs/ASIC_PORT.md` section 4: double-clocked memories, instruction ROM as `SPRAM_BE`.
- `doc/RegisterMap.md` sections 1, 3 and 4: register window, host registers, chip configuration.
- `SoC2611-main/synthesis/inventory.md`: macro counts per type.
- `release/v.3.0.2/netlist/SoC2611.v.gz`: PCORE and macro instance names.
- Design repository: `HW/asic/rtl/config.vhd`, `HW/src/ztachip_pkg.vhd`, `HW/src/top/ztachip.vhd`,
  `HW/src/top/axilite.vhd`, `HW/src/top/sram_core.vhd`, `HW/src/top/sram.vhd`, `HW/src/top/cell.vhd`,
  `HW/src/dp/dp_core.vhd`, `HW/src/dp/dp.vhd`, `HW/src/dp/dp_fetch.vhd`, `HW/src/dp/dp_gen_core.vhd`,
  `HW/src/dp/dp_sink.vhd`, `HW/src/pcore/core.vhd`, `HW/src/pcore/instr.vhd`, `HW/src/pcore/rom.vhd`,
  `HW/src/pcore/stream.vhd`, `HW/src/pcore/pcore.vhd`, `HW/src/pcore/register_bank.vhd`,
  `HW/src/pcore/register_file.vhd`, `HW/src/pcore/xregister_file.vhd`, `HW/src/ialu/iregister_file.vhd`,
  `HW/src/util/ram2r1w.vhd`, `HW/src/soc/soc_base.vhd`.
