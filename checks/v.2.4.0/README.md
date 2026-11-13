# DRC check of candidate v.2.4.0 on the second machine

**COMPLETE.**

Input: branch `candidate-v.2.4.0` (commit 1621fae), `candidate/v.2.4.0/gds/SoC2611.gds.gz`,
sha256 `eb1737985222725ce934cb96c14496ba8e47b4ee0944e47d7dbc9e5374dc82fe` (verified before the run).

Run: `bash run_drc_check.sh 5 8` on host 8e54483c835d, KLayout 0.30.5, IHP-Open-PDK
dcb03b1e2d24250bccbb2e8783d55d2b4f734f14, deep mode, IHP minimum rule set + density deck.
Start 2026-11-13 04:34:52 UTC, density deck end 06:56:01 UTC, tables end 09:38:59 UTC (5 h 4 min).

Result, each table checked by its own "completed in" line:
- 27 of 27 rule tables and the density deck completed; 0 exceptions; 0 processes killed by the system.
- `drc_out/tables/SoC2611_SoC2611_full.lyrdb` (merged by run_drc.py at the end): 72 rule categories, 0 markers.
- `drc_out/rest/SoC2611_SoC2611_density.lyrdb`: 0 markers.
- The Nwell table is not part of the run (no rules in the minimum set).

Notes:
- The seal ring table took 13,456 s (3 h 44 min) instead of about 2 h 56 min because the DRC of
  candidate v.2.5.0 was started on the same machine at 06:57 UTC and shared the 32 CPUs from then on.
- run_drc.py merges the per-table lyrdb files into `*_full.lyrdb` and removes them, so there is one lyrdb for
  the 27 tables; the per-table evidence is the `*.log` files.
- The "memory of klayout" lines in progress.log are the sum over all klayout processes, of both runs after 06:57.
- Peak process memory on the machine: about 117 GB of 128 GB (both runs together). A guard paused one small
  table of the v.2.5.0 run for 31 s at 08:20 UTC; no process of this run was paused or killed.
