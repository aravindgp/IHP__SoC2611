# SoC2611 v.2.0.0 - release note (11 November 2026, 22:35 UTC)

> **Which GDS to check and to use: the full-fill file.** GitHub does not accept files above 100 MB, and the
> full-fill GDS is 155 MB compressed. It is therefore stored in two parts:
> `cat gds/SoC2611_fullfill.gds.gz.00.part gds/SoC2611_fullfill.gds.gz.01.part > SoC2611_fullfill.gds.gz`
> (sha256 below), and once more as a single file `gds/SoC2611_fullfill.gds.xz`. Every DRC and density result of
> this note is for that file.
> The smaller `gds/SoC2611.gds.gz` has the same routing with the PDK lattice fill only. **It does not pass the
> density rules on its own**: 75 violations (Metal2 global 29.8 % against 35 %, and 74 windows of Metal2, Metal3
> and Metal4 below 25 %), see `checks/density_pdkfill_only.txt`. It is in the release only as a file that fits
> under the size limit; it is not the file to submit to the mask shop.

> **Status: candidate for the submission checks.** Routing is clean, the IHP minimum rule set is clean on the
> filled file of this release (26 rule tables and the GatPoly filler table), density is clean, hold is met with the
> parasitics of the routed wires, and every signal net was traced in the GDS against the netlist. Three limits are
> known and listed below: the speed on the routed wires, the antenna ratios, and LVS, which has not completed on
> this chip.

## What changed since rc3
1. **Timing with the routed wires.** rc3 was timed with parasitics estimated from the placement. This release is
   timed with the resistance and capacitance extracted from every routed wire. On the rc3 routing that showed about
   6,400 endpoints failing hold at the fast corner. Hold repair against the routed wires added 7,205 buffers; hold
   is now met at all three corners on all internal paths.
2. **Speed.** The same timing shows long wires into the SRAM pins (44 nets with more than 5 ns of wire delay).
   The system clock this file supports is 15.0 / 12.7 / 10.0 MHz (fast / typical / slow corner), not the
   50 / 34.6 / 21.7 MHz estimated in rc3. The limiting paths are the half-cycle paths from system-clock flip-flops
   into the SRAM pins on the double-rate clock.
3. **Row filler cells.** The standard-cell rows now carry filler cells (1,074,709 instances).
4. Routing re-closed after the hold repair: 0 violations, no signal net without a wire. No macro and no pad moved.

## State of this release (12 November 2026)

| Item | Result |
|---|---|
| Detailed routing (OpenROAD TritonRoute) | 0 violations, 0 signal nets without a wire |
| Power grid check, VDD and VSS | both pass |
| IHP minimum rule set, deep mode, on the full-fill GDS of this release | 26 of 26 rule tables and the GatPoly filler table completed, 0 violations, see `checks/drc_minimum_fullfill.txt` |
| IHP minimum rule set, deep mode, layout with seal ring, no fill | 23 of 23 rule tables completed, 0 violations |
| Density of the full-fill GDS (Activ, GatPoly, Metal1-4, TopMetal1; global and window rules) | 0 violations, see `density_fullfill.txt` |
| Connectivity of the GDS against the netlist (net trace, see below) | 341,753 signal nets traced, 0 open pins, 0 shorted pins, 0 nets touching a macro without a pin there |
| Hold, internal paths, routed-wire parasitics | met at all three corners: worst slack +0.02 / +0.11 / +0.05 ns (fast / typical / slow) |
| Hold at the SRAM pins, routed-wire parasitics | +0.20 / +0.49 / +0.93 ns (fast / typical / slow) |
| Setup, routed-wire parasitics | system clock 15.0 MHz fast, 12.7 MHz typical, 10.0 MHz slow (the double-rate input clock is twice that) |
| Antenna check (OpenROAD) | 6,129 nets above the ratio limit; not repaired in this file (a copy with 7,213 diodes is in routing closure) |
| LVS (deep) | not completed: all device extractions pass, the hierarchical net extraction did not return in more than 15 hours |

Notes on the checks:
- **Nwell table.** In the minimum rule set all four rules of the Nwell table are switched off (`!PRECHECK_DRC`); the
  table only builds whole-chip connectivity and has nothing to report. It is left out of the table count.
- **Net trace.** For every signal net the metal connected to its first pin is followed in the GDS through
  Metal1 to TopMetal1 and all vias, in all cell levels. A pin of the same net that is not reached is an open, a pin
  of another net inside the traced metal is a short. It is independent of the router's own checks and does not
  replace LVS: devices are not extracted, and the supplies are checked by the power grid check of the router
  database, not in the GDS.
- **Input pins.** Fourteen endpoints behind input pads show negative hold in the report. Six are input pins (SPI
  data in, UART, GPIO) against the placeholder input delay of the constraints; they are sampled by the system clock
  after the clock tree delay, and their timing depends on the board. Eight are the HyperBus data inputs, whose
  constraint models capture of the previous byte; with the on-chip strobe delay the current byte is captured.
- **Speed.** The numbers are for the double-rate clock scheme of this design: the single-port SRAMs do two
  accesses per system clock cycle. The slow-corner figure is the one to plan a board with.
- **Antenna.** The ratios are above the limit of the technology LEF on 6,129 nets. The minimum rule set of the
  precheck does not include the antenna rules. A repaired version exists as a routed copy and replaces this file
  only if its routing closes clean before the deadline.
- **Fill at the die corners.** Fill shapes at the four chamfered corners are removed in both GDS variants.

## Contents
- `gds/SoC2611.gds.gz`: whole file (the one `doc/info.json` points at), seal ring + label, PDK lattice fill only
  (under GitHub's 100 MB limit).
- `gds/SoC2611_fullfill.gds.gz.00.part` and following parts: same routing with PDK fill + top-up fill, density
  clean, the file the minimum rule set was run on; reassemble with `cat` and check the hash below.
- `gds/SoC2611_fullfill.gds.xz`: the same full-fill GDS as one xz file, if it fits under 100 MB.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog (with the hold buffers and
  row filler cells of this release).
- `density_fullfill.txt`: density result of the full-fill GDS.
- `checks/`: DRC table verdicts (filled file and no-fill file), net trace summary, timing with the routed wires,
  antenna summary.

## Source state
Routing of rc3 + hold repair against the routed wires; marker nets and nets without a wire re-routed until both
counts were 0. OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.

## SHA-256
```
282d089b7c6801d0e9839e008a3951e06c6a0f765f863c8b28683e9c48e96333  gds/SoC2611.gds.gz
95975e0fcb83e5392286aebb07a14cd0bb1ad281161c0185b219d7c7488c769e  gds/SoC2611_fullfill.gds.gz.00.part
223b19104f8d04092958b1402d875108801048d6f2e7ae5e63eba5910d405d00  gds/SoC2611_fullfill.gds.gz.01.part
0705fb4cf9bdf73c5cb0cfe3b68c11a71d432a7a4793a259fafdfcb55f3ecffb  gds/SoC2611_fullfill.gds.xz
410174a659188850a732043d2a4dd1eab31545a87689ac145d6c1067c2dba36a  netlist/SoC2611.cdl.gz
b832e1c7bc923bcc765f23fdeeb0c9e6ed89d11e662211c7d0655918af8ec757  netlist/SoC2611.v.gz
fullfill reassembled (cat the .part files): c4fe6e2fec55e63d6c5f504ebc424962c3221f7ff4570858f763c2f1d2b7b553
fullfill uncompressed GDS: ff26e7ae14e0655b7edb4f89d3135c97b8a846bc08a559877c58af26e8299b8a
```
