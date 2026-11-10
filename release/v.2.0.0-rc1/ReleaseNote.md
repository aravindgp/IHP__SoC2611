# SoC2611 v.2.0.0-rc1 - release note (10 November 2026, 04:10 UTC)

> **Status: release candidate, not the submission GDS.** Detailed routing is clean for the first time.
> Fill is NOT included in this file, so the density rules are not met yet. Sign-off checks are still running.

## State of this candidate (10 November 2026, 04:15 UTC)

| Item | Result |
|---|---|
| Detailed routing (OpenROAD TritonRoute) | 0 violations |
| Power grid check, VDD and VSS | both pass |
| IHP minimum DRC, deep mode, without fill | **0 violations**, 23 of 23 rule tables completed (10 Nov, 04:58 UTC); seal ring, filler, Nwell and density tables run on the filled GDS |
| LVS (deep) | device extraction done, netlist comparison running |
| Fill and density | running, next candidate |
| Antenna check (OpenROAD) | 6,129 nets above the ratio limit; repair not applied |
| Timing after the last macro moves | not re-checked |

The 48 pad-to-bondpad connections are made by abutment, not by routed wires.

## Contents
- `gds/SoC2611.gds.gz`: routed chip with seal ring and label, no fill.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog.

## How the routing was closed
Starting from 641 router violations: pass-through nets were routed around the congested spots (347), one SRAM
macro was moved by 63.36 um and the same detour applied (174), followed by two runs of plain repair passes (11, then 0).
OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.

## SHA-256
```
c8950ef0c892221ca93f73a0afefa6635842124dc67630f49ea1d61f8040b367  gds/SoC2611.gds.gz
4e7c0a2d2be070534529aadd78cc2e698ef794d0aabeba7ad9297a717face253  netlist/SoC2611.cdl.gz
b91a5f405fe33dcf385530bada2c7e825b9ac7b60b15d7c987c76a1835409fc5  netlist/SoC2611.v.gz
```
