# SoC2611 candidate v.3.0.0, for checking (14 November 2026)

**Not a release.** This branch exists so that the checks can run on a second machine straight from GitHub. The
release branch follows when every check has finished. Do not submit from this branch.

`gds/SoC2611.gds.gz` is the complete filled GDS in one file: seal ring, row filler cells, PDK fill and a thinned
top-up fill. Its hash is in `gds/SoC2611.gds.gz.sha256`.

## Why v.3.0.0: a repair that every earlier file needs

Every release up to v.2.4.0 and the candidates v.2.5.0, v.2.3.1 and v.2.4.1 have 384 buffers without a connection on
their input pin. They are the top buffers of the buffer trees of the 22 signals with the most loads, among them the
reset of the system clock domain with about 50,000 loads. A script of the flow built these trees on 30 October; it
moved the loads to the new buffers and did not join the top buffers to the original signal, so the original signal
kept only its driver. With these inputs open the chip would not work.

No earlier check could see it: layout and netlist agreed, so LVS matched; static timing analysis skips a pin without
a driver; the firmware tests ran on the RTL. It was found on 13 November while a simulation of the routed netlist
was being prepared.

In v.3.0.0 each of the 384 inputs is connected to its original signal and the 22 nets are routed. Two checks are new
and are part of this and every later release:
- every input pin of every standard cell, pad and SRAM macro has a net, and every net with loads has a driver;
- the routed netlist is simulated pad to pad: reset, boot from the external memory, six firmware checks, UART.

## What else changed against v.2.5.0

- The 6 nets that were above the limit of the PDK antenna table through TopMetal1 have a buffer with a large gate in
  front of their receiving pin.
- The four longest wires of the fast corner, each about 20 mm long between pins less than 3 mm apart, are laid
  straight.
- The die outline is on prBoundary.drawing (189/0) as in v.2.5.0.
- 26 antenna diodes were added for nets that had to move to make room for the repair wires. The antenna check of
  the router is at 0 nets again, as in v.2.5.0.
- The core supply has more metal between the pad ring and the core. In all earlier files the core current of the
  west and east supply pads reached the power grid over one Metal4 rail of the pad ring, 15.8 um wide, and the north
  and south supply pads were not tied to the power grid at all. New: a TopMetal1 bar per net along the west and east
  side, a TopMetal1 bar on the VDD side of the core ring in the north and south, and ties from the north and south
  pads to the core ring. All of it lies in the empty strip between the pad ring and the core. No signal wire moved.

## State on the build machine when this branch was made

| Check | Result |
|---|---|
| Input pins without a net, all instances | 0 (384 in v.2.5.0) |
| Routing | 0 violations, 0 signal nets without a wire, power grid check passes |
| Antenna check of the router | 0 nets |
| Simulation of the routed netlist, firmware suites | pass: quick suite, full suite (6 of 6) and camera capture with all registers starting at 0; quick suite with two random start patterns, camera capture with one |
| Timing on the routed wires, system clock, fast / typical / slow | 64.4 / 45.5 / 29.4 MHz (54.7 / 45.5 / 29.4 MHz in v.2.5.0) |
| Hold, internal paths, fast / typical / slow | +0.015 / +0.110 / +0.050 ns, met |
| Voltage drop of the core supply at 0.78 W, VDD / VSS, worst | 71 mV / 122 mV (217 mV / 205 mV in v.2.5.0) |
| Density, own calculation, on this file | 0 violations |
| IHP minimum rule set on this GDS | not run yet when the branch was pushed |

The typical and the slow corner are the same as in v.2.5.0. The fast corner is higher because the four longest
wires are laid straight. The 22 repaired signals were not timed in any earlier file, because a timing run skips a pin
without a net. They are timed now: the reset reaches every flip-flop with 1.50 ns to spare at the slow corner, and
the slowest path through a repaired signal still allows 32.3 MHz at the slow corner, above the 29.4 MHz that the chip
as a whole reaches there.

The voltage drop is new in this note. It is computed with the supply rails of the pad ring as real wires and the
four supply pads of each net as the sources, at the fast corner with 0.78 W (100 MHz input clock, one signal in ten
switching per cycle). For the layout of v.2.5.0 an analysis that takes the rails as ideal shows 17 mV and 27 mV where
this one shows 217 mV and 205 mV.

## Run the check on another machine

```
git clone --depth 1 -b candidate-v.3.0.0 https://github.com/aravindgp/IHP__SoC2611
cd IHP__SoC2611/candidate/v.3.0.0
bash run_drc_check.sh 5 8          # all 27 tables and the density deck, 5 tables at a time, 8 threads per table
```

The script fetches the rule deck from the public IHP-Open-PDK repository at the commit the design was built with,
unpacks the GDS and runs the IHP minimum rule set in deep mode. Needs: git, Python 3, KLayout 0.30.x with
`pip install klayout docopt`. Memory: about 14 GB per table; the GatPoly filler table takes about 20 GB at 8
threads and about 100 GB at 16 threads, so keep it at 8 when tables run side by side. The run of v.2.4.0 with
these options took 5 h 4 min.

To share the work with the build machine, only the long tables can be run here:
`TABLES="sealring gatpolyfiller" DENSITY=1 bash run_drc_check.sh 2 8`

## What to send back

`work/drc_out/progress.log` and every `*.lyrdb` and `*.log` file under `work/drc_out/`, committed under
`checks/v.3.0.0/` on a new branch `checks-v.3.0.0`. They are the evidence the release carries for each table.
