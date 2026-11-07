#!/bin/bash
# Option 2 step 2 (after chip_col1_shift.tcl): rip the nets whose wires lie under the shifted macros' new footprint
# (old gap x 782.34..814.34 um, Metal1-4), GRT the unrouted nets, clamp + widen the guides for the new strip, load
# them and start DRT with snapshots.  usage: run_f_route.sh <out_dir> [threads=8]
set -u
OUT=$1; T=${2:-8}
HERE=$(cd "$(dirname "$0")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
DX=${DX:-32}
cd "$OUT" || exit 1
echo "RUN_F route start $(date +%T)"
if [ -f shift.def ]; then
  python3 "$HERE/def_region_nets.py" shift.def ripnets_region.txt 782.34 365.2 $(python3 -c "print(782.34+$DX)") 1665.4 || exit 1
fi
# EXTRA_RIP: more nets to rip (e.g. nets of cells the legaliser nudged: loc_diff_nets.txt)
cat ripnets_region.txt ${EXTRA_RIP:-/dev/null} | sort -u > ripnets_more.txt
sort -u ripnets_more.txt ripnets_shift.txt > ripnets_all.txt
echo "RUN_F nets to re-route: $(wc -l < ripnets_all.txt) (region+extra $(wc -l < ripnets_more.txt) + shift $(wc -l < ripnets_shift.txt))"
IN_ODB=$OUT/chip_shift.odb OUT_ODB=$OUT/chip_ripped.odb NETS_TXT=$OUT/ripnets_more.txt \
  "$OR" -exit -no_init "$HERE/chip_strip_margin.tcl" > 2_rip.log 2>&1 || { echo "rip failed"; tail -3 2_rip.log; exit 1; }
grep -a -i "strip\|destroy" 2_rip.log | tail -2
rm -f shift.def
LAYER_ADJUST="TopMetal1 0.0" CONG_ITERS=10 IN_ODB=$OUT/chip_ripped.odb OUT_ODB=$OUT/chip_grt.odb \
  BPINS_TCL=$OUT/bpins_unused.tcl GUIDE=$OUT/route.guide THREADS=8 \
  "$OR" -exit -no_init "$HERE/chip_grt.tcl" > 3_grt.log 2>&1 || { echo "grt failed"; tail -3 3_grt.log; exit 1; }
grep -a -E "GRT-0303|CHIP_GRT done" 3_grt.log
grep -a -A8 "GRT-0096" 3_grt.log | tail -6
python3 "$HERE/guide_clamp.py" route.guide route_clamped.guide "$OUT/../runD/padnets.txt" || exit 1
STRIP_E=$(python3 -c "print(int(round((365.7+$DX)/7.2))*7200)")
GUIDE_STRIP_E=$STRIP_E python3 "$HERE/guide_widen.py" route_clamped.guide route_widen.guide "$OUT/../runD/padnets.txt" 1 || exit 1
# gate G1: no NON-pad net may keep a guide box inside the IO band (pad nets have their pins there)
python3 "$HERE/guide_band_nets.py" route_widen.guide "$OUT/../runD/padnets.txt" | tee 4_gate.log
non=$(grep -a -o "[0-9]* NON-pad nets" 4_gate.log | grep -a -o "^[0-9]*")
if [ "${non:-9999}" -gt 0 ]; then echo "RUN_F GATE G1 FAILED ($non non-pad nets in band)"; exit 2; fi
echo "RUN_F GATE G1 PASSED (band boxes only on pad nets)"
IN_ODB=$OUT/chip_grt.odb OUT_ODB=$OUT/chip_guided.odb GUIDE=$OUT/route_widen.guide \
  "$OR" -exit -no_init "$HERE/chip_load_guides.tcl" > 5_guides.log 2>&1 || { echo "load guides failed"; exit 1; }
grep -a CHIP_LOAD_GUIDES 5_guides.log
mkdir -p drt_snap
echo "RUN_F DRT start $(date +%T) threads $T"
STEP_IN=$OUT/chip_guided.odb STEP_OUT=$OUT/chip_droute.odb STEP_START=0 STEP_END=64 STEP_THREADS=$T \
  STEP_SNAPSHOT_DIR=$OUT/drt_snap STEP_DRC_RPT=$OUT/chip_route_drc.rpt \
  "$OR" -exit -no_init "$HERE/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" > drt_chip.log 2>&1
echo "RUN_F DRT exited rc=$? $(date +%T)"
