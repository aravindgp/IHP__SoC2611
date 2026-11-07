#!/bin/bash
# Chip-level GRT with routing obstructions over the macros: copy a chip_drt_prep.sh directory's pad-integrated db,
# add macro obstructions (macro_obs.tcl), re-run chip_grt.tcl -> <out>/chip_grt.odb + route.guide for run_chip_drt.sh.
# usage: chip_mobs_grt.sh <prep_dir> <out_dir> [threads=16] [layers="Metal4"] [margin=0] [cong_iters=15]
set -u
PREP=$(readlink -m "$1"); OUT=$(readlink -m "$2"); T=${3:-16}; LAY=${4:-Metal4}; MG=${5:-0}; CI=${6:-15}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
mkdir -p "$OUT"; cd "$OUT" || exit 1
echo "CHIP_MOBS start $(date -u +%T) prep=$PREP layers=$LAY margin=$MG threads=$T"
IN_ODB=$PREP/chip_pdn.odb OUT_ODB=$OUT/chip_pdn.odb LAYERS=$LAY MARGIN=$MG \
  "$OR" -no_init -no_splash -exit "$HERE/macro_obs.tcl" > "$OUT/3m_obs.log" 2>&1 || { echo "macro_obs failed"; tail -5 "$OUT/3m_obs.log"; exit 1; }
grep -a MACRO_OBS "$OUT/3m_obs.log"
IN_ODB=$OUT/chip_pdn.odb OUT_ODB=$OUT/chip_grt.odb BPINS_TCL=$OUT/bpins.tcl GUIDE=$OUT/route.guide THREADS=$T CONG_ITERS=$CI \
  "$OR" -no_init -no_splash -exit "$HERE/chip_grt.tcl" > "$OUT/4_grt.log" 2>&1 || { echo "chip_grt failed"; tail -20 "$OUT/4_grt.log"; exit 1; }
grep -a -A9 "GRT-0096" "$OUT/4_grt.log" | grep -a -E "^Metal|^TopMetal|^Total"
grep -a "CHIP_GRT done" "$OUT/4_grt.log" && echo "CHIP_MOBS done $(date -u +%T)"
