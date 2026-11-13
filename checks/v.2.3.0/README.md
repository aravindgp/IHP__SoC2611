# DRC check of candidate v.2.3.0 on the second machine

**COMPLETE.** (A partial snapshot without the seal ring table was pushed at 2026-11-13 02:50 UTC.)

Input: branch `candidate-v.2.3.0` (commit f322b5b), `candidate/v.2.3.0/gds/SoC2611.gds.gz`,
sha256 `652972ef692cff275e34ff16568ca1c744652846ebda3300160a36b2e11a7ebe` (verified before the run).

Run: `bash run_drc_check.sh 5 8` on host 8e54483c835d, KLayout 0.30.5, IHP-Open-PDK
dcb03b1e2d24250bccbb2e8783d55d2b4f734f14, deep mode, IHP minimum rule set + density deck.
Start 2026-11-12 23:56:47 UTC, density deck end 2026-11-13 02:21:15 UTC, tables end 04:16:35 UTC (4 h 20 min).

Result, each table checked by its own "completed in" line:
- 27 of 27 rule tables and the density deck completed; 0 exceptions; 0 processes killed by the system.
- `drc_out/tables/SoC2611_SoC2611_full.lyrdb` (merged by run_drc.py at the end): 72 rule categories, 0 markers.
- `drc_out/rest/SoC2611_SoC2611_density.lyrdb`: 0 markers.
- Seal ring table: completed in 10,541 s, 0 markers (part of the merged file).
- The Nwell table is not part of the run (no rules in the minimum set).

Files: the per-table `*.lyrdb` files in `drc_out/tables/` are from the partial snapshot (26 tables, 0 markers
each); run_drc.py removes them locally when it writes `*_full.lyrdb`, which is the authoritative merged result.
The "memory of klayout" lines in progress.log are the sum over all klayout processes.
Peak process memory on the machine during the run: about 98 GB of 128 GB (sampled every 30 s).
