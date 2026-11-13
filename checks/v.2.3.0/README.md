# DRC check of candidate v.2.3.0 on the second machine

**PARTIAL (snapshot 2026-11-13 02:50 UTC): the seal ring table is still running.** This file and the
folder are updated when it ends.

Input: branch `candidate-v.2.3.0` (commit f322b5b), `candidate/v.2.3.0/gds/SoC2611.gds.gz`,
sha256 `652972ef692cff275e34ff16568ca1c744652846ebda3300160a36b2e11a7ebe` (verified before the run).

Run: `bash run_drc_check.sh 5 8` on host 8e54483c835d, KLayout 0.30.5, IHP-Open-PDK
dcb03b1e2d24250bccbb2e8783d55d2b4f734f14, deep mode, IHP minimum rule set + density deck.
Start 2026-11-12 23:56:47 UTC; density deck end 2026-11-13 02:21:15 UTC.

State at the snapshot, each table checked by its own "completed in" line:
- 26 of 27 rule tables and the density deck completed; 0 exceptions; 0 processes killed by the system.
- 27 result files (`drc_out/tables/*.lyrdb` per table, `drc_out/rest/*density.lyrdb`): 0 markers in every one.
- Seal ring table: running since 01:21 UTC, in rule Seal.l; its log is incomplete here and it has no lyrdb yet.
- The Nwell table is not part of the run (no rules in the minimum set).

Note: the "memory of klayout" lines in progress.log are the sum over all klayout processes.
