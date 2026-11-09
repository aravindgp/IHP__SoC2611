# Runbook: close the DSOC2610 chip route (run B + west-band ECO "run D")

Written 3 Nov 2026 23:45 IST. Execute step by step; every step has a gate. Do not reason past a failed gate: stop
and report. Paths: `S=/root/DGrid-SoC1/.claude/worktrees/asic-rtl-prep/HW/asic/signoff`,
`OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad`, work dir `/workspace/chip_drt`.
Shell rules on this pod: plain commands only (no `sed -n Np`, no `xargs sh`, no `cd` chains outside the worktree);
side jobs through `$S/lowprio.sh`; keep the pod under 95 GB (run B ~17 GB, a check_drc ~15 GB, a DRT ~16 GB).

## Diagnosis (why run B alone is likely to stall)

* Run B (DRT, `/workspace/chip_drt/stripB`, PID 459562, 30 threads) pass 13 = 67,430. Per-layer table: M4 shorts
  34.4k -> 31.2k (-9 %/pass, core, closing); **M3 shorts 16.5k -> 16.0k (-3 %/pass) = the west IO band, stalling.**
* Mechanism: PCORE 0 register-file nets leave SRAM column 1 (x 365.7..602.5 um) through the 50 um gaps between the
  stacked macros; column 2 (x >= 652.9) blocks M1-M4 eastwards, so they detour north/south in the 46 um strip
  (x 320..365.7) and overflow into the IO band (x 140..320) where the IO-cell supply rails (PINs on M3/M4/TM1) short
  them. GRT put them there: `-allow_congestion` overflows into blocked gcells. Run C's obstructions left Metal2
  open (1,774 M2 guide boxes in the band) and its M3 derate 0.30 doubled the M3 shorts -> run C stopped.
* Resources the ECO must use instead: Metal2 and Metal4 are VERTICAL (pitch 0.42: ~110 tracks each in the 46 um
  strip); TopMetal1 is VERTICAL (pitch 3.28) and free over the SRAMs except the 16 um-pitch PDN stripes.
* GRT on ~800 stripped nets takes ~3 min (run C: 2:17) -> GRT configurations are cheap to iterate; DRT is not.

## Track A: keep run B (always on)

After every `Number of violations` line in `/workspace/chip_drt/stripB/drt_chip.log`, append to
`HW/asic/dgse/runs/NOTES.md`: pass, IST time, count, and the `Short` row of the `Viol/Layer` table. Do nothing else
to run B unless Track B says so.

## Track B: west-band ECO = run D (start now, in parallel, 8 threads)

0. **Baseline.** `check_drc` on `stripB/drt_snap/drt_iter13.odb` is running (`/workspace/chip_drt/hotspot/chkB13.log`,
   report `runB_iter13_drc.rpt`). When `HOTSPOT_DONE` appears: `python3 $S/drc_zones.py hotspot/runB_iter13_drc.rpt`.
   Record W13 = the `IO band 140-320 W` count (pass 12 was 10,853 of 19,097). If W13 < 0.7 * 10,853, the band IS
   closing in run B: skip Track B, keep run B, report.
1. **Nets to strip** (`mkdir -p /workspace/chip_drt/runD`):
   a. write_def of drt_iter13 (2-line tcl: `read_db ...; write_def /workspace/chip_drt/runD/snap.def`), then
      `python3 $S/def_margin_nets.py runD/snap.def runD/nets_band.txt 318 6282` (nets with wires in any IO band).
   b. nets named in west-band markers: from `runB_iter13_drc.rpt`, every `net:<name>` in a violation whose bbox
      centre has x < 320 um, excluding `IOVSS`, `IOVDD`, `VDD`, `VSS` -> `runD/nets_mark.txt`.
   c. `sort -u nets_band.txt nets_mark.txt > runD/nets.txt`. Gate: 500..3,000 nets. Delete snap.def.
