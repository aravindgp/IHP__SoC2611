# SoC2611 v.1.3.1 - release note (9 November 2026, 11:11 UTC)

> **Status: PRELIMINARY, built overnight for the 9 November deadline.** Routed state after ECO round GC:
> 0 power shorts inside the SRAM macros remain, total detailed-route violations 1624.
> Antenna repair, LVS and timing sign-off not run on this GDS. DRC (IHP minimum deck) running, result to follow.

## Contents
- `gds/SoC2611.gds.gz`: whole file (the one `doc/info.json` points at), seal ring + label, PDK lattice fill only (under GitHub's 100 MB limit).
- `gds/SoC2611_fullfill.gds.gz.00.part` + `.01.part`: same routing with PDK fill + top-up fill, density clean; reassemble with `cat` and check the hash below.
- `gds/SoC2611_fullfill.gds.xz`: the same full-fill GDS as one xz file.
- `netlist/SoC2611.cdl.gz`, `netlist/SoC2611.v.gz`: LVS netlist and post-route Verilog.
- `density_fullfill.txt`, `density_pdkfill.txt`: density_fast.py results of both variants.

## SHA-256
```
3497ba25685664cba3942359f5524a5cf086f493afe95ca703dddb0748ee12cc  gds/SoC2611.gds.gz
72f39b87ca1120af2fd4992356bcdbef885ac40d087f9a4d3b129d86d03b05ab  gds/SoC2611_fullfill.gds.gz.00.part
464aae7054af0bfcdf90fc1944bdb6b86b980edf866396dc04dc71ae5a56b016  gds/SoC2611_fullfill.gds.gz.01.part
21397ca3c5b1dd5229e3139691873e16f54399d82add2ce87f2096cc3ad9641c  gds/SoC2611_fullfill.gds.xz
4f9e03d8b0f5bb45585c73b8ca54c9047b95931f7e26d6cc4653911739a88dd9  netlist/SoC2611.cdl.gz
81c06b0fb2a04c1f3d0be922af869c48f16325f36b5c95c0b3361f6564759def  netlist/SoC2611.v.gz
fullfill reassembled: f825cb3cf6d1307ac6e26d38206b8358d0602b1c5773be449227f63dd1f94487
```

## Source state
Floorplan H13 + side-move / obstruction ECO rounds A-G (`SoC2611-main/Flow/scripts/signoff/eco_round.sh`), OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified.
Known open items: shorts inside the SRAM macros listed above, antenna, hold timing, LVS, waivers.
