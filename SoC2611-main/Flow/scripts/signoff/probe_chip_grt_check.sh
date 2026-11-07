#!/bin/bash
# Wait for a probe's ck_cts.odb, run the chip-level prep + GRT (chip_drt_prep.sh), then count the Metal4 guide boxes
# that lie >= 10 um inside macro outlines (guides_in_macros.py, margin -10) and print the GRT table.
# usage: probe_chip_grt_check.sh <engine_run_dir> <chip_dir> <place.pl> [grt_threads=8] [cong_iters=15]
set -u
R=$1; CHIP=$2; PL=$3; GT=${4:-8}; CI=${5:-15}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
MAC=/workspace/chip_fp2/handoff/macros_name_w_h_um.txt
until [ -f "$R/build/ck_cts.odb" ]; do
  if [ -f "$R/driver.log" ] && grep -a -q 'Traceback\|"fail"' "$R/driver.log"; then echo "CHECK: engine flow failed"; exit 1; fi
  sleep 60
done
sleep 20
echo "CHECK: ck_cts ready $(date -u +%T)"
mkdir -p "$CHIP"; cd "$CHIP" || exit 1
CONG_ITERS=$CI bash "$HERE/chip_drt_prep.sh" "$R/build/ck_cts.odb" "$CHIP" "$GT" > "$CHIP/prep.log" 2>&1
grep -a -A9 "GRT-0096" "$CHIP/4_grt.log" | grep -a -E "^Metal|^TopMetal|^Total"
grep -a -q "CHIP_GRT done" "$CHIP/4_grt.log" || { echo "CHECK: chip GRT failed"; tail -5 "$CHIP/4_grt.log"; exit 1; }
python3 "$HERE/guides_in_macros.py" "$CHIP/route.guide" "$MAC" "$PL" -10 "$CHIP/m4_pairs.txt" | head -9
echo "CHECK: done $(date -u +%T)"
