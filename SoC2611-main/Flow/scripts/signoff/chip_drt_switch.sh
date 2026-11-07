#!/bin/bash
# Switch the running core DRT to a chip-level DRT (pads in) at a pass boundary:
# wait for "Start <N+1>th" in the core DRT log (=> drt_iter<N>.odb written), kill the core DRT, build the chip ODB
# from drt_iter<N>.odb (chip_drt_prep.sh), then run drt_steps.tcl STEP_START=0 with per-pass snapshots on it.
# usage: chip_drt_switch.sh <core_run_dir> <core_drt_log> <N> <out_dir> <core_openroad_pid> [threads=16]
set -u
R=$1; LOG=$2; N=$3; OUT=$4; KILLPID=$5; T=${6:-16}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
NEXT=$((N + 1))
echo "SWITCH waiting for pass $NEXT start in $LOG $(date +%T)"
until tr -d '\000' < "$LOG" | grep -a -q "Start ${NEXT}[a-z]* optimization iteration"; do sleep 30; done
SNAP=$R/build/drt_snap/drt_iter${N}.odb
[ -s "$SNAP" ] || { echo "SWITCH missing $SNAP"; exit 1; }
echo "SWITCH pass $NEXT started; killing core DRT pid $KILLPID $(date +%T)"
kill "$KILLPID"
sleep 5
bash "$HERE/chip_drt_prep.sh" "$SNAP" "$OUT" 8 || { echo "SWITCH prep failed"; exit 1; }
mkdir -p "$OUT/drt_snap"
echo "SWITCH chip DRT start $(date +%T)"
cd "$OUT" && STEP_IN=$OUT/chip_grt.odb STEP_OUT=$OUT/chip_droute.odb STEP_START=0 STEP_END=64 STEP_THREADS=$T \
  STEP_SNAPSHOT_DIR=$OUT/drt_snap STEP_DRC_RPT=$OUT/chip_route_drc.rpt \
  "$OR" -exit -no_init "$HERE/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" > "$OUT/drt_chip.log" 2>&1
echo "SWITCH chip DRT exited rc=$? $(date +%T)"
