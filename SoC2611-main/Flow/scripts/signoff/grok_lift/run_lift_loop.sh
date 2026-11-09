#!/usr/bin/env bash
# One staged macro-move loop (~20-30 min): dry run -> staged ECO (move + PDN fix + strip + ONE incremental GRT)
# -> resumed DRT (drt_steps.tcl, never a plain detailed_route) -> count + supply check. Nothing overwrites IN_ODB.
# usage: run_lift_loop.sh <IN_ODB> <TAG> <SHIFT_FILE> [EXTRA_NETS]
#   env: SIGNOFF=<repo>/Flow/scripts/signoff  DGSE=<repo>/Flow/scripts/dgse  OUTD=/workspace/knot2/out
#        PACK=/workspace/knot2/knot_pack_v2_20261109  KNOT1=/workspace/knot/out (knot_measure.sh, knot_analyze.py)
#        THREADS=8 START=17 END=19 MAX_NETS=450 TM1_ADJ=0.30 HALO_UM=0.5 MAXDISP="150 60" REFW=1469 REFT=1760
#        DRY_ONLY=1 -> stop after the dry run
set -euo pipefail
IN=$1; TAG=$2; SHIFT=$3; EXTRA=${4:-}
OUTD=${OUTD:-/workspace/knot2/out}; PACK=${PACK:-/workspace/knot2/knot_pack_v2_20261109}; KNOT1=${KNOT1:-/workspace/knot/out}
SIGNOFF=${SIGNOFF:?set SIGNOFF to Flow/scripts/signoff}; DGSE=${DGSE:?set DGSE to Flow/scripts/dgse}
W=$OUTD/$TAG; mkdir -p $W
log() { echo "[$(date '+%H:%M:%S IST')] $*"; }
# 0. dry run (read-only, ~2-5 min): what the move covers
bash $SIGNOFF/run_tcl.sh $OUTD/nets_under_footprint.tcl $W/dry.log IN_ODB=$IN SHIFT_FILE=$SHIFT STRIP_OUT=$W/strip_dry.txt \
    HALO_UM=${HALO_UM:-0.5} || true
grep -q NETS_UNDER_FOOTPRINT $W/dry.log || { log "dry run failed"; exit 1; }
grep -E "^(FOOT|STRIP|PUSH|PDN|LIFT)" $W/dry.log
[ "${DRY_ONLY:-0}" = 1 ] && exit 0
# 1. staged ECO, DRT=none
bash $SIGNOFF/run_tcl.sh $OUTD/eco_lift_staged.tcl $W/eco.log IN_ODB=$IN OUT_ODB=$W/eco.odb SHIFT_FILE=$SHIFT \
    ${EXTRA:+EXTRA_NETS=$EXTRA} GUIDE_OUT=$W/eco_guides.txt THREADS=${THREADS:-8} MAX_NETS=${MAX_NETS:-450} \
    TM1_ADJ=${TM1_ADJ:-0.30} HALO_UM=${HALO_UM:-0.5} "MAXDISP=${MAXDISP:-150 60}" "REGION_ADJ=${REGION_ADJ:-}"
grep -q "ECO_LIFT done" $W/eco.log || { log "eco_lift_staged failed (nothing written)"; grep -E "ERROR|ECO_LIFT" $W/eco.log | tail -5; exit 1; }
S=$(grep -o "strip set total [0-9]*" $W/eco.log | awk '{print $4}')
R=$(grep -o "GRT-0009\] rerouting [0-9]* nets" $W/eco.log | awk '{print $3}' | tail -1)
log "strip set $S, GRT re-routed ${R:-?}"
grep "ECO_LIFT gate\|ECO_PDN" $W/eco.log
if [ -z "${R:-}" ] || [ "$R" -lt $(( S * 90 / 100 )) ]; then log "GATE FAIL: GRT re-routed ${R:-0} of $S stripped nets"; exit 2; fi
# 2. resumed DRT: pass START (ALL->INCR routes the stripped nets) .. END
bash $SIGNOFF/run_tcl.sh $DGSE/drt_steps.tcl $W/drt.log STEP_IN=$W/eco.odb STEP_OUT=$W/drt.odb \
    STEP_START=${START:-17} STEP_END=${END:-19} STEP_ALL_AS_INCR=1 STEP_THREADS=${THREADS:-8} STEP_DRC_RPT=$W/drt.rpt
grep "DRT_STEPS pass\|DRT_STEPS final\|DRT_STEPS scan" $W/drt.log || true
# 3. count + supply
PACK=$PACK bash $KNOT1/knot_measure.sh $W/drt.rpt ${REFW:-1469} ${REFT:-1760} | tee $W/measure.txt
bash $SIGNOFF/run_tcl.sh $OUTD/pg_check.tcl $W/pg.log IN_ODB=$W/drt.odb MOVES=$W/eco_moves.txt || true
grep "PG_CHECK\|ECO_PDN_AUDIT" $W/pg.log || true
log "loop $TAG done: $W/drt.odb"
