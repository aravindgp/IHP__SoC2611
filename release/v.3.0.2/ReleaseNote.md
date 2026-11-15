# SoC2611 v.3.0.2 - release note (15 November 2026, 09:56 UTC)

> **One GDS file.** `gds/SoC2611.gds.gz` is the only GDS of this release and the file `doc/info.json` names. It is
> fully filled, it is the file the minimum rule set and the density check ran on, and it is under GitHub's 100 MB
> limit.

> **Status: the version to submit.** v.3.0.2 is v.3.0.0 with two row filler cells left out; nothing else changed.
> Routing is clean, the IHP minimum rule set is clean on the GDS of this release (26 rule tables and the GatPoly
> filler table), density is clean, LVS matches, the NWell rules and the NWell gaps are at 0, both antenna checks are
> at 0, hold is met with the parasitics of the routed wires, every input pin has a net, and the routed netlist runs
> the test firmware in simulation.

## Why v.3.0.2: two NWell gaps of 0.485 um

An extra check on v.3.0.0 found two gaps between NWell regions of 0.485 um, where rule NW.b asks for 0.62 um. Both
are at the top right corner of an RM_IHPSG13_1P_64x16_c2 macro: the macro NWell ends at y 2995.025 um and the NWell
of the first cell of the row beside it begins at y 2995.510 um, at x 1630.88 um and x 3120.72 um. The gaps are in
every release from v.2.0.1 on. Our own NWell measurement had found them but filed them as gaps inside the macros,
because they start exactly on the macro outline.

