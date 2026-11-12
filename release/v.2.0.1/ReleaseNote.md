# SoC2611 v.2.0.1 - release note (12 November 2026, 05:10 UTC)

> **One GDS file.** `gds/SoC2611.gds.gz` is the only GDS of this release and the file `doc/info.json` names. It is
> fully filled, it is the file the minimum rule set and the density check ran on, and it is under GitHub's 100 MB
> limit. Up to v.2.0.0 the file named in `doc/info.json` carried the PDK lattice fill only and did not pass density on
> its own (75 violations); the checked full-fill file was 155 MB and came in two parts. That possible mix-up is gone.

> **Status: candidate for the submission checks.** Routing is clean, the IHP minimum rule set is clean on the GDS of
> this release (26 rule tables and the GatPoly filler table), density is clean, hold is met with the parasitics of
> the routed wires, every signal net was traced in the GDS against the netlist, and LVS matches (result of
> 12 November 2026). Two limits are known and listed below: the speed on the routed wires and the antenna ratios.

## What changed since v.2.0.0
The routing, all cells, the seal ring and the PDK fill are those of v.2.0.0. Two things were removed to bring the
filled GDS from 155 MB to under 100 MB compressed:
1. **Name properties.** The stream-out wrote the net name on every wire and the instance name on every cell as GDS
   properties: a quarter of the file. Masks, DRC and density do not use them. Cell names, text labels and all
   geometry are unchanged.
2. **Part of the top-up fill.** The top-up fill added far more than density needs (Metal4 went from 38.6 % to
   56.4 %). Kept are all top-up shapes of Metal2 and TopMetal1, and of Metal1, Metal3 and Metal4 those that density
   windows below 30 % need, plus the largest ones up to a global density of 38.5 %; the Activ and GatPoly top-up is
   not needed (the PDK fill alone gives 38.8 % and 21.0 %). In numbers: 756,931 of 3,166,568 top-up shapes.
   Every fill shape of this file is an unchanged shape of the v.2.0.0 full-fill file, which passed the minimum rule
   set; none was added or moved (`checks/release_file_identity.txt`).
The minimum rule set and the density check were run again on exactly this file.

## State of this release (12 November 2026)

| Item | Result |
|---|---|
| Detailed routing (OpenROAD TritonRoute) | 0 violations, 0 signal nets without a wire |
| Power grid check, VDD and VSS | both pass |
| IHP minimum rule set, deep mode, on the GDS of this release | 26 of 26 rule tables and the GatPoly filler table completed, 0 violations, see `checks/drc_minimum_fullfill.txt` and the result databases next to it. The GatPoly filler table ran on a second machine on the same GDS (the run on the build machine was ended by its memory limit after 3 hours). |
| Density of the GDS of this release | 0 violations, see `density.txt`: global Metal1 38.5 %, Metal2 38.0 %, Metal3 38.5 %, Metal4 39.6 % (limit 35 %), TopMetal1 33.1 % (25 %), Activ 38.8 % (35 %), GatPoly 21.0 % (15 %); lowest window Metal1 30.8 %, Metal2 31.0 %, Metal3 30.8 %, Metal4 30.6 %, Activ 33.0 % (limit 25 %). IHP's own density deck passes on this file as well (`checks/density_ihp_deck.txt`). |
| IHP minimum rule set, deep mode, layout with seal ring, no fill | 23 of 23 rule tables completed, 0 violations |
| NWell rules without connectivity (13 rules of IHP's maximal deck, and NWell width and gaps measured directly) | 12 rules at 0. NW.f: 9 markers at one SRAM macro edge, where the row filler of the first site puts its substrate tie 0.16 um from the macro's NWell (rule 0.24 um). NW.f is not part of the minimum rule set; it is fixed in the next release. NWell width and gaps: nothing in the chip assembly. See `checks/nwell_rules.txt`. |
| Connectivity of the GDS against the netlist (net trace, see below) | 341,753 signal nets traced, 0 open pins, 0 shorted pins, 0 nets touching a macro without a pin there |
| Hold, internal paths, routed-wire parasitics | met at all three corners: worst slack +0.02 / +0.11 / +0.05 ns (fast / typical / slow) |
| Hold at the SRAM pins, routed-wire parasitics | +0.20 / +0.49 / +0.93 ns (fast / typical / slow) |
| Setup, routed-wire parasitics | system clock 15.0 MHz fast, 12.7 MHz typical, 10.0 MHz slow (the double-rate input clock is twice that) |
| Antenna check (OpenROAD) | 6,129 nets above the ratio limit; not repaired in this file (a repaired routing with 590 such nets is in sign-off as the next release) |
| LVS (KLayout, IHP deck, deep mode) | netlists match, 0 errors: 66 of 66 circuits, 344,865 instances and 352,928 nets of the chip top. SRAM macros and pad cells are black boxes with their pins; the layout is the one before fill. A copy of the layout with one removed via and one bridge between two wires is reported as a mismatch on exactly those three nets. Scope and the changes to view and deck: `checks/lvs_summary.txt` |

Notes on the checks:
- **Nwell table.** In the minimum rule set all four rules of the Nwell table are switched off (`!PRECHECK_DRC`); the
  table only builds whole-chip connectivity and has nothing to report, and that build does not finish on this
  chip. It is left out of the table count. The NWell rules that need no connectivity were run separately (see the
  table).
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
- **Antenna.** The ratios are above the limit of the technology LEF on 6,129 nets. The minimum rule set of the
  precheck does not include the antenna rules.
- **Fill at the die corners.** Fill shapes at the four chamfered corners are removed.
- **Standard-cell rows.** The rows carry filler cells (1,074,709 instances).

## Contents
- `gds/SoC2611.gds.gz`: the GDS. Seal ring + label, row filler cells, PDK fill, thinned top-up fill.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog.
- `density.txt`: density result of the GDS.
- `checks/`: DRC table verdicts and KLayout result databases of the GDS, DRC verdict of the no-fill layout, net
  trace summary, timing with the routed wires, antenna summary, and the comparison of the packaged GDS with the
  checked file.

## Source state
Routing of v.2.0.0 (rc3 routing + hold repair against the routed wires). OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l
unmodified.

## SHA-256
```
aebf0261346a5245c1454e575e78ea09419cde234d2a69f9d23ec1a5c6dcc23e  gds/SoC2611.gds.gz
4421ed009b4e1d573b7050b4c4f120b01177ed3fdbb16422a75d2b8bb1098f34  netlist/SoC2611.cdl.gz
a3d18c2562e734c6f450b977e0dd800d3b05c01bb1193c648622a11e88cb6c4e  netlist/SoC2611.v.gz
uncompressed GDS: b9780211feb2c199809713a92e828ab19d12bebbb58624268e316a64d596d485
```
