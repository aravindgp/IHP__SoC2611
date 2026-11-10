# SoC2611 v.2.0.0-rc2 - release note (10 November 2026, 12:54 UTC)

> **Status: release candidate with fill.** Detailed routing is clean and the IHP minimum rule set is clean on 25 of
> 28 rule tables of this exact file; the three slowest tables, LVS and antenna repair are still open (see below).

## State of this candidate (10 November 2026)

| Item | Result |
|---|---|
| Detailed routing (OpenROAD TritonRoute) | 0 violations |
| Power grid check, VDD and VSS | both pass |
| Density (Activ, GatPoly, Metal1-4, TopMetal1; global and window rules) | 0 violations, see `density_fullfill.txt` |
| IHP minimum rule set, deep mode, on the full-fill GDS of this release | 25 of 28 rule tables completed, 0 violations (Metal1, Metal2-4, vias, TopMetal1, Activ / Metal / TopMetal1 filler, wells, contacts, pads, pins, latch-up, forbidden layers, ...) |
| Nwell, seal ring and GatPoly filler tables on this file | running (the seal ring table is 0 on the same layout without fill) |
| LVS (deep) | device extraction done, netlist comparison running |
| Antenna check (OpenROAD) | 6,129 nets above the ratio limit; repair in progress on a copy, not in this file |
| Timing after the last macro move | not re-checked |

Fill shapes at the four chamfered die corners (34 fill-to-metal spacing findings on the file before this step) are
removed in both GDS variants of this release.

## Contents
- `gds/SoC2611.gds.gz`: whole file (the one `doc/info.json` points at), seal ring + label, PDK lattice fill only
  (under GitHub's 100 MB limit).
- `gds/SoC2611_fullfill.gds.gz.00.part` + `.01.part`: same routing with PDK fill + top-up fill, density clean;
  reassemble with `cat` and check the hash below. This is the file the DRC results above refer to.
- `gds/SoC2611_fullfill.gds.xz`: the same full-fill GDS as one xz file, if it fits under 100 MB.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog.
- `density_fullfill.txt`: density result of the full-fill GDS.

## Source state
Routing closed on 10 November (641 -> 0 violations): pass-through nets routed around the congested spots, one SRAM
macro moved by 63.36 um, repair passes. OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.

## SHA-256
```
8ca2c3a588dc828821e5064814ea70179ed7c6783ebaa384167bea36fa31f31a  gds/SoC2611.gds.gz
f1c6dd80cf4443af371b6ad695eae611a075a10bc2d6080bc646efb184eb1461  gds/SoC2611_fullfill.gds.gz.00.part
95a402f3aa7ade4de56f889498f78c621c4d708d57b87a2ed18d6dd21892d388  gds/SoC2611_fullfill.gds.gz.01.part
01660b606ce3969ddb69e3d89571caad8251ea9154c552ffad710a2d70accd7a  gds/SoC2611_fullfill.gds.xz
50d0ab135ab0b1866d698eae3cb105976ff8f0fe79ea78076fa1a2bcbc50d3b9  netlist/SoC2611.cdl.gz
75540f01169448c724dd3a5753f6af2b0a4f6b573349cc918b46120a9a6f6272  netlist/SoC2611.v.gz
fullfill reassembled (cat the .part files): 8cd5c342e01dfe4259b06e560962e0f415fc0803bbd383e3d2cac8c1322f5119
fullfill uncompressed GDS: 5af965fc85b743ca22e90994e0346afa78758dd33d44f2c8c6ee67a3944e7c0f
```
