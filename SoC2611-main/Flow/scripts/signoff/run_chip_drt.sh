#!/bin/bash
# From a chip-level GRT (chip_drt_prep.sh output: chip_grt.odb + route.guide, GRT run WITHOUT band obstructions) to
# DRT: clamp the guides of non-pad nets out of the IO band, add the band obstructions for DRT, load the clamped
# guides, start drt_steps at the given thread count.  usage: run_chip_drt.sh <prep_dir> <out_dir> [threads=32]
set -u
PREP=$(readlink -m "$1"); OUT=$(readlink -m "$2"); T=${3:-32}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
PADS=/workspace/chip_drt/runD/padnets.txt
mkdir -p "$OUT/drt_snap"; cd "$OUT" || exit 1
echo "RUN_CHIP_DRT start $(date +%T) prep=$PREP threads=$T"
python3 "$HERE/guide_band_nets.py" "$PREP/route.guide" "$PADS" | tee 1_before.log
python3 "$HERE/guide_clamp.py" "$PREP/route.guide" "$OUT/route_clamped.guide" "$PADS" || exit 1
python3 "$HERE/guide_band_nets.py" "$OUT/route_clamped.guide" "$PADS" | tee 2_gate.log
non=$(grep -a -o "[0-9]* NON-pad nets" 2_gate.log | grep -a -o "^[0-9]*")
if [ "${non:-9999}" -gt 0 ]; then echo "RUN_CHIP_DRT GATE FAILED ($non non-pad nets in band)"; exit 2; fi
echo "RUN_CHIP_DRT GATE PASSED"
IN_ODB=$PREP/chip_grt.odb OUT_ODB=$OUT/chip_obs.odb OBS_LAYERS="Metal1 Metal2 Metal3 Metal4 TopMetal1" \
  "$OR" -exit -no_init "$HERE/chip_io_obs.tcl" > 3_obs.log 2>&1 || { echo "obs failed"; tail -5 3_obs.log; exit 1; }
grep -a CHIP_IO_OBS 3_obs.log
IN_ODB=$OUT/chip_obs.odb OUT_ODB=$OUT/chip_guided.odb GUIDE=$OUT/route_clamped.guide \
  "$OR" -exit -no_init "$HERE/chip_load_guides.tcl" > 4_guides.log 2>&1 || { echo "load guides failed"; tail -5 4_guides.log; exit 1; }
grep -a CHIP_LOAD_GUIDES 4_guides.log
echo "RUN_CHIP_DRT DRT start $(date +%T) threads $T"
STEP_IN=$OUT/chip_guided.odb STEP_OUT=$OUT/chip_droute.odb STEP_START=0 STEP_END=64 STEP_THREADS=$T \
  STEP_SNAPSHOT_DIR=$OUT/drt_snap STEP_DRC_RPT=$OUT/chip_route_drc.rpt \
  "$OR" -exit -no_init "$HERE/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" > drt_chip.log 2>&1
echo "RUN_CHIP_DRT DRT exited rc=$? $(date +%T)"
