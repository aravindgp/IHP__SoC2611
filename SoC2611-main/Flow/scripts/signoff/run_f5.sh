#!/bin/bash
# Run F v5: shift the NORTH part of the west SRAM column (16x 1P_512x8 + 4x 1P_64x16 at x 365.7, y 3.2..6.24 mm) by
# DX um on a run-F4 snapshot (south array already shifted, band stripped/obstructed, guides clamped/widened), then
# rip every net of every instance whose location changed (signal + clock), the nets under the new footprint, GRT,
# clamp + widen, load, DRT.  usage: run_f5.sh <snapshot.odb> <out_dir> [threads=8]   env DX=32
set -u
SNAP=$1; OUT=$2; T=${3:-8}
HERE=$(cd "$(dirname "$0")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
LP="$HERE/lowprio.sh"
DX=${DX:-32}
PADS=/workspace/chip_drt/runD/padnets.txt
BP=/workspace/chip_drt/stripB/bpins.tcl
mkdir -p "$OUT/drt_snap"
cd "$OUT" || exit 1
echo "RUN_F5 start $(date +%T)"
# 1. shift (macros at x 365.7, y 3204..6240; east edge 602.5; next column at 652.3)
COL_X0=365.7 COL_X1=602.5 CY0=3204 CY1=6240 GAP_X1=652.3 NMACROS=20 DX=$DX OUTDIR=$OUT BPINS_TCL=$BP \
  IN_ODB=$SNAP OUT_ODB=$OUT/chip_shift.odb bash "$LP" "$OR" -exit -no_init "$HERE/chip_col_shift.tcl" > 1_shift.log 2>&1
grep -a -E "COL1_SHIFT|ERROR|Error|displacement" 1_shift.log | grep -v "row seen"
grep -a -q "COL1_SHIFT wrote" 1_shift.log || { echo "RUN_F5 shift failed"; exit 1; }
# 2. every instance that moved (legaliser included) -> all its non-supply nets
IN_ODB=$SNAP OUT_TXT=$OUT/loc_pre.txt XMAX_UM=1200 YMAX_UM=6600 bash "$LP" "$OR" -exit -no_init "$HERE/dump_loc.tcl" > loc_pre.log 2>&1
IN_ODB=$OUT/chip_shift.odb OUT_TXT=$OUT/loc_post.txt XMAX_UM=1200 YMAX_UM=6600 bash "$LP" "$OR" -exit -no_init "$HERE/dump_loc.tcl" > loc_post.log 2>&1
python3 "$HERE/loc_diff_nets.py" loc_pre.txt loc_post.txt moved_cells.txt || exit 1
ALLNETS=1 IN_ODB=$OUT/chip_shift.odb CELLS_TXT=$OUT/moved_cells.txt OUT_TXT=$OUT/moved_nets_all.txt \
  bash "$LP" "$OR" -exit -no_init "$HERE/cells_to_nets.tcl" > 2_nets.log 2>&1
grep -a CELLS_TO_NETS 2_nets.log
# 3. nets routed under the new footprint (old gap x 602.5..602.5+DX, Metal1-4)
python3 "$HERE/def_region_nets.py" shift.def ripnets_region.txt 602.5 3204 $(python3 -c "print(602.5+$DX)") 6240 || exit 1
rm -f shift.def
cat ripnets_region.txt moved_nets_all.txt ripnets_shift.txt | sort -u > ripnets_all.txt
echo "RUN_F5 nets to re-route: $(wc -l < ripnets_all.txt)"
IN_ODB=$OUT/chip_shift.odb OUT_ODB=$OUT/chip_ripped.odb NETS_TXT=$OUT/ripnets_all.txt \
  "$OR" -exit -no_init "$HERE/chip_strip_margin.tcl" > 3_rip.log 2>&1 || { echo "rip failed"; exit 1; }
grep -a -i "strip\|destroy" 3_rip.log | tail -1
# 4. GRT, guides, DRT
LAYER_ADJUST="TopMetal1 0.0" CONG_ITERS=10 IN_ODB=$OUT/chip_ripped.odb OUT_ODB=$OUT/chip_grt.odb \
  BPINS_TCL=$OUT/bpins_unused.tcl GUIDE=$OUT/route.guide THREADS=8 \
  "$OR" -exit -no_init "$HERE/chip_grt.tcl" > 4_grt.log 2>&1 || { echo "grt failed"; tail -5 4_grt.log; exit 1; }
grep -a -E "GRT-0303|CHIP_GRT done" 4_grt.log
python3 "$HERE/guide_clamp.py" route.guide route_clamped.guide "$PADS" || exit 1
STRIP_E=$(python3 -c "print(int(round((365.7+$DX)/7.2))*7200)")
GUIDE_STRIP_E=$STRIP_E python3 "$HERE/guide_widen.py" route_clamped.guide route_widen.guide "$PADS" 1 || exit 1
python3 "$HERE/guide_band_nets.py" route_widen.guide "$PADS" | tee 5_gate.log
non=$(grep -a -o "[0-9]* NON-pad nets" 5_gate.log | grep -a -o "^[0-9]*")
if [ "${non:-9999}" -gt 0 ]; then echo "RUN_F5 GATE G1 FAILED ($non non-pad nets in band)"; exit 2; fi
echo "RUN_F5 GATE G1 PASSED"
IN_ODB=$OUT/chip_grt.odb OUT_ODB=$OUT/chip_guided.odb GUIDE=$OUT/route_widen.guide \
  "$OR" -exit -no_init "$HERE/chip_load_guides.tcl" > 6_guides.log 2>&1 || { echo "load guides failed"; exit 1; }
grep -a CHIP_LOAD_GUIDES 6_guides.log
echo "RUN_F5 DRT start $(date +%T) threads $T"
STEP_IN=$OUT/chip_guided.odb STEP_OUT=$OUT/chip_droute.odb STEP_START=0 STEP_END=64 STEP_THREADS=$T \
  STEP_SNAPSHOT_DIR=$OUT/drt_snap STEP_DRC_RPT=$OUT/chip_route_drc.rpt \
  "$OR" -exit -no_init "$HERE/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" > drt_chip.log 2>&1
echo "RUN_F5 DRT exited rc=$? $(date +%T)"
