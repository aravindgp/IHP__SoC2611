#!/bin/bash
# GRT capacity trials on a ripped chip ODB WITHOUT the IO-band obstructions (they underflow GRT): baseline vs
# per-layer derates that push the re-routed nets up to TopMetal1 (free over the SRAM columns).
# usage: grt_trials.sh <ripped.odb> <out_dir>
set -u
IN=$1; OUT=$2
HERE=$(cd "$(dirname "$0")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
PADS=/workspace/chip_drt/runD/padnets.txt
mkdir -p "$OUT"; cd "$OUT" || exit 1
IN_ODB=$IN OUT_ODB=$OUT/noobs.odb "$OR" -exit -no_init "$HERE/chip_rm_obs.tcl" > rmobs.log 2>&1
grep -a CHIP_RM_OBS rmobs.log
run_trial() {
  k=$1; adj=$2
  LAYER_ADJUST="$adj" CONG_ITERS=10 IN_ODB=$OUT/noobs.odb OUT_ODB=$OUT/grt_$k.odb BPINS_TCL=$OUT/bp_$k.tcl \
    GUIDE=$OUT/route_$k.guide THREADS=8 "$OR" -exit -no_init "$HERE/chip_grt.tcl" > grt_$k.log 2>&1
  echo "== trial $k ($adj): $(grep -a -o 'runtime = [0-9:]*' grt_$k.log)"
  grep -a -A7 "GRT-0096" grt_$k.log | grep -a -E "^Metal|^TopMetal" | awk '{printf "  %s dem %s ovf %s\n",$1,$3,$NF}'
  python3 "$HERE/guide_band_nets.py" route_$k.guide "$PADS" | head -1
}
run_trial B "TopMetal1 0.0"
run_trial A "Metal2 0.5 Metal3 0.5 Metal4 0.5 TopMetal1 0.0"
run_trial C "Metal2 0.3 Metal3 0.3 Metal4 0.3 TopMetal1 0.0"
echo "GRT_TRIALS done $(date +%T)"
