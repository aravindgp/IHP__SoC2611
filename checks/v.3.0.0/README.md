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
