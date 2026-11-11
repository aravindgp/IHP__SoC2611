# SoC2611 v.2.0.0-rc3 - release note (11 November 2026, 03:11 UTC)

> **Status: release candidate with the timing fix.** This candidate replaces `v.2.0.0-rc2`, which had a clock
> alignment problem (found by the first full timing report of the routed chip on 10 November). Routing is clean, the IHP minimum rule set is clean on the
> layout without fill, density is clean on this file, and every signal net was traced in the GDS against the
> netlist. The minimum rule set on the filled file of this release is running; LVS and antenna repair are open.

## What changed since rc2
1. **Clock alignment for the single-port SRAMs.** The SRAM wrapper does two accesses per system clock cycle on the
   double-rate clock and needs the SRAM clock not later than the clock of the flip-flops around it. In rc2 the SRAM
   clock arrived up to 7 ns late (10,324 SRAM pins failed hold, independent of frequency). Now the SRAM clock tree
   is taken from the clock root, the root has six repeaters, 16 + 17 delay cells align the two flip-flop clocks
   behind it, and hold repair was run at the fast and the slow corner (7,615 + 315 buffers).
2. **HyperBus read strobe.** The read capture needs the strobe (RWDS) delayed against the data by an on-chip
   delay chain; the top level had none and the layout gave 0.9 ns, against up to 0.8 ns strobe-to-data skew of the
   memory. Twelve delay cells behind the RWDS pad now give 3.7 / 5.4 / 8.5 ns (fast / typical / slow); any value
   between about 1.5 and 18 ns captures the right byte at the 25 MHz bus clock.
3. Routing re-closed after both changes: 0 violations. No macro and no pad was moved.

## State of this candidate (11 November 2026)

| Item | Result |
|---|---|
| Detailed routing (OpenROAD TritonRoute) | 0 violations |
| Power grid check, VDD and VSS | both pass |
| Connectivity of the GDS against the netlist (net trace, see below) | 334,548 signal nets traced, 0 open pins, 0 shorted pins, 0 nets touching a macro without a pin there |
| IHP minimum rule set, deep mode, layout with seal ring, no fill | 23 of 23 rule tables completed, 0 violations |
| Density of this file (Activ, GatPoly, Metal1-4, TopMetal1; global and window rules) | 0 violations, see `density_fullfill.txt` |
| IHP minimum rule set, deep mode, on the full-fill GDS of this release | running (26 tables + GatPoly filler); result follows in the final release |
| Hold, internal paths (static timing, parasitics estimated from placement) | met at the typical and slow corner; fast corner 168 endpoints at -0.03 ns worst, inside the 0.15 ns clock uncertainty |
| Hold at the SRAM pins | +0.27 / +0.57 / +1.05 ns (fast / typical / slow) |
| Setup | met at 50 MHz system clock at the fast corner; 34.6 MHz typical, 21.7 MHz slow (paths into the SRAM pins on the double-rate clock) |
| LVS (deep) | running; it has not completed on this chip yet |
| Antenna check (OpenROAD) | 6,111 nets above the ratio limit (median 1.7 times the limit, 1,314 nets at 3 times or more); a repair of those 1,314 nets with 1,410 diodes is in routing on a copy, not in this file |

Notes on the checks:
- **Nwell table.** In the minimum rule set all four rules of the Nwell table are switched off (`!PRECHECK_DRC`); the
  table only builds whole-chip connectivity and has nothing to report. It is left out of the table count.
- **Net trace.** For every signal net the metal connected to its first pin is followed in the GDS through
  Metal1 to TopMetal1 and all vias, in all cell levels. A pin of the same net that is not reached is an open, a pin
  of another net inside the traced metal is a short. The same run on an earlier database with 16 router violations
  reported the shorted nets (4 net-to-net, 3 to a supply). It is independent of the router's own checks and does
  not replace LVS: devices are not extracted.
- **Input pins.** Six paths from input pads (SPI data in, UART, GPIO) show negative hold against the placeholder
  input delay of the constraints. They are sampled by the system clock after the clock tree delay; their timing
  depends on the board, not on the layout. The HyperBus data inputs show negative hold in the report because the
  constraint models capture of the previous byte; with the strobe delay the current byte is captured (item 2).
- **Fill at the die corners.** Fill shapes at the four chamfered corners are removed in both GDS variants, as in rc2.
- **Standard-cell rows.** The rows carry no filler cells. The minimum rule set is clean without them.

## Contents
- `gds/SoC2611.gds.gz`: whole file (the one `doc/info.json` points at), seal ring + label, PDK lattice fill only
  (under GitHub's 100 MB limit).
- `gds/SoC2611_fullfill.gds.gz.00.part` + `.01.part`: same routing with PDK fill + top-up fill, density clean;
  reassemble with `cat` and check the hash below.
- `gds/SoC2611_fullfill.gds.xz`: the same full-fill GDS as one xz file, if it fits under 100 MB.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog (with the delay cells and
  hold buffers of this release).
- `density_fullfill.txt`: density result of the full-fill GDS.
- `checks/`: DRC table verdict, net trace summary, timing summary.

## Source state
Routed database of 10 November (0 violations) + clock alignment + hold repair + strobe delay chain; marker nets
re-routed until 0 violations. OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.

## SHA-256
```
fb6bd3e3d73dcf0787e960f2caf2d6e2776d0b2037889ba948872f68135eff7f  gds/SoC2611.gds.gz
1051f1fa860f927003dd6515a6ca85cd360e45b20a0a8476301728de8f37d214  gds/SoC2611_fullfill.gds.gz.00.part
25e485dee26d9288abc54b1d3fac736d5864efcae0a412c7e5e620017909a07e  gds/SoC2611_fullfill.gds.gz.01.part
308ddcaf76dcdbd4ef2442a0c798a759c1004f41728596664cad7dbec2b2b0c9  gds/SoC2611_fullfill.gds.xz
f44b52197102b240ad480a09a844b6c94e5d18648912442e35600e87b19a1853  netlist/SoC2611.cdl.gz
b5de229371633f654a79fd1637b46b4e5674e73cea70560283d0b14e6e1c6889  netlist/SoC2611.v.gz
fullfill reassembled (cat the .part files): 8770a929b5e6db7b59db55bd7309d71b26e293c1d5ef7a156ad233dcd62513d2
fullfill uncompressed GDS: 2e1955189786162aee61f5aa8b6227e76dfd351e8278a2bf923ae76597fe0096
```