2. **Obstruct ALL routing layers over the band and strip:**
   `IN_ODB=stripB/drt_snap/drt_iter13.odb OUT_ODB=runD/chip_obs.odb NETS_TXT=runD/nets.txt
   OBS_LAYERS="Metal1 Metal2 Metal3 Metal4 TopMetal1" $OR -exit -no_init $S/chip_io_obs.tcl > runD/1_obs.log`.
   Gate: log says `stripped the routing of N nets` with N within 10 % of the list.
3. **GRT (3 min):** `LAYER_ADJUST="TopMetal1 0.0" CONG_ITERS=10 IN_ODB=runD/chip_obs.odb OUT_ODB=runD/chip_grt.odb
   BPINS_TCL=runD/bpins_unused.tcl GUIDE=runD/route.guide THREADS=8 $OR -exit -no_init $S/chip_grt.tcl > runD/2_grt.log`.
   Do NOT derate Metal3 (run C's 0.30 doubled the M3 shorts); the script's uniform 0.05 stays.
   **Gate G1:** `python3 $S/guide_band.py runD/route.guide` -> total boxes in the band < 300 (run C had 6,049; W side
   must be < 100). If G1 fails: add to a copy of chip_grt.tcl, before `global_route`, four
   `set_global_routing_region_adjustment {x0 y0 x1 y1} -layer L -adjustment 0.95` calls per layer Metal2..TopMetal1
   with the rectangles strictly inside the die: W `141 141 317 6459`, E `6283 141 6459 6459`, S `141 141 6459 317`,
   N `141 6283 6459 6459` (um; 1.0 underflowed to 65535 on 3 Nov, 0.95 is the test). Re-run GRT, re-gate. If G1 still
   fails: STOP Track B, report "GRT will not leave the band", keep run B.
4. **DRT:** `STEP_IN=runD/chip_grt.odb STEP_OUT=runD/chip_droute.odb STEP_START=0 STEP_END=64 STEP_THREADS=8
   STEP_SNAPSHOT_DIR=runD/drt_snap STEP_DRC_RPT=runD/chip_route_drc.rpt $OR -exit -no_init
   $S/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl > runD/drt_chip.log 2>&1 &` (nohup/background; never inside the DGSE
   driver). Expect pass 0..2 in ~15-20 min each, pass 3 ~1 h at 8 threads.
   **Gate G2 (after pass 3, drt_iter3.odb written):** `check_drc` on `runD/drt_snap/drt_iter3.odb` (lowprio, 4 threads,
   ~15 min) -> `drc_zones.py`. PASS if `IO band 140-320 W` < 0.5 * W13 AND total markers <= run B's latest. Then raise
   run D to 16 threads at the next pass boundary (kill, restart `drt_steps` with `STEP_START=0 STEP_IN=<newest
   drt_iter<N>.odb>` — plain restart, never STEP_START>0: that resume path gives a false clean) and, once run D's
   `Number of violations` is below run B's, `kill 459562` (run B) and restart run D at 30 threads the same way.
   FAIL: kill run D, keep run B, report; the fallback is the extension request to IHP (owner's e-mail).

## Clean-route chain (whichever run reaches 0 first; ~1 day)

1. `chip_finish.tcl` with `BPINS_TCL=/workspace/chip_drt/stripB/bpins.tcl` (restores the bondpad pins) ->
   `chip.odb/.def/.v`. 2. `stream_chip.sh`. 3. seal ring + label (`make_sealring.py`, `ihp_sealring_label.py`).
4. `fill_tiled.py --abstract-macros "RM_IHPSG13_.*"` -> `fill_topup.py` -> `density_fast.py` (gate: 0 density errors).
5. IHP precheck DRC (`run_drc.sh` minimum deck) on the filled GDS: gate 0 unwaived. 6. `ihp_release.py`,
   `ihp_repo_docs.py ... final`, commit + push `IHP__DSOC2610`, report hashes on issue #79 (owner posts).

## Dates (IST)

Clean route: late 5 Nov at best, 6 Nov likely; final GDS 7-8 Nov; 9 Nov at risk. Owner decides on the extension
e-mail to IHP (K. Herman).
