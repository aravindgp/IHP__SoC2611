#!/bin/bash
# Resume a paused chip DRT from its last snapshot, in sessions of a few passes so each session leaves a checkpoint.
# usage: resume_chip_drt.sh <drt_dir> <start_pass> [threads=32] [passes_per_session=3] [end_pass=64]
# Pass N resumes from <drt_dir>/drt_snap/drt_iter<N-1>.odb (or the previous session's output); each session writes
# <drt_dir>/resume/pass<END>.odb, its DRC report, and appends to <drt_dir>/drt_resume.log.
set -u
D=$1; START=$2; T=${3:-32}; PER=${4:-3}; END=${5:-64}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
mkdir -p "$D/resume"
IN=$D/drt_snap/drt_iter$((START - 1)).odb
[ -f "$D/resume/pass$((START - 1)).odb" ] && IN=$D/resume/pass$((START - 1)).odb
[ -f "$IN" ] || { echo "RESUME: no input $IN"; exit 1; }
s=$START
while [ "$s" -le "$END" ]; do
  e=$((s + PER - 1)); [ "$e" -gt "$END" ] && e=$END
  OUT=$D/resume/pass$e.odb
  echo "RESUME: passes $s..$e from $IN at $T threads $(date -u +%T)" | tee -a "$D/drt_resume.log"
  STEP_IN=$IN STEP_OUT=$OUT STEP_START=$s STEP_END=$e STEP_THREADS=$T STEP_DRC_RPT=$D/resume/pass${e}_drc.rpt \
    "$OR" -exit -no_init "$HERE/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" > "$D/resume/pass$e.log" 2>&1
  rc=$?
  grep -a "DRT_STEPS pass\|DRT_STEPS final\|DRT_STEPS scan" "$D/resume/pass$e.log" | tee -a "$D/drt_resume.log"
  [ "$rc" -eq 0 ] && [ -f "$OUT" ] || { echo "RESUME: session $s..$e failed rc=$rc" | tee -a "$D/drt_resume.log"; exit 1; }
  v=$(grep -a "DRT_STEPS final violations" "$D/resume/pass$e.log" | grep -a -o "[0-9]*$")
  [ "${v:-1}" -eq 0 ] && { echo "RESUME: zero violations after pass $e" | tee -a "$D/drt_resume.log"; exit 0; }
  IN=$OUT; s=$((e + 1))
done
echo "RESUME: reached pass $END" | tee -a "$D/drt_resume.log"
