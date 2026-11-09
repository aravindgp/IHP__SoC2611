#!/usr/bin/env bash
# Overnight clean-up on the approved database (Grok's order of 9 Nov evening):
#   1. grok_lift/drt_steps.tcl: resume OpenROAD's DRT schedule at pass START (default 17, after the rip-up-all pass,
#      turned into INCR by STEP_ALL_AS_INCR=1) up to END (default 24, before the rip-up-all at 25), 24 threads;
#   2. on any error (or no written db): plain detailed_route END=16 (eco_plain.tcl) on the same input, 24 threads;
#   3. count: pass curve, D1_COUNT line, breakdown, markers inside macro outlines.
# usage: overnight.sh <in.odb> <name> [START=17] [END=24] [THREADS=24]   (outputs in /workspace/chip_fp2/eco/lift)
IN=$1; N=$2; START=${3:-17}; END=${4:-24}; T=${5:-24}
D=/workspace/chip_fp2/eco/lift
S=<design-repo>/HW/asic/signoff
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
W=/root/.claude/jobs/658ac326/tmp/grok_onehour/out/d1_watch.sh
log() { echo "[overnight $(date +%H:%M:%S)] $*"; }
cd /root/.claude/jobs/658ac326/tmp
log "start $N from $IN: drt_steps $START..$END, $T threads"
STEP_IN=$IN STEP_OUT=$D/$N.odb STEP_START=$START STEP_END=$END STEP_THREADS=$T STEP_ALL_AS_INCR=1 \
STEP_DRC_RPT=$D/${N}_drc.rpt $OR -exit $S/grok_lift/drt_steps.tcl > $D/$N.log 2>&1
rc=$?
# "scan markers 0": the INCR scan step did not rebuild the marker list (9 Nov 12:05: 0 markers on a db with 2,548,
# pass 17 "done" in 3 min) -> the step result is empty, not clean; use the plain run.
if [ $rc -ne 0 ] || ! grep -q "DRT_STEPS wrote" $D/$N.log || grep -q -E "^\[ERROR|Error:" $D/$N.log || grep -q "DRT_STEPS scan markers 0$" $D/$N.log; then
  log "drt_steps failed (rc=$rc): $(grep -m1 -E 'ERROR|Error' $D/$N.log | cut -c1-160)"
  log "fallback: plain detailed_route END=16"
  IN_ODB=$IN OUT_ODB=$D/${N}p.odb END=16 THREADS=$T DRC_RPT=$D/${N}p_drc.rpt $OR -exit $S/eco_plain.tcl > $D/${N}p.log 2>&1
  N=${N}p
fi
log "done $N"
grep -a -E "DRT_STEPS pass|Number of violations" $D/$N.log | tail -30 | cut -c1-80
bash $W $D/$N.log $D/${N}_drc.rpt | tail -1
python3 -I $S/drc_breakdown.py $D/${N}_drc.rpt /workspace/chip_fp2/handoff/macros_name_w_h_um.txt $D/d1_place.pl | head -12
log "all done"
