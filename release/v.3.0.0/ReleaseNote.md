# SoC2611 v.3.0.0 - release note (14 November 2026, 04:20 UTC)

> **One GDS file.** `gds/SoC2611.gds.gz` is the only GDS of this release and the file `doc/info.json` names. It is
> fully filled, it is the file the minimum rule set and the density check ran on, and it is under GitHub's 100 MB
> limit.

> **Status: the version to submit. It repairs a defect that every earlier file has.** Routing is clean, the IHP
> minimum rule set is clean on the GDS of this release (26 rule tables and the GatPoly filler table), density is
> clean, both antenna checks are at 0, hold is met with the parasitics of the routed wires, every signal net was
> traced in the GDS against the netlist, LVS matches, every input pin has a net, and the routed netlist runs the test
> firmware in simulation, without delays and with the delays of the routed wires at three corners.

## Why v.3.0.0: a repair that every earlier file needs

Every release up to v.2.4.0 and the candidates v.2.5.0, v.2.3.1 and v.2.4.1 have 384 buffers without a connection on
their input pin. They are the top buffers of the buffer trees of the 22 signals with the most loads, among them the
reset of the system clock domain with about 50,000 loads. A script of the flow built these trees on 30 October; it
moved the loads to the new buffers and did not join the top buffers to the original signal, so the original signal
kept only its driver. With these inputs open the chip would not work. **Do not submit any earlier file.**

No earlier check could see it: layout and netlist agreed, so LVS matched; static timing analysis skips a pin without
a driver; the firmware tests ran on the RTL. It was found on 13 November while a simulation of the routed netlist
was being prepared.

In v.3.0.0 each of the 384 inputs is connected to its original signal, each of the 22 signals has a strong buffer
behind its driver, and the 44 nets are routed. Two checks are new and are part of this and every later release:
- every input pin of every standard cell, pad and SRAM macro has a net, and every net with loads has a driver;
- the routed netlist is simulated pad to pad: reset, boot from the external memory, the firmware checks, UART.

## What else changed since v.2.4.0
1. **Antenna at 0 in both checks.** 91 diodes under the wire and 10 Metal2 runs lifted to Metal4 took the router's
   antenna check from 78 nets to 0. The 6 nets that were above the limit of the PDK antenna table through TopMetal1
   have a buffer with a large gate in front of their receiving pin. After the repair route, 26 more diodes protect
   nets that had to move to make room for the repair wires.
2. **Four long wires laid straight.** The four longest wires of the fast corner, each about 20 mm long between pins
   less than 3 mm apart, are routed directly. System clock on the routed wires: 64.4 MHz fast, 45.5 MHz typical,
   29.4 MHz slow, against 54.7 / 45.5 / 29.4 MHz in v.2.4.0.
3. **More metal for the core supply.** In all earlier files the core current of the west and east supply pads
   reached the power grid over one Metal4 rail of the pad ring, 15.8 um wide, and the north and south supply pads
   were not tied to the power grid at all. New: a TopMetal1 bar per net along the west and east side, a TopMetal1
   bar on the VDD side of the core ring in the north and south, and ties from the north and south pads to the core
   ring: 0.76 mm2 of TopMetal1 and 516 vias in the empty strip between the pad ring and the core. No signal wire
   moved. Voltage drop at 0.78 W, worst point: VDD 71 mV, VSS 122 mV, against 217 mV and 205 mV before.
4. **Die outline** on prBoundary.drawing (189/0).
The floorplan, the macros and the pads are those of v.2.4.0.

## State of this release (14 November 2026)