Both wells are on VDD (the macro's VDD! and VDDARRAY! pins connect to VDD), so the rule is NW.b, whose text says
that such regions are merged, and not NW.b1 (different nets, 1.80 um). NW.b is not part of the minimum rule set of
the precheck. In both places the first cell of the row was a row filler; v.3.0.2 leaves those two fillers out.

| Place | Filler left out | New first cell of the row | Its NWell to the macro NWell corner |
|---|---|---|---|
| 1 | sg13cmos5l_fill_1, r0 at (1631.04, 2993.76) um | sg13cmos5l_tiehi | 0.629 um (rule 0.62 um) |
| 2 | sg13cmos5l_fill_4, r0 at (3120.96, 2993.76) um | sg13cmos5l_dfrbpq_1 | 1.92 um |

Fillers have no devices and no nets. The full-fill file and the layout without fill of v.3.0.2 were compared with
those of v.3.0.0 cell by cell: the only differences are the two filler instances. Routing, netlist, timing, antenna
diodes, simulation and supply metal are those of v.3.0.0. See `checks/changes_from_v3.0.0.txt`.

v.3.0.1 is not a release. It joined the wells with two drawn NWell rectangles, whose joints turned out narrower
than 0.62 um (rule NW.a); its candidate branch is marked as withdrawn.

## State of this release (15 November 2026)

| Item | Result |
|---|---|
| NWell gaps below 0.62 um, whole chip (NWell not SRAM marker, as IHP's deck derives it) | 0 (2 in v.3.0.0). See `checks/nwell_rules.txt` |
| NWell rules without connectivity (13 rules of the maximal deck) | all 13 rules at 0, NW.a (width) included. See `checks/nwell_rules.txt` |
| IHP minimum rule set, deep mode, on the GDS of this release | 26 of 26 rule tables and the GatPoly filler table completed, 0 violations, all on the build machine, see `checks/drc_minimum_fullfill.txt` and the result databases next to it. Each table is counted by the completion line of its own log. |
| Density of the GDS of this release | 0 violations, see `density.txt`: global Metal1 38.5 %, Metal2 38.0 %, Metal3 38.5 %, Metal4 39.5 % (limit 35 %), TopMetal1 34.2 % (25 %), Activ 38.8 % (35 %), GatPoly 20.9 % (15 %); lowest window Metal1 30.8 %, Metal2 31.0 %, Metal3 30.8 %, Metal4 30.6 %, Activ 33.0 % (limit 25 %), the same as v.3.0.0. IHP's own density deck passed on v.3.0.0; it was not run again (`checks/density_ihp_deck.txt` says why). |
| IHP minimum rule set, deep mode, layout with seal ring, no fill | 23 of 23 rule tables completed, 0 violations |
| LVS (KLayout, IHP deck, deep mode) | netlists match, 0 warnings, 0 errors: 67 of 67 circuits, 354,825 instances and 354,306 nets of the chip top, as in v.3.0.0. SRAM macros and pad cells are black boxes with their pins; the seal ring instance is left out. See `checks/lvs_summary.txt` |
| Antenna table of the PDK | 0 violations in all rules Ant.a to Ant.i on v.3.0.0; carried, because the two fillers are on no net. See `checks/antenna_ihp_table.txt` |
| Input pins without a net, all instances | 0, as in v.3.0.0 (same routed database). See `checks/open_inputs.txt` |
| Detailed routing (OpenROAD TritonRoute) | 0 violations, 0 signal nets without a wire (same routed database) |
| Connectivity of the GDS against the netlist (net trace of the metal) | 343,545 signal nets traced, 0 open pins, 0 shorted pins (signal metal identical to v.3.0.0) |
| Hold, internal paths, routed-wire parasitics | met at all three corners: worst slack +0.015 / +0.11 / +0.05 ns (fast / typical / slow) |
| Setup, routed-wire parasitics | system clock 64.4 MHz fast, 45.5 MHz typical, 29.4 MHz slow (the double-rate input clock is twice that) |
| Antenna check (OpenROAD) | 0 nets above the ratio limit |
| Simulation of the routed netlist | as v.3.0.0: no delays, quick suite, full suite (6 of 6) and camera capture pass, also with random start values; with the delays of the routed wires the quick suite passes at a 17.1 / 11.0 / 7.8 ns input clock (slow / typical / fast, 29.2 / 45.5 / 64.1 MHz system clock), and a control run far too fast fails. See `checks/simulation_summary.txt` |
| Voltage drop of the core supply at 0.78 W | VDD 71 mV worst, VSS 122 mV worst. See `checks/supply_drop.txt` |

Notes on the checks:
- **Which checks ran again.** Everything that reads NWell, the fillers or the whole file ran on the files of
  v.3.0.2: the minimum rule set on the GDS of this release and on the layout without fill, density, LVS, the NWell
  rules and the NWell gap measurement. The checks whose inputs did not change (routed database, netlist, signal
  metal) are carried from v.3.0.0 and say so in their first line.
- **NWell.** IHP's deck checks NW.b and NW.b1 per net, and the Nwell table builds whole-chip connectivity; in the
  minimum rule set its rules are switched off. The NWell rules that need no connectivity were run from IHP's maximal
  deck, and every gap between NWell regions was measured without nets.
- **Speed.** The slow-corner figure is the one to rate the chip at. The numbers are results of static timing
  analysis; no silicon has been measured.
- For everything else the release note of v.3.0.0 applies: the open-input check, the simulation set-up, the net
  trace, the input pins, the antenna checks, the voltage drop, the fill and the standard-cell rows.

## Contents
- `gds/SoC2611.gds.gz`: the GDS. Seal ring + label, row filler cells, PDK fill, thinned top-up fill.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog (unchanged from v.3.0.0).
- `density.txt`: density result of the GDS.
- `checks/`: DRC table verdicts and KLayout result databases of the GDS, DRC verdict of the no-fill layout, density
  deck result, NWell rules and gaps, LVS summary, the changes against v.3.0.0, and the evidence carried from v.3.0.0.

## Source state
v.3.0.0 (routing, antenna passes, buffers, four direct routes, repair of the 384 open inputs, supply bars) without
two row filler cells at two SRAM macro corners. OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.

## SHA-256
```
4c194fab821fd62ccc8974324e3713bf87c894b57138f9ab4e9b5a81153571e7  gds/SoC2611.gds.gz
d12313d52792d1363fdd542530b3823136bc0f0b43e598c8a8530ac2d52462db  netlist/SoC2611.cdl.gz
1ae675a4d489c861081a3c3a7966430ad7b25e2d240f385c918dcdcdc756037b  netlist/SoC2611.v.gz
uncompressed GDS: 58c8ea468ceda2f178c3329a1c619f76a8868fb54e8a0a202b476aaa5eec85a7
```
