#!/bin/bash
# Run C: from a chip DRT snapshot -> IO-band obstructions (M3/M4/TM1) + strip nets that enter the IO band -> GRT with
# per-layer adjustment (LAYER_ADJUST) and capped iterations -> drt_steps.tcl START=0 with per-pass snapshots.
# usage: run_c_prep.sh <snapshot.odb> <out_dir> [threads=16]
set -u
SNAP=$1; OUT=$2; T=${3:-16}
HERE=$(cd "$(dirname "$0")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
mkdir -p "$OUT/drt_snap"
cd "$OUT" || exit 1
printf 'read_db %s\nwrite_def %s\n' "$SNAP" "$OUT/snap.def" > wdef.tcl
"$OR" -exit -no_init wdef.tcl > 0_def.log 2>&1 || { echo "write_def failed"; exit 1; }
# nets with routing inside the IO band: anything beyond 318 um from the die edge (IO band 140..320, pins at 320)
python3 "$HERE/def_margin_nets.py" "$OUT/snap.def" "$OUT/ioband_nets.txt" 318 6282 || exit 1
IN_ODB=$SNAP OUT_ODB=$OUT/chip_obs.odb NETS_TXT=$OUT/ioband_nets.txt \
  "$OR" -exit -no_init "$HERE/chip_io_obs.tcl" > 1_obs.log 2>&1 || { echo "obs failed"; tail -5 1_obs.log; exit 1; }
grep -a CHIP_IO_OBS 1_obs.log
rm -f "$OUT/snap.def"
LAYER_ADJUST="${LAYER_ADJUST:-Metal2 0.30 Metal3 0.30 Metal4 0.15 TopMetal1 0.0}" CONG_ITERS=${CONG_ITERS:-10} \
  IN_ODB=$OUT/chip_obs.odb OUT_ODB=$OUT/chip_grt.odb BPINS_TCL=$OUT/bpins_unused.tcl GUIDE=$OUT/route.guide THREADS=8 \
  "$OR" -exit -no_init "$HERE/chip_grt.tcl" > 2_grt.log 2>&1 || { echo "grt failed"; tail -5 2_grt.log; exit 1; }
grep -a -E "CHIP_GRT|^Total|GRT-0303" 2_grt.log
echo "RUN_C DRT start $(date +%T)"
STEP_IN=$OUT/chip_grt.odb STEP_OUT=$OUT/chip_droute.odb STEP_START=0 STEP_END=64 STEP_THREADS=$T \
  STEP_SNAPSHOT_DIR=$OUT/drt_snap STEP_DRC_RPT=$OUT/chip_route_drc.rpt \
  "$OR" -exit -no_init "$HERE/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" > drt_chip.log 2>&1
echo "RUN_C DRT exited rc=$? $(date +%T)"
