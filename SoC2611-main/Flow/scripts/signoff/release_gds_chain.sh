#!/bin/bash
# Interim-release GDS chain: seal ring -> PDK fill (SRAM macros abstracted) -> top-up fill -> density numbers.
# usage: release_gds_chain.sh <chip.gds> <topcell> <out_dir> [die=6600] [fill_j=2] [topup_j=8]
set -u
GDS=$(readlink -f "$1"); TOP=$2; OUT=$(readlink -m "$3"); DIE=${4:-6600}; FJ=${5:-2}; TJ=${6:-8}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$OUT"; cd "$OUT" || exit 1
echo "RELEASE_GDS start $(date -u +%T)"
python3 "$HERE/make_sealring.py" --input "$GDS" --top "$TOP" --width "$DIE" --height "$DIE" -o "$OUT/${TOP}_sealring.gds" > sealring.log 2>&1 || { echo "sealring failed"; tail -3 sealring.log; exit 2; }
echo "RELEASE_GDS sealring done $(date -u +%T)"
python3 "$HERE/fill_tiled.py" "$OUT/${TOP}_sealring.gds" "$OUT/${TOP}_pdkfill.gds" --top "$TOP" --tile 1000 -j "$FJ" --abstract-macros 'RM_IHPSG13_.*' > fill.log 2>&1 || { echo "fill failed"; tail -5 fill.log; exit 2; }
echo "RELEASE_GDS pdk fill done $(date -u +%T)"
python3 "$HERE/fill_topup.py" "$OUT/${TOP}_pdkfill.gds" "$OUT/${TOP}_final.gds" --top "$TOP" -j "$TJ" > topup.log 2>&1 || { echo "topup failed"; tail -5 topup.log; exit 2; }
echo "RELEASE_GDS topup done $(date -u +%T)"
python3 "$HERE/density_fast.py" "$OUT/${TOP}_final.gds" --top "$TOP" -j "$TJ" --attrib --json "$OUT/density.json" > density.txt 2>&1
echo "RELEASE_GDS density exit $? $(date -u +%T)"
tail -6 density.txt
ls -la "$OUT/${TOP}_final.gds"
echo "RELEASE_GDS done $(date -u +%T)"
