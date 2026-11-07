#!/bin/bash
# Run D (west-band ECO, RUNBOOK_WEST_BAND.md steps 1-3): from a chip DRT snapshot -> strip the nets with routing in
# the IO band (+ nets listed in EXTRA_NETS) -> obstructions on ALL routing layers over the four IO bands -> GRT with
# TopMetal1 fully open -> gate G1 (guide_band.py). Stops before DRT; start DRT by hand when G1 passes.
# usage: run_d_prep.sh <snapshot.odb> <out_dir> [EXTRA_NETS=file]
set -u
SNAP=$1; OUT=$2; EXTRA=${EXTRA_NETS:-}
HERE=$(cd "$(dirname "$0")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
mkdir -p "$OUT/drt_snap"
cd "$OUT" || exit 1
echo "RUN_D start $(date +%T)"
printf 'read_db %s\nwrite_def %s\n' "$SNAP" "$OUT/snap.def" > wdef.tcl
"$OR" -exit -no_init wdef.tcl > 0_def.log 2>&1 || { echo "write_def failed"; exit 1; }
python3 "$HERE/def_margin_nets.py" "$OUT/snap.def" "$OUT/nets_band.txt" 318 6282 || exit 1
rm -f "$OUT/snap.def"
if [ -n "$EXTRA" ] && [ -f "$EXTRA" ]; then cat "$OUT/nets_band.txt" "$EXTRA" | sort -u > "$OUT/nets.txt"; else sort -u "$OUT/nets_band.txt" > "$OUT/nets.txt"; fi
echo "RUN_D nets to strip: $(wc -l < "$OUT/nets.txt") (band $(wc -l < "$OUT/nets_band.txt"))"
IN_ODB=$SNAP OUT_ODB=$OUT/chip_obs.odb NETS_TXT=$OUT/nets.txt OBS_LAYERS="Metal1 Metal2 Metal3 Metal4 TopMetal1" \
  "$OR" -exit -no_init "$HERE/chip_io_obs.tcl" > 1_obs.log 2>&1 || { echo "obs failed"; tail -5 1_obs.log; exit 1; }
grep -a CHIP_IO_OBS 1_obs.log
LAYER_ADJUST="${LAYER_ADJUST:-TopMetal1 0.0}" CONG_ITERS=${CONG_ITERS:-10} \
  IN_ODB=$OUT/chip_obs.odb OUT_ODB=$OUT/chip_grt.odb BPINS_TCL=$OUT/bpins_unused.tcl GUIDE=$OUT/route.guide THREADS=8 \
  "$OR" -exit -no_init "$HERE/chip_grt.tcl" > 2_grt.log 2>&1 || { echo "grt failed"; tail -5 2_grt.log; exit 1; }
grep -a -E "CHIP_GRT|GRT-0303" 2_grt.log
grep -a -A8 "GRT-0096" 2_grt.log | tail -7
python3 "$HERE/guide_band.py" "$OUT/route.guide"
echo "RUN_D prep done $(date +%T)"
