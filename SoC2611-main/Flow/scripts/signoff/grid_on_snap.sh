#!/bin/bash
# Wait for a DRT snapshot, then run drc_grid.tcl (600 um windows, 4 threads) on it and print the ranking.
# usage: grid_on_snap.sh <drt_dir> <iter> [grid_um=600] [max_wait_min=90]
set -u
D=$1; IT=$2; G=${3:-600}; W=${4:-90}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
S=$D/drt_snap/drt_iter$IT.odb
for i in $(seq 1 "$W"); do [ -f "$S" ] && break; sleep 60; done
sleep 90
[ -f "$S" ] || { echo "GRID: no iter$IT after $W min"; exit 1; }
echo "GRID: iter$IT ready $(date -u +%T)"
grep -a "Number of violations" "$D/drt_chip.log" | tail -1
mkdir -p "$D/chk"; cd "$D/chk" || exit 1
IN_ODB=$S GRID_UM=$G OUT_DIR=$D/chk/grid$IT THREADS=4 "$OR" -exit "$HERE/drc_grid.tcl" > "grid$IT.log" 2>&1
echo "GRID: done $(date -u +%T)"
grep -a DRC_GRID "grid$IT.log" | awk -v t="iter$IT" '{s+=$6} END {print "GRID: " t " sum " s}'
grep -a DRC_GRID "grid$IT.log" | sort -k6 -n -r | head -8
grep -a "DRC_GRID 2740 2140\|DRC_GRID 2740 2740" "grid$IT.log"
