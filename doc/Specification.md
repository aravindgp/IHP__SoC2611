# SoC2611 — Specification

> **Status: release `v.3.0.2` (15 November 2026), the version for fabrication.** Routing is clean, the IHP
> minimum rule set, density and LVS are clean on the released GDS, hold is met at three corners, and the routed
> netlist runs the test firmware in simulation with and without the delays of the routed wires. Readiness: TRL 6
> (`doc/TRL-Mixed-Signal-IP.md`). No silicon has been measured yet; the figures below come from analysis and
> simulation.

## Function
- VexRiscv RISC-V CPU (RV32IM, JTAG debug, I/D caches), boot ROM copy to a tightly-coupled memory, UART loader.
- ztachip AI accelerator: 8 PCOREs (2 cells x 4), 16 threads each, data path, scratchpad SRAM, AXI-lite control
  (register map in `RegisterMap.md`, interfaces in `Interfaces.md`).
- AXI interconnect (lean AXI split/merge), HyperBus memory interface, camera input + video stream writer,
  UART, timer, GPIO, APB bridge. Single main clock with integrated clock gating (2 ICG cells).

## Technology and physical data
| Item | Value |
|---|---|
| Process | IHP SG13CMOS5L (CMOS only, Metal1-4 + TopMetal1), 1.2 V core, 3.3 V IO |
| Die / seal ring | 6600 × 6600 µm, seal ring at the die edge |
| Core | 5920 × 5920 µm (340 µm pad-ring margin) |
| Package | QFN64 (64 pads: 48 signal, 16 supply) |
| Standard cells | ~290k after synthesis (~6.2 mm²), ~335k after P&R |
| SRAM | 298 RM_IHPSG13 macros, 214 KiB, ~12.9 mm² |
| IO | sg13cmos5l_io (IOPadIn / Out4mA / Out16mA / InOut4mA / InOut16mA / supply pads), 70 × 70 µm bondpads |

## Ratings (static timing on the routed wires, release `v.3.0.2`)
| Corner | System clock, maximum | Input clock `clk_x2`, maximum |
|---|---|---|
| slow, 1.08 V, 125 C | 29.4 MHz | 58.8 MHz |
| typical, 1.20 V, 25 C | 45.5 MHz | 91.0 MHz |
| fast, 1.32 V, -40 C | 64.4 MHz | 128.8 MHz |

The slow-corner figure is the one to rate the chip at. The constraints were written for a 100 MHz input clock
(50 MHz system clock), which the chip meets at the fast corner only. Power, supply and operating notes:
`doc/Datasheet.md`.

## Known limits of this revision
- The UART and the millisecond timer are scaled for a 125 MHz system clock: the UART bit rate is the system clock
  divided by 1085, and one timer "millisecond" is 125,000 system clocks (`doc/RegisterMap.md` section 2).
- The CPU trap vector is fixed at `0x8000_0020`, inside the accelerator register window, and `ecall` does not
  trap. Firmware must not raise exceptions (`doc/RegisterMap.md` section 1).
- Slew and load limits of the cell libraries were not part of the timing sign-off. About 1,050 switching nets load
  their driver beyond the library limit (worst slew 13.8 ns at the slow corner), so part of the slow-corner rating
  rests on delays outside the library tables. The simulations with delays pass at all three corners.
