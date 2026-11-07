#!/bin/bash
# Run D step 4: clamp the GRT guides out of the IO band (guide_clamp.py), gate G1 on the clamped guides, load them
# into the ODB (chip_load_guides.tcl) and start drt_steps.tcl START=0 with snapshots.
# usage: run_d_drt.sh <out_dir> [threads=8]   (needs <out_dir>/chip_grt.odb, route.guide, padnets.txt)
set -u
OUT=$1; T=${2:-8}
HERE=$(cd "$(dirname "$0")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
cd "$OUT" || exit 1
python3 "$HERE/guide_clamp.py" route.guide route_clamped.guide padnets.txt || exit 1
# gate at the obstruction's inner edge (316.8 um = the gcell boundary the clamp projects onto), not 318
python3 "$HERE/guide_band.py" route_clamped.guide 6600 140 316.8 | tee 3_gate.log
tot=$(grep -a -o "band 140..317 um: [0-9]*" 3_gate.log | grep -a -o "[0-9]*$")
if [ "${tot:-9999}" -gt 400 ]; then echo "RUN_D GATE G1 FAILED ($tot boxes in band)"; exit 2; fi
echo "RUN_D GATE G1 PASSED ($tot boxes in band, pad nets)"
IN_ODB=$OUT/chip_grt.odb OUT_ODB=$OUT/chip_guided.odb GUIDE=$OUT/route_clamped.guide \
  "$OR" -exit -no_init "$HERE/chip_load_guides.tcl" > 4_guides.log 2>&1 || { echo "load guides failed"; tail -5 4_guides.log; exit 1; }
grep -a CHIP_LOAD_GUIDES 4_guides.log
echo "RUN_D DRT start $(date +%T) threads $T"
STEP_IN=$OUT/chip_guided.odb STEP_OUT=$OUT/chip_droute.odb STEP_START=0 STEP_END=64 STEP_THREADS=$T \
  STEP_SNAPSHOT_DIR=$OUT/drt_snap STEP_DRC_RPT=$OUT/chip_route_drc.rpt \
  "$OR" -exit -no_init "$HERE/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" > drt_chip.log 2>&1
echo "RUN_D DRT exited rc=$? $(date +%T)"
