# SoC2611 v.1.1.0 — release note (8 November 2026)

> **Status: PRELIMINARY — not for fabrication.** Best routed state of the re-floorplanned chip at the time of
> writing; detailed routing has not converged, DRC/LVS have not been run on this GDS. A final release will replace
> this one. v.1.0.0 is kept for reference.

## Contents
- GDS: `gds/SoC2611.gds.gz` (157 MB) is stored as two parts because GitHub refuses files above 100 MB:
  `gds/SoC2611.gds.gz.00.part` + `gds/SoC2611.gds.gz.01.part`. Reassemble with
  `cat SoC2611.gds.gz.00.part SoC2611.gds.gz.01.part > SoC2611.gds.gz` and check the SHA-256 below (the hash is of
  the reassembled file). The same file is attached whole to the GitHub release tag `v.1.1.0` when available.
  Content: top cell `SoC2611`, die 6600 x 6600 um, seal ring with the device
  registration label, PDK density fill (Activ/GatPoly, Metal1-4, TopMetal1; SRAM macros as keep-out outlines)
  plus top-up fill, saved with the KLayout options of Open-Silicon-MPW (GDS2, dbu 0.001, no PCell/library
  context, zero-length paths eliminated).
- Netlists: `netlist/SoC2611.cdl.gz` (LVS netlist, 327,956 instances; IHP standard cells, SRAM and IO cells as
  library subcircuits; the 64 bondpads have no CDL model), `netlist/SoC2611.v.gz` (post-route Verilog).
- Documentation: `../../doc/` (Specification, Datasheet with the QFN64 pinout).

## SHA-256
| file | sha256 |
|---|---|
| gds/SoC2611.gds.gz | ba6945e77c195cc825f95c91877af820275d6e6be2b628da53df548206d283d2 |
| netlist/SoC2611.cdl.gz | 6b0dbc45ec3a55e557df9af49f31d9c5302982fef03f1322be0a557e99e2126e |
| netlist/SoC2611.v.gz | 761d79494ac04f4a51d9e1b5015558d8056a2c7799726e29442347f25312f524 |

## Source state
- Floorplan H10 (hand floorplan H4 + two placement blockages, `SoC2611-main/Flow/floorplan/`), DGSE flow on
  OpenROAD dcf36133, IHP-Open-PDK dcb03b1e2d24250bccbb2e8783d55d2b4f734f14 / ihp-sg13cmos5l unmodified.
- Detailed route snapshot after pass 61 of the 64-pass schedule: **1,005 remaining violations** (down from 392,430
  at pass 0), about 860 of them Metal4 shorts between pass-through signal wires and the SRAM macros' power-pin
  stripes inside the macros (root cause and fix in progress: `../../STATUS_2026-11-08.md`).
- Density (`density_fast.py`, same windows and limits as the PDK density deck): **0 violations**, all Activ/GatPoly/
  Metal1-4/TopMetal1 rules PASS (global TopMetal1 33.1 %).
- Antenna: not repaired on this snapshot (about 6,000 violating nets; repair rehearsed, see the status note).
- Scripts to reproduce every step: `SoC2611-main/Flow/scripts/signoff/` (chip_finish.tcl, stream_chip.sh,
  release_gds_chain.sh = make_sealring.py + fill_tiled.py + fill_topup.py + density_fast.py, make_chip_cdl.sh,
  ihp_release.py, ihp_sealring_label.py, ihp_repo_docs.py), dated log `SoC2611-main/Flow/ROUTING_CLOSURE_LOG.md`.

## Known open items
Detailed routing not converged (shorts inside the SRAM macros, metal spacing), antenna repair, hold timing on
CPU-SRAM paths, DRC (IHP minimum deck) and LVS not run on this GDS, testbenches/simulation logs, self-contained
synthesis script.
