# DRC check of candidate v.2.5.0 on the second machine

**COMPLETE.**

Input: branch `candidate-v.2.5.0` (commit 153e343), `candidate/v.2.5.0/gds/SoC2611.gds.gz`,
sha256 `85ff72aada520f6285deef0a74a4e1f15f371dd63ad505967aa8f556f53e4256` (verified before the run).

Run: `bash run_drc_check.sh 5 8` on host 8e54483c835d, KLayout 0.30.5, IHP-Open-PDK
dcb03b1e2d24250bccbb2e8783d55d2b4f734f14, deep mode, IHP minimum rule set + density deck.
Start 2026-11-13 06:57:32 UTC, density deck end 09:41:46 UTC, tables end 11:38:14 UTC (4 h 41 min).

Result, each table checked by its own "completed in" line:
- 27 of 27 rule tables and the density deck completed; 0 exceptions; 0 processes killed by the system.
- `drc_out/tables/SoC2611_SoC2611_full.lyrdb` (merged by run_drc.py at the end): 72 rule categories, 0 markers.
- `drc_out/rest/SoC2611_SoC2611_density.lyrdb`: 0 markers.
- The deck logs "prboundary_drw has 1 polygons": the new die outline on prBoundary.drawing (189/0) is read.
  (On the earlier candidates this line was "prboundary_drw has 0 polygons".)
- The Nwell table is not part of the run (no rules in the minimum set).

Notes:
- This run overlapped with the last table (seal ring) of the v.2.4.0 run on the same machine until 09:39 UTC.
  Peak process memory of both together: about 116 GB of 128 GB. A guard (`memguard.log`) paused one small
  table of this run with SIGSTOP for 31 s at 08:20:34 UTC and resumed it at 08:21:05; nothing was killed and
  every table has its completion line.
- run_drc.py merges the per-table lyrdb files into `*_full.lyrdb` and removes them, so there is one lyrdb for
  the 27 tables; the per-table evidence is the `*.log` files.
- The "memory of klayout" lines in progress.log are the sum over all klayout processes, of both runs until 09:39.
