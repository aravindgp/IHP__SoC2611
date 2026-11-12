# DRC check of candidate v.2.2.0 on the second machine

Input: branch `candidate-v.2.2.0` (commit 4286272), `candidate/v.2.2.0/gds/SoC2611.gds.gz`,
sha256 `01aa56f73661f142738e370092350b33e90814bf982c05e5862501ccdf90c584` (verified before the run).

Run: `bash run_drc_check.sh 5 8` on host 8e54483c835d, KLayout 0.30.5, IHP-Open-PDK
dcb03b1e2d24250bccbb2e8783d55d2b4f734f14, deep mode, IHP minimum rule set + density deck.
Start 2026-11-12 17:03:41 UTC, density deck end 20:35:54 UTC, tables end 22:37:07 UTC.

Result, checked per table by its own "completed in" line:
- 27 of 27 rule tables and the density deck completed; 0 exceptions; 0 processes killed by the system.
- `drc_out/tables/SoC2611_SoC2611_full.lyrdb` (merged by run_drc.py): 72 rule categories, 0 markers.
- `drc_out/rest/SoC2611_SoC2611_density.lyrdb`: 0 markers.
- The Nwell table is not part of the run (no rules in the minimum set).

Note: run_drc.py merges the per-table lyrdb files into `*_full.lyrdb` and removes them, so there is one
lyrdb for the 27 tables. The "memory of klayout" lines in progress.log are the sum over all klayout processes.
Peak process memory on the machine during the run: about 99 GB of 128 GB.
