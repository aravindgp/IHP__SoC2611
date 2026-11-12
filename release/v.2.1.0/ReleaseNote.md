# SoC2611 v.2.1.0 - release note (12 November 2026, 10:05 UTC)

> **One GDS file.** `gds/SoC2611.gds.gz` is the only GDS of this release and the file `doc/info.json` names. It is
> fully filled, it is the file the minimum rule set and the density check ran on, and it is under GitHub's 100 MB
> limit.

> **Status: candidate for the submission checks, with the antenna repair.** Routing is clean, the IHP minimum rule
> set is clean on the GDS of this release (26 rule tables and the GatPoly filler table), density is clean, hold is
> met with the parasitics of the routed wires, and every signal net was traced in the GDS against the netlist.
> Known limits, listed below: the speed on the routed wires, 590 nets still above the antenna ratio limit, and LVS.

## What changed since v.2.0.1
1. **Antenna repair.** 7,213 diode cells at gate pins and 1,315 small buffers at SRAM and pad pins were added and
   the touched nets re-routed until the routing was clean again. Nets above the antenna ratio limit: 590, down from
   6,129; the worst factor is 13.1 times the limit, the median 1.44, and 23 nets are at 5 times or more.
2. **Hold after the repair.** The re-route left 5 endpoints, the phase flip-flops of the SRAM wrappers, 0.02 to
   0.07 ns short at the fast corner. Nine delay cells were added there; the routing closed again at the first pass
   and hold is met at all three corners.
3. **Row fillers next to one SRAM macro.** IHP's NWell rules from the maximal rule deck, run without connectivity,
   showed 9 markers of NW.f on v.2.0.1: the rows next to one SRAM macro start 0.16 um from its edge, and the row
   filler in the first site put its substrate tie strap 0.16 um from the macro's NWell (rule: 0.24 um). In this
   release the fillers of that site give way (18 fillers removed, 32 smaller ones set one site further out); their NWell stays, so the NWell of the chip is unchanged.
   NW.f is not part of the minimum rule set.
The floorplan, the macros, the pads and the clock scheme are those of v.2.0.1.

## State of this release (12 November 2026)

| Item | Result |
|---|---|
| Detailed routing (OpenROAD TritonRoute) | 0 violations, 0 signal nets without a wire |
| Power grid check, VDD and VSS | both pass |
| IHP minimum rule set, deep mode, on the GDS of this release | 26 of 26 rule tables and the GatPoly filler table completed, 0 violations, see `checks/drc_minimum_fullfill.txt` and the result databases next to it |
| Density of the GDS of this release | 0 violations, see `density.txt`: global Metal1 38.5 %, Metal2 38.0 %, Metal3 38.5 %, Metal4 39.5 % (limit 35 %), TopMetal1 33.1 % (25 %), Activ 38.8 % (35 %), GatPoly 20.9 % (15 %); lowest window Metal1 30.8 %, Metal2 31.0 %, Metal3 30.8 %, Metal4 30.6 %, Activ 33.0 % (limit 25 %). IHP's own density deck passes on this file as well (`checks/density_ihp_deck.txt`, result database next to it). |
| IHP minimum rule set, deep mode, layout with seal ring, no fill | 23 of 23 rule tables completed, 0 violations |
| NWell rules without connectivity (13 rules of the maximal deck, and NWell width and gaps measured directly) | all 13 rules at 0, NW.f included (9 markers on v.2.0.1). NWell width and gaps: nothing in the chip assembly, the same counts as v.2.0.1. See `checks/nwell_rules.txt` |
| Connectivity of the GDS against the netlist (net trace, see below) | 343,085 signal nets traced, 0 open pins, 0 shorted pins, 0 nets touching a macro without a pin there |
| Hold, internal paths, routed-wire parasitics | met at all three corners: worst slack +0.03 / +0.13 / +0.09 ns (fast / typical / slow) |
| Hold at the SRAM pins, routed-wire parasitics | +0.15 / +0.49 / +0.93 ns (fast / typical / slow) |
| Setup, routed-wire parasitics | system clock 15.8 MHz fast, 13.2 MHz typical, 10.3 MHz slow (the double-rate input clock is twice that) |
| Antenna check (OpenROAD) | 590 nets above the ratio limit (6,129 before the repair) |
| LVS (deep) | not completed. After corrections to the LVS view (seal ring instance, resistor markers inside the macros, unused subcircuits, row filler cells) the net extraction of the chip completes in about an hour. The comparison step is in progress on the v.2.0.1 layout; the view of this release is built the same way and follows. |

Notes on the checks:
- **Nwell table.** In the minimum rule set all four rules of the Nwell table are switched off (`!PRECHECK_DRC`); the
  table only builds whole-chip connectivity and has nothing to report. It is left out of the table count. The
  NWell rules that need no connectivity were run separately (see the table).
- **Net trace.** For every signal net the metal connected to its first pin is followed in the GDS through
  Metal1 to TopMetal1 and all vias, in all cell levels. A pin of the same net that is not reached is an open, a pin
  of another net inside the traced metal is a short. It is independent of the router's own checks and does not
  replace LVS: devices are not extracted, and the supplies are checked by the power grid check of the router
  database, not in the GDS. It was run on the GDS before fill; fill shapes are on their own datatype and are not
  part of any net.
- **Input pins.** Fourteen endpoints behind input pads show negative hold in the report. Six are input pins (SPI
  data in, UART, GPIO) against the placeholder input delay of the constraints; they are sampled by the system clock
  after the clock tree delay, and their timing depends on the board. Eight are the HyperBus data inputs, whose
  constraint models capture of the previous byte; with the on-chip strobe delay the current byte is captured.
- **Speed.** The numbers are for the double-rate clock scheme of this design: the single-port SRAMs do two
  accesses per system clock cycle. The slow-corner figure is the one to plan a board with.
- **Antenna.** The minimum rule set of the precheck does not include the antenna rules. The 590 remaining nets are
  ordinary gate pins whose wires grew in the re-routes; none is at 20 times the limit or more.
- **Fill.** PDK fill plus a top-up fill thinned to what density needs with margin; fill shapes at the four chamfered
  die corners are removed. The GDS carries no net or instance name properties.
- **Standard-cell rows.** The rows carry filler cells.

## Contents
- `gds/SoC2611.gds.gz`: the GDS. Seal ring + label, row filler cells, PDK fill, thinned top-up fill.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog.
- `density.txt`: density result of the GDS.
- `checks/`: DRC table verdicts and KLayout result databases of the GDS, DRC verdict of the no-fill layout, NWell
  rules, net trace summary, timing with the routed wires, antenna summary, and the comparison of the packaged GDS
  with the checked file.

## Source state
Routing of v.2.0.1 + antenna repair + hold repair; marker nets and nets without a wire re-routed until both counts
were 0. OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.

## SHA-256
```
ebf859203110f4a9149dc566b4853dcdfcc442bdeaa6e4bc3cf128fdd8cbbcdf  gds/SoC2611.gds.gz
f4388794bbeda866d7708d826d92ec6c01c86fc17846b48edc15cc28bd81ceb4  netlist/SoC2611.cdl.gz
c77c09a6c9e2f484d3313971db3cb8723dd4d43ce3a501aa1e6c152f4c0e08a6  netlist/SoC2611.v.gz
uncompressed GDS: 35a65cdb8ae6857eec5f1b75561ef205c06cf5dca602bb3a7f2d74a9ec3e2630
```
