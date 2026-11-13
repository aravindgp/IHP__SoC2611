# SoC2611 v.2.3.0 - release note (13 November 2026, 04:35 UTC)

> **One GDS file.** `gds/SoC2611.gds.gz` is the only GDS of this release and the file `doc/info.json` names. It is
> fully filled, it is the file the minimum rule set and the density check ran on, and it is under GitHub's 100 MB
> limit.

> **Status: candidate for the submission checks, with four speed steps.** Routing is clean, the IHP minimum rule
> set is clean on the GDS of this release (26 rule tables and the GatPoly filler table), density is clean, hold is
> met with the parasitics of the routed wires, every signal net was traced in the GDS against the netlist, and LVS
> matches. The 100 MHz input clock of the constraints is met at the fast corner. Known limits, listed below: the
> speed at the typical and slow corners and 592 nets still above the antenna ratio limit.

## What changed since v.2.2.0
1. **Speed, two steps of drive buffers.** After the direct routes of v.2.2.0 the slow stages were small gates
   (drive 1 or 2) that drive long nets: a single-drive gate took up to 5 ns for one stage at the slow corner. 244
   such gates got a strong buffer right at their output, with every existing cell locked: 14 in the third step,
   230 in the fourth. Each buffered net kept the guides of its clean routing, so only the neighbourhood of each new
   buffer was routed anew. System clock on the routed wires: 54.2 MHz fast, 44.3 MHz typical, 28.7 MHz slow,
   against 45.7 / 30.0 / 18.9 MHz in v.2.2.0.
2. **Hold after the speed steps.** Four delay cells restore a margin of 0.03 ns at the fast corner; the routing
   closed again at the first pass.
The floorplan, the macros, the pads, the clock scheme, the antenna repair of the first pass and the row filler fix
next to one SRAM macro (rule NW.f) are those of v.2.2.0.

## State of this release (13 November 2026)

| Item | Result |
|---|---|
| Detailed routing (OpenROAD TritonRoute) | 0 violations, 0 signal nets without a wire |
| Power grid check, VDD and VSS | both pass |
| IHP minimum rule set, deep mode, on the GDS of this release | 26 of 26 rule tables and the GatPoly filler table completed, 0 violations, see `checks/drc_minimum_fullfill.txt` and the result databases next to it. The tables ran on a second machine on the candidate copy of this GDS; each table is counted by the completion line of its own log. |
| Density of the GDS of this release | 0 violations, see `density.txt`: global Metal1 38.5 %, Metal2 38.0 %, Metal3 38.5 %, Metal4 39.5 % (limit 35 %), TopMetal1 33.1 % (25 %), Activ 38.8 % (35 %), GatPoly 20.9 % (15 %); lowest window Metal1 30.8 %, Metal2 31.0 %, Metal3 31.0 %, Metal4 30.6 %, Activ 33.0 % (limit 25 %). IHP's own density deck passes on this file as well (`checks/density_ihp_deck.txt`). |
| IHP minimum rule set, deep mode, layout with seal ring, no fill | 23 of 23 rule tables completed, 0 violations |
| NWell rules without connectivity (13 rules of the maximal deck, and NWell width and gaps measured directly) | all 13 rules at 0, NW.f included. NWell width and gaps: nothing in the chip assembly, the same counts as v.2.2.0. See `checks/nwell_rules.txt` |
| Connectivity of the GDS against the netlist (net trace, see below) | 343,324 signal nets traced, 0 open pins, 0 shorted pins, 0 nets touching a macro without a pin there |
| LVS (KLayout, IHP deck, deep mode) | netlists match, 0 warnings, 0 errors: 67 of 67 circuits, 353,641 instances and 354,491 nets of the chip top. SRAM macros and pad cells are black boxes with their pins; the seal ring instance is left out. See `checks/lvs_summary.txt` |
| Hold, internal paths, routed-wire parasitics | met at all three corners: worst slack +0.03 / +0.11 / +0.05 ns (fast / typical / slow) |
| Hold at the SRAM pins, routed-wire parasitics | +0.20 / +0.49 / +0.93 ns (fast / typical / slow) |
| Setup, routed-wire parasitics | system clock 54.2 MHz fast, 44.3 MHz typical, 28.7 MHz slow (the double-rate input clock is twice that: 108.5 / 88.5 / 57.4 MHz) |
| Antenna check (OpenROAD) | 592 nets above the ratio limit (6,129 before the first repair pass); none at 20 times the limit or more |

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
- **Clock generator.** At the typical corner the tightest path is the enable of the gate that derives the system
  clock: its register sits on a leaf of the balanced clock tree while the gate sits at the root, so the enable has
  one input clock cycle minus the tree delay (slack at a 10 ns input clock: +2.2 / -1.3 / -7.4 ns fast / typical /
  slow). At the slow-corner rating the path is met on every chip. A later candidate clocks these registers from the
  root.
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
Routing of v.2.2.0 + two steps of drive buffers (buffered nets on their old guides) + hold repair; marker nets and
nets without a wire re-routed until both counts were 0. OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.

## SHA-256
```
02b3a89b5739cf5a3ec6b53b03ff61012486977a1b9a55b9c3f4b39b303855d4  gds/SoC2611.gds.gz
0c462889e67378c92ddcd83d223257d39cefb04939aed79f37d4522ace817e86  netlist/SoC2611.cdl.gz
3073da486097b75270c81f6b49b252a4bfe60e8a9f7da030add06297ce79d0e4  netlist/SoC2611.v.gz
uncompressed GDS: ebffb7e423c7be7826ee2c04b2c659aa646f9d511a900dc6e49f22fc36de244e
```
