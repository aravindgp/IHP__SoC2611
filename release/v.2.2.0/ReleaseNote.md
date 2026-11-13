# SoC2611 v.2.2.0 - release note (12 November 2026, 23:27 UTC)

> **One GDS file.** `gds/SoC2611.gds.gz` is the only GDS of this release and the file `doc/info.json` names. It is
> fully filled, it is the file the minimum rule set and the density check ran on, and it is under GitHub's 100 MB
> limit.

> **Status: candidate for the submission checks, with the first two speed rounds.** Routing is clean, the IHP
> minimum rule set is clean on the GDS of this release (26 rule tables and the GatPoly filler table), density is
> clean, hold is met with the parasitics of the routed wires, every signal net was traced in the GDS against the
> netlist, and LVS matches. Known limits, listed below: the speed at the slow corner and 582 nets still above the
> antenna ratio limit.

## What changed since v.2.1.0
1. **Speed, two rounds of direct routes.** 87 wires that made the slowest paths slow were re-routed on direct
   paths: 62 in the first round, 25 in the second, among them single wires with 14 to 18 ns of wire delay left by
   earlier routing closures. The routing was closed again after each round. System clock on the routed wires:
   45.7 MHz fast, 30.0 MHz typical, 18.9 MHz slow, against 15.8 / 13.2 / 10.3 MHz in v.2.1.0.
2. **Hold after the speed rounds.** Four delay cells restore a margin of 0.03 ns at the fast corner; the routing
   closed again at the first pass.
The floorplan, the macros, the pads, the clock scheme, the antenna repair of the first pass and the row filler fix
next to one SRAM macro (rule NW.f) are those of v.2.1.0.

## State of this release (13 November 2026)

| Item | Result |
|---|---|
| Detailed routing (OpenROAD TritonRoute) | 0 violations, 0 signal nets without a wire |
| Power grid check, VDD and VSS | both pass |
| IHP minimum rule set, deep mode, on the GDS of this release | 26 of 26 rule tables and the GatPoly filler table completed, 0 violations, see `checks/drc_minimum_fullfill.txt` and the result databases next to it. The tables ran on a second machine on the candidate copy of this GDS; each table is counted by the completion line of its own log. |
| Density of the GDS of this release | 0 violations, see `density.txt`: global Metal1 38.5 %, Metal2 38.0 %, Metal3 38.5 %, Metal4 39.5 % (limit 35 %), TopMetal1 33.1 % (25 %), Activ 38.8 % (35 %), GatPoly 20.9 % (15 %); lowest window Metal1 30.8 %, Metal2 31.0 %, Metal3 30.7 %, Metal4 30.6 %, Activ 33.0 % (limit 25 %). IHP's own density deck passes on this file as well (`checks/density_ihp_deck.txt`). |
| IHP minimum rule set, deep mode, layout with seal ring, no fill | 23 of 23 rule tables completed, 0 violations |
| NWell rules without connectivity (13 rules of the maximal deck, and NWell width and gaps measured directly) | all 13 rules at 0, NW.f included. NWell width and gaps: nothing in the chip assembly, the same counts as v.2.1.0. See `checks/nwell_rules.txt` |
| Connectivity of the GDS against the netlist (net trace, see below) | 343,080 signal nets traced, 0 open pins, 0 shorted pins, 0 nets touching a macro without a pin there |
| LVS (KLayout, IHP deck, deep mode) | netlists match, 0 errors: 67 of 67 circuits, 353,397 instances and 354,247 nets of the chip top. SRAM macros and pad cells are black boxes with their pins; the layout is the one before fill. A negative control on the v.2.0.1 layout, one removed via and one bridge between two wires, is reported as a mismatch on exactly those three nets. Scope and the changes to view and deck: `checks/lvs_summary.txt` |
| Hold, internal paths, routed-wire parasitics | met at all three corners: worst slack +0.03 / +0.11 / +0.05 ns (fast / typical / slow) |
| Hold at the SRAM pins, routed-wire parasitics | +0.20 / +0.49 / +0.93 ns (fast / typical / slow) |
| Setup, routed-wire parasitics | system clock 45.7 MHz fast, 30.0 MHz typical, 18.9 MHz slow (the double-rate input clock is twice that) |
| Antenna check (OpenROAD) | 582 nets above the ratio limit (6,129 before the first repair pass); none at 20 times the limit or more |

Notes on the checks:
- **Nwell table.** In the minimum rule set all four rules of the Nwell table are switched off (`!PRECHECK_DRC`); the
  table only builds whole-chip connectivity and has nothing to report. It is left out of the table count. The
  NWell rules that need no connectivity were run separately (see the table).
- **Net trace.** For every signal net the metal connected to its first pin is followed in the GDS through
  Metal1 to TopMetal1 and all vias, in all cell levels. A pin of the same net that is not reached is an open, a pin
  of another net inside the traced metal is a short. It is independent of the router's own checks and of LVS. It was
  run on the GDS before fill; fill shapes are on their own datatype and are not part of any net.
- **Input pins.** Fourteen endpoints behind input pads show negative hold in the report. Six are input pins (SPI
  data in, UART, GPIO) against the placeholder input delay of the constraints; they are sampled by the system clock
  after the clock tree delay, and their timing depends on the board. Eight are the HyperBus data inputs, whose
  constraint models capture of the previous byte; with the on-chip strobe delay the current byte is captured.
- **Speed.** The numbers are for the double-rate clock scheme of this design: the single-port SRAMs do two
  accesses per system clock cycle. The slow-corner figure is the one to rate the chip at.
- **Antenna.** The minimum rule set of the precheck does not include the antenna rules. The remaining nets are
  ordinary gate pins whose wires grew in the re-routes; a second diode pass is in work on a later routing.
- **Fill.** PDK fill plus a top-up fill thinned to what density needs with margin; fill shapes at the four chamfered
  die corners are removed. The GDS carries no net or instance name properties.
- **Standard-cell rows.** The rows carry filler cells.

## Contents
- `gds/SoC2611.gds.gz`: the GDS. Seal ring + label, row filler cells, PDK fill, thinned top-up fill.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog.
- `density.txt`: density result of the GDS.
- `checks/`: DRC table verdicts and KLayout result databases of the GDS, DRC verdict of the no-fill layout, IHP
  density deck result, NWell rules, LVS summary, net trace summary, timing with the routed wires, antenna summary,
  and the comparison of the packaged GDS with the checked file.

## Source state
Routing of v.2.1.0 + two speed rounds (direct guides) + hold repair; marker nets and nets without a wire re-routed
until both counts were 0. OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.

## SHA-256
```
cf3907aa3fc6d9b0379dee5e40099a7a4e51033a20f5402a57a184fd13a700d6  gds/SoC2611.gds.gz
7b2eaad4550ad102f3ea289422501c530eedd3d37ad8545bbff9a70f360a9255  netlist/SoC2611.cdl.gz
5f84f95ae49db886490e076280f5d4b7bb807e8c3662ab7dbd7ecfea6f309374  netlist/SoC2611.v.gz
uncompressed GDS: cb3528e3ce7c593e4b7f762a1b19812799765631202f94a70cadfc955b3a1088
```
