# SoC2611 v.1.2.0 - release note (9 November 2026, 06:48 UTC)

> **Status: PRELIMINARY, not for fabrication.** Routed state after ECO round H (9 Nov, 05:17 UTC): 42 power shorts
> between signal wires and the SRAM macros' VDD/VSS stripes inside the macros remain, on 17 nets, 5 of which touch
> both VDD and VSS; 1,433 detailed-route violations in total, about 1,200 of them signal-to-signal shorts in one
> congestion knot around the dp_sink3 / dp_fetch SRAM block (see `../../STATUS_2026-11-09.md`). Density (PDK fill +
> top-up, `density_fullfill.txt`): 0 violations. Antenna repair, LVS and timing sign-off not run on this GDS.
> Superseded the same day by v.1.3.0.

## Contents
- `gds/SoC2611.gds.gz`: whole file (the one `doc/info.json` points at), seal ring + label, PDK lattice fill only (under GitHub's 100 MB limit).
- `gds/SoC2611_fullfill.gds.gz.00.part` + `.01.part`: same routing with PDK fill + top-up fill, density clean; reassemble with `cat` and check the hash below.
- `gds/SoC2611_fullfill.gds.xz`: the same full-fill GDS as one xz file.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog.
- `density_fullfill.txt`, `density_pdkfill.txt`: density_fast.py results of both variants.

## SHA-256
```
cca7929aedf4ede27b340335021e44c7a5872ec3185c90798e83846b5955ce45  gds/SoC2611.gds.gz
b10bc2d86c1ad95dd498c8f37cdb7c1235db7997dd227fd6b655d861c26cdee3  gds/SoC2611_fullfill.gds.gz.00.part
f2bcbd5fd52d58fa5e367dad213fab158ae9ccdb6518708ab3a1d973489b3d87  gds/SoC2611_fullfill.gds.gz.01.part
2d08a727115946bb01c7fe224e67e7d5c14b77bab1cbf866199fb2dd5603bc23  gds/SoC2611_fullfill.gds.xz
3139e921ec57f55301ba935f40fa7ac83421bd8f5e8f66bb4c3aad4d6234f9b6  netlist/SoC2611.cdl.gz
f999af70b3819c99823054d8ecee48d654fa2c083c8572ff4b297203bfb9635b  netlist/SoC2611.v.gz
fullfill reassembled: 1252c2b2fa831ac43c07d18c4858ba6b50c807211b3aa1135be754289f97d11f
```

## Source state
Floorplan H13 + side-move / obstruction ECO rounds A-G (`SoC2611-main/Flow/scripts/signoff/eco_round.sh`), OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.
Known open items: shorts inside the SRAM macros listed above, antenna, hold timing, LVS, waivers.
