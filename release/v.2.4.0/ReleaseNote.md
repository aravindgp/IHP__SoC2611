# SoC2611 v.2.4.0 - release note (13 November 2026, 09:42 UTC)

> **One GDS file.** `gds/SoC2611.gds.gz` is the only GDS of this release and the file `doc/info.json` names. It is
> fully filled, it is the file the minimum rule set and the density check ran on, and it is under GitHub's 100 MB
> limit.

> **Status: candidate for the submission checks, with five speed steps and three antenna passes.** Routing is clean, the IHP minimum rule
> set is clean on the GDS of this release (26 rule tables and the GatPoly filler table), density is clean, hold is
> met with the parasitics of the routed wires, every signal net was traced in the GDS against the netlist, and LVS
> matches. The 100 MHz input clock of the constraints is met at the fast corner. Known limits, listed below: the
> speed at the typical and slow corners, 78 nets still above the antenna ratio limit of the router's check, and
> 6 nets above the limit of IHP's antenna table through TopMetal1.

## What changed since v.2.3.0
1. **Fifth speed step and clock generator.** 67 more gates that drive long nets got a strong buffer at their
   output. The three registers of the clock generator are now clocked from the root of the clock tree, next to the
   clock gates they feed; in v.2.3.0 their enable path limited the typical corner. A hold repair of 4 delay cells
   restores the margin of 0.03 ns at the fast corner. System clock on the routed wires: 54.7 MHz fast, 45.5 MHz
   typical, 29.4 MHz slow, against 54.2 / 44.3 / 28.7 MHz in v.2.3.0.
2. **Antenna, second and third pass.** 865 more diode cells and 98 buffers at SRAM pins were added, each touched
   net re-routed on its old guides. Nets above the antenna ratio limit of the router's check: 78, down from 592;
   none is above 4 times the limit.
The floorplan, the macros, the pads and the row filler fix next to one SRAM macro (rule NW.f) are those of v.2.3.0.

## State of this release (13 November 2026)

| Item | Result |
|---|---|
| Detailed routing (OpenROAD TritonRoute) | 0 violations, 0 signal nets without a wire |
| Power grid check, VDD and VSS | both pass |
| IHP minimum rule set, deep mode, on the GDS of this release | 26 of 26 rule tables and the GatPoly filler table completed, 0 violations, see `checks/drc_minimum_fullfill.txt` and the result databases next to it. The tables ran on a second machine on the candidate copy of this GDS; each table is counted by the completion line of its own log. |
| Density of the GDS of this release | 0 violations, see `density.txt`: global Metal1 38.5 %, Metal2 38.0 %, Metal3 38.5 %, Metal4 39.5 % (limit 35 %), TopMetal1 33.1 % (25 %), Activ 38.8 % (35 %), GatPoly 20.9 % (15 %); lowest window Metal1 30.8 %, Metal2 31.0 %, Metal3 30.7 %, Metal4 30.6 %, Activ 33.0 % (limit 25 %). IHP's own density deck passes on this file as well (`checks/density_ihp_deck.txt`). |
| IHP minimum rule set, deep mode, layout with seal ring, no fill | 23 of 23 rule tables completed, 0 violations |
| NWell rules without connectivity (13 rules of the maximal deck, and NWell width and gaps measured directly) | all 13 rules at 0, NW.f included. NWell width and gaps: nothing in the chip assembly, the same counts as v.2.3.0. See `checks/nwell_rules.txt` |
| Connectivity of the GDS against the netlist (net trace, see below) | 343,489 signal nets traced, 0 open pins, 0 shorted pins, 0 nets touching a macro without a pin there |
| LVS (KLayout, IHP deck, deep mode) | netlists match, 0 warnings, 0 errors: 67 of 67 circuits, 354,671 instances and 354,656 nets of the chip top. SRAM macros and pad cells are black boxes with their pins; the seal ring instance is left out. See `checks/lvs_summary.txt` |
| Hold, internal paths, routed-wire parasitics | met at all three corners: worst slack +0.03 / +0.11 / +0.05 ns (fast / typical / slow) |
| Hold at the SRAM pins, routed-wire parasitics | +0.20 / +0.49 / +0.92 ns (fast / typical / slow) |
| Setup, routed-wire parasitics | system clock 54.7 MHz fast, 45.5 MHz typical, 29.4 MHz slow (the double-rate input clock is twice that: 109.4 / 91.0 / 58.8 MHz) |
| Antenna check (OpenROAD) | 78 nets above the ratio limit (6,129 before the first repair pass); none above 4 times the limit |
| Antenna table of the PDK (KLayout, `antenna.drc`, layout before fill) | 6 nets above rule Ant.e on TopMetal1 (cumulative metal-to-gate ratio with a protection diode, limit 20,000: 20,029 to 29,054); every other rule of the table at 0. See `checks/antenna_ihp_table.txt` |

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
- **Clock generator.** Its three registers are clocked from the root of the clock tree since this release. The
  tightest paths at the typical and slow corner are now those from system-clock flip-flops into the SRAM pins,
  which have one input clock cycle (slack at a 10 ns input clock: +2.5 / -1.0 / -7.0 ns fast / typical / slow).
- **Antenna.** The minimum rule set of the precheck does not include the antenna rules. Two checks were run. The
  router's check asks for the protection diode on the layer under check: 78 nets remain, ordinary gate pins at the
  end of a long Metal2 or Metal3 wire whose diode is joined one layer higher. The antenna table of the PDK takes
  the diode from the complete net and allows a ratio of 20,000 with it: none of those 78 nets appears there, but 6
  nets with one small gate on 1.3 to 1.9 mm of TopMetal1 (1.64 um wide) are above it. Both are repaired in a later
  candidate.
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
Routing of v.2.3.0 + a fifth step of drive buffers and the clock generator fix + hold repair + two antenna passes
(every touched net on its old guides); marker nets and nets without a wire re-routed until both counts were 0. OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.

## SHA-256
```
cbf7704a4355d65e11c8162cb894cc91572ebc9f142f20113ef15ae84ccfaea0  gds/SoC2611.gds.gz
5f84f5ecec64e14482078e148629fe1bb1044dca7fbba6b8140bb31f9632b63f  netlist/SoC2611.cdl.gz
dc60c9cf46fae34a3450b08adff30de71bf67e19875a0b83ad167039a5078e0b  netlist/SoC2611.v.gz
uncompressed GDS: ee582cb32d9dec3d369512996a782021a0c31c49a43610e14210a77127da1eb2
```
