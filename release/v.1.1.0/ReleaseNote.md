# SoC2611 v.1.1.0 — release note (8 November 2026)

> **Status: PRELIMINARY — not for fabrication.** Best routed state of the re-floorplanned chip at the time of
> writing; detailed routing has not converged, DRC/LVS have not been run on this GDS. A final release will replace
> this one. v.1.0.0 is kept for reference.

## Contents
- GDS, whole file (the one `doc/info.json` points at): `gds/SoC2611.gds.gz` (86.6 MB): top cell `SoC2611`,
  die 6600 x 6600 um, seal ring with the device registration label, PDK density fill (Activ/GatPoly, Metal1-4,
  TopMetal1 fill recipes; SRAM macros as keep-out outlines), saved with the KLayout options of Open-Silicon-MPW
  (GDS2, dbu 0.001, no PCell/library context, zero-length paths eliminated). It carries the PDK lattice fill only;
  the top-up fill that brings every density window to PASS is in the full-fill variant below (that file is 157 MB
  and exceeds GitHub's 100 MB file limit, so it is stored in two parts).
- GDS, full-fill variant: `gds/SoC2611_fullfill.gds.gz.00.part` + `gds/SoC2611_fullfill.gds.gz.01.part`
  (same routing and seal ring, PDK fill plus top-up fill, density 0 violations). Reassemble with
  `cat SoC2611_fullfill.gds.gz.00.part SoC2611_fullfill.gds.gz.01.part > SoC2611_fullfill.gds.gz` and check the
  SHA-256 below (hash of the reassembled file).
- Netlists: `netlist/SoC2611.cdl.gz` (LVS netlist, 327,956 instances; IHP standard cells, SRAM and IO cells as
  library subcircuits; the 64 bondpads have no CDL model), `netlist/SoC2611.v.gz` (post-route Verilog).
- Documentation: `../../doc/` (Specification, Datasheet with the QFN64 pinout).

## SHA-256
| file | sha256 |
|---|---|
| gds/SoC2611.gds.gz (whole file, PDK fill) | 64dcfd8833b9fe7e78a5c78c7cf8bc9b1993997bb08759104563fbc72e68f260 |
| gds/SoC2611_fullfill.gds.gz (reassembled from the two parts) | ba6945e77c195cc825f95c91877af820275d6e6be2b628da53df548206d283d2 |
| netlist/SoC2611.cdl.gz | 70c5af94165ebacc06efb723019f8aaabb4d3345e7eb927e446a76fbbb534fbe |
| netlist/SoC2611.v.gz | 742ff72190006af11e327ae533a2503c58210a9023a2c5529c0e665a29d0041e |

## Source state
- Floorplan H10 (hand floorplan H4 + two placement blockages, `SoC2611-main/Flow/floorplan/`), DGSE flow on
  OpenROAD dcf36133, IHP-Open-PDK dcb03b1e2d24250bccbb2e8783d55d2b4f734f14 / ihp-sg13cmos5l unmodified.
- Detailed route snapshot after pass 61 of the 64-pass schedule: **1,005 remaining violations** (down from 392,430
  at pass 0), about 860 of them Metal4 shorts between pass-through signal wires and the SRAM macros' power-pin
  stripes inside the macros (root cause and fix in progress: `../../STATUS_2026-11-08.md`).
- Density (`density_fast.py`, same windows and limits as the PDK density deck): full-fill variant **0 violations**,
  all Activ/GatPoly/Metal1-4/TopMetal1 rules PASS (global TopMetal1 33.1 %). Whole-file (PDK-fill-only) variant:
  **84 violations** — Metal2 global 29.7 % (limit >= 35 %), and 4 / 69 / 10 windows of Metal1 / Metal2 / Metal3
  below the 25 % window minimum (15.6-24.9 %); Activ, GatPoly, Metal4 and TopMetal1 pass. The top-up fill of the
  full-fill variant removes all of them; the final release will be a single density-clean file within the size
  limit.
- Antenna: not repaired on this snapshot (about 6,000 violating nets; repair rehearsed, see the status note).
- Scripts to reproduce every step: `SoC2611-main/Flow/scripts/signoff/` (chip_finish.tcl, stream_chip.sh,
  release_gds_chain.sh = make_sealring.py + fill_tiled.py + fill_topup.py + density_fast.py, make_chip_cdl.sh,
  ihp_release.py, ihp_sealring_label.py, ihp_repo_docs.py), dated log `SoC2611-main/Flow/ROUTING_CLOSURE_LOG.md`.

## Known open items
Detailed routing not converged (shorts inside the SRAM macros, metal spacing), antenna repair, hold timing on
CPU-SRAM paths, DRC (IHP minimum deck) and LVS not run on this GDS, testbenches/simulation logs, self-contained
synthesis script.
