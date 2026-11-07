#!/bin/bash
# Run F v3: on a run-F DRT snapshot (column 1 shifted), strip the nets that still route in the IO band, put
# obstructions on all layers over the four IO bands, GRT the stripped nets, clamp + widen the guides for the 78 um
# strip, load them and start DRT.  usage: run_f3.sh <snapshot.odb> <out_dir> [threads=8]   env DX=32
set -u
SNAP=$1; OUT=$2; T=${3:-8}
HERE=$(cd "$(dirname "$0")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
DX=${DX:-32}
PADS=/workspace/chip_drt/runD/padnets.txt
mkdir -p "$OUT/drt_snap"
cd "$OUT" || exit 1
echo "RUN_F3 start $(date +%T)"
printf 'read_db %s\nwrite_def %s\n' "$SNAP" "$OUT/snap.def" > wdef.tcl
"$OR" -exit -no_init wdef.tcl > 0_def.log 2>&1 || { echo "write_def failed"; exit 1; }
python3 "$HERE/def_margin_nets.py" "$OUT/snap.def" "$OUT/ioband_nets.txt" 318 6282 || exit 1
rm -f "$OUT/snap.def"
IN_ODB=$SNAP OUT_ODB=$OUT/chip_obs.odb NETS_TXT=$OUT/ioband_nets.txt OBS_LAYERS="Metal1 Metal2 Metal3 Metal4 TopMetal1" \
  "$OR" -exit -no_init "$HERE/chip_io_obs.tcl" > 1_obs.log 2>&1 || { echo "obs failed"; tail -5 1_obs.log; exit 1; }
grep -a CHIP_IO_OBS 1_obs.log
LAYER_ADJUST="TopMetal1 0.0" CONG_ITERS=10 IN_ODB=$OUT/chip_obs.odb OUT_ODB=$OUT/chip_grt.odb \
  BPINS_TCL=$OUT/bpins_unused.tcl GUIDE=$OUT/route.guide THREADS=8 \
  "$OR" -exit -no_init "$HERE/chip_grt.tcl" > 2_grt.log 2>&1 || { echo "grt failed"; tail -5 2_grt.log; exit 1; }
grep -a -E "GRT-0303|CHIP_GRT done" 2_grt.log
python3 "$HERE/guide_clamp.py" route.guide route_clamped.guide "$PADS" || exit 1
STRIP_E=$(python3 -c "print(int(round((365.7+$DX)/7.2))*7200)")
GUIDE_STRIP_E=$STRIP_E python3 "$HERE/guide_widen.py" route_clamped.guide route_widen.guide "$PADS" 1 || exit 1
python3 "$HERE/guide_band_nets.py" route_widen.guide "$PADS" | tee 3_gate.log
non=$(grep -a -o "[0-9]* NON-pad nets" 3_gate.log | grep -a -o "^[0-9]*")
if [ "${non:-9999}" -gt 0 ]; then echo "RUN_F3 GATE G1 FAILED ($non non-pad nets in band)"; exit 2; fi
echo "RUN_F3 GATE G1 PASSED"
IN_ODB=$OUT/chip_grt.odb OUT_ODB=$OUT/chip_guided.odb GUIDE=$OUT/route_widen.guide \
  "$OR" -exit -no_init "$HERE/chip_load_guides.tcl" > 4_guides.log 2>&1 || { echo "load guides failed"; exit 1; }
grep -a CHIP_LOAD_GUIDES 4_guides.log
echo "RUN_F3 DRT start $(date +%T) threads $T"
STEP_IN=$OUT/chip_guided.odb STEP_OUT=$OUT/chip_droute.odb STEP_START=0 STEP_END=64 STEP_THREADS=$T \
  STEP_SNAPSHOT_DIR=$OUT/drt_snap STEP_DRC_RPT=$OUT/chip_route_drc.rpt \
  "$OR" -exit -no_init "$HERE/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" > drt_chip.log 2>&1
echo "RUN_F3 DRT exited rc=$? $(date +%T)"
