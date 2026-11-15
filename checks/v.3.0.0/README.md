# DRC check of candidate v.3.0.0 on the second machine (long tables)

**COMPLETE.**

Input: branch `candidate-v.3.0.0` (commit 3ee45fe), `candidate/v.3.0.0/gds/SoC2611.gds.gz`,
sha256 `c6f22d10f31cf8b4a31dc43026164ea1c3bdd87dcc0786c64c068290b37bc92a` (verified before the run).
`run_drc_check.sh` identical to the one of v.2.5.0.

Run: `TABLES="gatpolyfiller sealring" DENSITY=1 bash run_drc_check.sh 3 8` on host 8e54483c835d, KLayout 0.30.5,
IHP-Open-PDK dcb03b1e2d24250bccbb2e8783d55d2b4f734f14, deep mode, IHP minimum rule set + density deck.
Start 2026-11-14 00:48:42 UTC, end 03:47:53 UTC (2 h 59 min). Nothing else ran on the machine.
The other 25 tables are run on the build machine.

Result, each checked by its own "completed in" line:
| Check | Completed in | Markers |
|---|---|---|
| GatPoly filler table (6.x) | 7,030 s (1 h 57 min) | 0 |
| Seal ring table (6.10) | 10,741 s (2 h 59 min) | 0 |
| Density deck | 8,241 s (2 h 17 min) | 0 |

- `drc_out/tables/SoC2611_SoC2611_full.lyrdb` (merged by run_drc.py): 3 rule categories (GFil.d, Seal.l, Seal.n), 0 markers.
- `drc_out/rest/SoC2611_SoC2611_density.lyrdb`: 0 markers. Density log: Metal3 38.50 %, Metal4 39.47 %,
  TopMetal1 34.22 %, all inside the limits.
- 3 of 3 finished; 0 processes killed by the system; 0 exceptions. Peak klayout memory (sum) 73.9 GB.
- The deck logs "prboundary_drw has 1 polygons": the die outline on prBoundary.drawing (189/0) is read.
- `launch.log` is the console output of run_drc_check.sh.

## Added 2026-11-15: PDK antenna table and NWell geometry rules (not part of the minimum rule set)

### Antenna table (`antenna/`): CLEAN
`run_drc.py --path=SoC2611.gds --topcell=SoC2611 --run_mode=deep --antenna_only --density_thr=16`, same PDK commit.
2026-11-14 03:56 → 07:32 UTC (12,983 s), peak about 21 GB. 23 rule categories (Ant.a, Ant.c, Ant.b/Ant.e for
Metal1–TopMetal1, Ant.d/Ant.f for Via1–TopVia1, Ant.g, Ant.h, Ant.i), **0 markers**. Deck reads the design as
6600.0 um * 6600.0 um.

### NWell geometry without connectivity (`nwell/`): 2 NW.b markers
The PDK nwell table runs no rules with `--minimum_drc` and its full version hangs in connectivity setup on this
chip, so `nwell/nwell_noconn.drc` checks the geometric NWell rules (values from sg13cmos5l_tech_default.json).
2026-11-14 03:55 → 07:27 UTC (19,154 s).

| Rule | Markers |
|---|---|
| NW.a width >= 0.62 | 0 |
| NW.b space >= 0.62 | **2** |
| NW.c / NW.d / NW.e enclosure and space to Activ, and both straddle checks | 0 |
| NW.b1 candidates (space < 1.80, net-blind, review only) | 13: 11 at the two NW.b spots, 4 inside library cells (DFNQX2, DFNQMX2IX1, SRAM COLCTRL2, lgcp_1) |

Both NW.b markers are at the top-right corner of an SRAM macro `RM_IHPSG13_1P_64x16_c2`:
- x 1630.41–1631.27, y 2995.025–2995.510: macro (1394.08,2930.44;1630.88,2995.025); its NWell ends at
  y 2995.025, the NWell of `sg13cmos5l_tiehi` + `fill_2` in the row above starts at y 2995.510, overlapping
  the macro by 0.08 um in x. Gap 0.485 um < 0.62.
- x 3120.33–3121.11, y 2995.025–2995.500: macro (2883.92,2930.44;3120.72,2995.025); NWell of `sg13cmos5l_fill_4`
  + `dfrbpq_1` above starts at x 3120.72 (corner on corner), y 2995.500. Gap 0.475 um < 0.62.

The same cells and NWell edges are in v.2.5.0, so this is not new in v.3.0.0. Fix options: keep the standard cells
next to these two corners at least 0.62 um (1.80 um if the macro NWell is on a different net) away in x, or join
the two NWells if both are VDD.
