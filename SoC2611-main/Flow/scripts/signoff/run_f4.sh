#!/bin/bash
# Run F v4: from a run-F3 DRT snapshot (column shifted, band stripped + obstructed, guides clamped/widened), rip the
# nets of the moved instances that were not ripped yet (clock nets!), GRT the unrouted nets, clamp + widen, load,
# DRT.  usage: run_f4.sh <snapshot.odb> <out_dir> <moved_cells.txt> [threads=8]   env DX=32
set -u
SNAP=$1; OUT=$2; CELLS=$3; T=${4:-8}
HERE=$(cd "$(dirname "$0")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
DX=${DX:-32}
PADS=/workspace/chip_drt/runD/padnets.txt
mkdir -p "$OUT/drt_snap"
cd "$OUT" || exit 1
echo "RUN_F4 start $(date +%T)"
ALLNETS=1 IN_ODB=$SNAP CELLS_TXT=$CELLS OUT_TXT=$OUT/moved_nets_all.txt \
  "$OR" -exit -no_init "$HERE/cells_to_nets.tcl" > 0_nets.log 2>&1 || { echo "cells_to_nets failed"; exit 1; }
grep -a CELLS_TO_NETS 0_nets.log
IN_ODB=$SNAP OUT_ODB=$OUT/chip_ripped.odb NETS_TXT=$OUT/moved_nets_all.txt \
  "$OR" -exit -no_init "$HERE/chip_strip_margin.tcl" > 1_rip.log 2>&1 || { echo "rip failed"; tail -3 1_rip.log; exit 1; }
grep -a -i "strip\|destroy" 1_rip.log | tail -1
LAYER_ADJUST="TopMetal1 0.0" CONG_ITERS=10 IN_ODB=$OUT/chip_ripped.odb OUT_ODB=$OUT/chip_grt.odb \
  BPINS_TCL=$OUT/bpins_unused.tcl GUIDE=$OUT/route.guide THREADS=8 \
  "$OR" -exit -no_init "$HERE/chip_grt.tcl" > 2_grt.log 2>&1 || { echo "grt failed"; tail -5 2_grt.log; exit 1; }
grep -a -E "GRT-0303|CHIP_GRT done" 2_grt.log
python3 "$HERE/guide_clamp.py" route.guide route_clamped.guide "$PADS" || exit 1
STRIP_E=$(python3 -c "print(int(round((365.7+$DX)/7.2))*7200)")
GUIDE_STRIP_E=$STRIP_E python3 "$HERE/guide_widen.py" route_clamped.guide route_widen.guide "$PADS" 1 || exit 1
python3 "$HERE/guide_band_nets.py" route_widen.guide "$PADS" | tee 3_gate.log
non=$(grep -a -o "[0-9]* NON-pad nets" 3_gate.log | grep -a -o "^[0-9]*")
if [ "${non:-9999}" -gt 0 ]; then echo "RUN_F4 GATE G1 FAILED ($non non-pad nets in band)"; exit 2; fi
echo "RUN_F4 GATE G1 PASSED"
IN_ODB=$OUT/chip_grt.odb OUT_ODB=$OUT/chip_guided.odb GUIDE=$OUT/route_widen.guide \
  "$OR" -exit -no_init "$HERE/chip_load_guides.tcl" > 4_guides.log 2>&1 || { echo "load guides failed"; exit 1; }
grep -a CHIP_LOAD_GUIDES 4_guides.log
echo "RUN_F4 DRT start $(date +%T) threads $T"
STEP_IN=$OUT/chip_guided.odb STEP_OUT=$OUT/chip_droute.odb STEP_START=0 STEP_END=64 STEP_THREADS=$T \
  STEP_SNAPSHOT_DIR=$OUT/drt_snap STEP_DRC_RPT=$OUT/chip_route_drc.rpt \
  "$OR" -exit -no_init "$HERE/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" > drt_chip.log 2>&1
echo "RUN_F4 DRT exited rc=$? $(date +%T)"