| Item | Result |
|---|---|
| Input pins without a net, all instances | 0 (384 in every earlier file). Nets with loads and no driver: 0. See `checks/open_inputs.txt` |
| Wiring of the routed netlist against the netlist after synthesis | 801,501 input pins compared, every one driven by the same source; see `checks/open_inputs.txt` |
| Detailed routing (OpenROAD TritonRoute) | 0 violations, 0 signal nets without a wire |
| Power grid check, VDD and VSS | both pass |
| IHP minimum rule set, deep mode, on the GDS of this release | 26 of 26 rule tables and the GatPoly filler table completed, 0 violations, see `checks/drc_minimum_fullfill.txt` and the result databases next to it. 25 tables ran on the build machine; the seal ring and the GatPoly filler tables ran on a second machine on the candidate copy of this GDS (hash checked before the run). Each table is counted by the completion line of its own log. |
| Density of the GDS of this release | 0 violations, see `density.txt`: global Metal1 38.5 %, Metal2 38.0 %, Metal3 38.5 %, Metal4 39.5 % (limit 35 %), TopMetal1 34.2 % (25 %), Activ 38.8 % (35 %), GatPoly 20.9 % (15 %); lowest window Metal1 30.8 %, Metal2 31.0 %, Metal3 30.8 %, Metal4 30.6 %, Activ 33.0 % (limit 25 %). IHP's own density deck passes on this file as well (`checks/density_ihp_deck.txt`). |
| IHP minimum rule set, deep mode, layout with seal ring, no fill | 23 of 23 rule tables completed, 0 violations |
| NWell rules without connectivity (13 rules of the maximal deck, and NWell width and gaps measured directly) | all 13 rules at 0, NW.f included. NWell width and gaps: nothing in the chip assembly, the same counts as v.2.4.0. See `checks/nwell_rules.txt` |
| Connectivity of the GDS against the netlist (net trace, see below) | 343,545 signal nets traced, 0 open pins, 0 shorted pins, 0 nets touching a macro without a pin there |
| LVS (KLayout, IHP deck, deep mode) | netlists match, 0 warnings, 0 errors: 67 of 67 circuits, 354,825 instances and 354,306 nets of the chip top. SRAM macros and pad cells are black boxes with their pins; the seal ring instance is left out. See `checks/lvs_summary.txt` |
| Hold, internal paths, routed-wire parasitics | met at all three corners: worst slack +0.015 / +0.11 / +0.05 ns (fast / typical / slow) |
| Hold at the SRAM pins, routed-wire parasitics | +0.20 / +0.49 / +0.92 ns (fast / typical / slow) |
| Setup, routed-wire parasitics | system clock 64.4 MHz fast, 45.5 MHz typical, 29.4 MHz slow (the double-rate input clock is twice that: 128.8 / 91.0 / 58.8 MHz) |
| Reset of the system clock domain, routed-wire parasitics | recovery +2.95 / +2.38 / +1.50 ns, removal +1.21 / +1.63 / +2.34 ns (fast / typical / slow) |
| Antenna check (OpenROAD) | 0 nets above the ratio limit (78 in v.2.4.0) |
| Antenna table of the PDK (KLayout, `antenna.drc`, layout before fill) | 0 violations in all rules Ant.a to Ant.i (6 nets in v.2.4.0). See `checks/antenna_ihp_table.txt` |
| Simulation of the routed netlist, no delays | pass: quick suite, full suite (6 of 6 checks) and camera capture with all registers starting at 0; quick suite and camera capture with two random start patterns each. See `checks/simulation_summary.txt` |
| Simulation of the routed netlist with cell and wire delays | pass at the rated speed of each corner: slow at a 17.1 ns input clock, typical at 11.0 ns, fast at 7.8 ns; each boots, makes all 281 memory transactions and prints its three UART lines. A control run far too fast (6.0 ns at the typical corner) fails as it must. See `checks/simulation_summary.txt` |
| Voltage drop of the core supply at 0.78 W | VDD 71 mV worst, 48 mV average; VSS 122 mV worst, 89 mV average. See `checks/supply_drop.txt` |

Notes on the checks:
- **Open inputs.** The check walks every instance of the routed database and reports each input pin without a net
  and each net that has loads and no driver. It would have found the defect on 30 October.
- **Simulation.** The netlist that is simulated is the routed netlist with the cells that have no logic removed
  (row fillers, antenna diodes, pad fillers). Pad to pad: the reset is applied at the pad, the processor boots from
  the model of the external memory, runs the test firmware and reports over the UART pad. With delays, the same test
  bench runs the netlist with the cell and wire delays of the timing analysis built in, one run per corner at the
  speed that corner is rated for, and one run far too fast that has to fail.
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
  accesses per system clock cycle. The slow-corner figure is the one to rate the chip at. At the fast corner cells,
  not wires, limit the worst path now. The slowest path through one of the 22 repaired signals has two input clock
  cycles and allows 32.3 MHz at the slow corner, above the 29.4 MHz of the chip as a whole.
- **Antenna.** The minimum rule set of the precheck does not include the antenna rules. Two checks were run and
  both are at 0: the router's check, which asks for the protection diode on the layer under check, and the antenna
  table of the PDK, which takes the diode from the complete net.
- **Voltage drop.** Computed with the supply rails of the pad ring as real wires and the four supply pads of each
  net as the sources, at the fast corner with 0.78 W (100 MHz input clock, one signal in ten switching per cycle).
  For the same layout without the added metal this analysis shows 217 mV and 205 mV, where an analysis that takes
  the rails as ideal shows 17 mV and 27 mV. The supply metal of every earlier file is that of the layout without
  the added metal.
- **Fill.** PDK fill plus a top-up fill thinned to what density needs with margin; fill shapes at the four chamfered
  die corners are removed. The GDS carries no net or instance name properties.
- **Standard-cell rows.** The rows carry filler cells.

## Contents
- `gds/SoC2611.gds.gz`: the GDS. Seal ring + label, row filler cells, PDK fill, thinned top-up fill.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog.
- `density.txt`: density result of the GDS.
- `checks/`: DRC table verdicts and KLayout result databases of the GDS, DRC verdict of the no-fill layout, IHP
  density deck result, NWell rules, LVS summary, net trace summary, timing with the routed wires, antenna summary
  and antenna table, open-input and wiring check, simulation summary, voltage drop, and the comparison of the
  packaged GDS with the checked file.

## Source state
Routing of v.2.4.0 + antenna passes to 0 + buffers in front of 6 TopMetal1 nets + four direct routes + the repair of
the 384 open inputs with 22 drive buffers + 26 diodes + supply bars; every touched net on its old guides where it
had one; marker nets re-routed until the count was 0. OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.

## SHA-256
```
5cb1caa218ee16156cb656467195274cfbb17a92be66035459b41e853d3abccf  gds/SoC2611.gds.gz
c695f8441bb2878f24e67548b22a55815324d483aeab26e53d7f28bfac47d11c  netlist/SoC2611.cdl.gz
79e2504230856e5632ac5d342c881b798588b6ab8639aa07a4269035a6fbcbe8  netlist/SoC2611.v.gz
uncompressed GDS: cd224efdc093d13021ec366e73e405878ceaa858fdbcba7296c150d0d12253e3
```
