# SoC2611 v.1.3.0 - release note (9 November 2026, 09:11 UTC)

> **Status: PRELIMINARY, built overnight for the 9 November deadline.** Routed state after ECO round GT:
> 0 power shorts inside the SRAM macros remain, total detailed-route violations 1760.
> Antenna repair, LVS and timing sign-off not run on this GDS. DRC (IHP minimum deck) running, result to follow.

## Contents
- `gds/SoC2611.gds.gz`: whole file (the one `doc/info.json` points at), seal ring + label, PDK lattice fill only (under GitHub's 100 MB limit).
- `gds/SoC2611_fullfill.gds.gz.00.part` + `.01.part`: same routing with PDK fill + top-up fill, density clean; reassemble with `cat` and check the hash below.
- `gds/SoC2611_fullfill.gds.xz`: the same full-fill GDS as one xz file.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog.
- `density_fullfill.txt`, `density_pdkfill.txt`: density_fast.py results of both variants.

## SHA-256
```
2b63f120ead5179bc90c52ed2706670e6951da9654660a5d1ccb129fdc61c23f  gds/SoC2611.gds.gz
7dfc916d88f7278b11c076611954f1ef4ae313a90501dc91a0d7b8f85da4996f  gds/SoC2611_fullfill.gds.gz.00.part
1e99747c9547c2adba654df58486ae51593236b071d8508af6c5a3c2440fd717  gds/SoC2611_fullfill.gds.gz.01.part
0b73e3a26daa63e43b0d242979d058bb76a3b5c28816f1370ab152e836e52947  gds/SoC2611_fullfill.gds.xz
48ff437888b4ee5f7db76456768ec6186f0191f1c3cb4e66a5d275f56afecce7  netlist/SoC2611.cdl.gz
ea2440f339d1206a93a33468e2a96a4f361a64874b2712c4508525cb41ffff12  netlist/SoC2611.v.gz
fullfill reassembled: 830a4337cb19279d8e834967d83cffd5513374e163d3a92307ed66ef2a6d19c7
```

## Source state
Floorplan H13 + side-move / obstruction ECO rounds A-G (`SoC2611-main/Flow/scripts/signoff/eco_round.sh`), OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.
Known open items: shorts inside the SRAM macros listed above, antenna, hold timing, LVS, waivers.
