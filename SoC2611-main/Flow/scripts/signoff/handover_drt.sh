#!/bin/bash
# Hand a probe over to DRT: wait for the engine run's ck_cts.odb, integrate pads + straps + chip GRT (16 threads,
# 15 iterations), stop the running DRT whose snapshot dir contains OLD_TAG, then run_chip_drt.sh at 32 threads.
# usage: handover_drt.sh <engine_run_dir> <chip_dir> <drt_dir> <old_drt_tag|none> [grt_threads=16] [drt_threads=32]
set -u
R=$1; CHIP=$2; DRT=$3; OLD=$4; GT=${5:-16}; DT=${6:-32}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
until [ -f "$R/build/ck_cts.odb" ]; do
  if [ -f "$R/driver.log" ] && grep -a -q 'Traceback\|"fail"' "$R/driver.log"; then echo "HANDOVER: engine flow failed"; exit 1; fi
  sleep 60
done
sleep 20
echo "HANDOVER: ck_cts ready $(date +%T)"
mkdir -p "$CHIP"; cd "$CHIP" || exit 1
CONG_ITERS=15 bash "$HERE/chip_drt_prep.sh" "$R/build/ck_cts.odb" "$CHIP" "$GT" > "$CHIP/prep.log" 2>&1
grep -a -A8 "GRT-0096" "$CHIP/4_grt.log" | grep -a -E "^Metal|^TopMetal|^Total"
grep -a -q "CHIP_GRT done" "$CHIP/4_grt.log" || { echo "HANDOVER: chip GRT failed"; tail -5 "$CHIP/4_grt.log"; exit 1; }
# optional gate: env GATE_JSON (DPASS probe result) and GATE_MAX (core GRT overflow): wait for the json, stop if above
if [ -n "${GATE_JSON:-}" ]; then
  until [ -f "$GATE_JSON" ]; do sleep 60; done
  python3 "$HERE/gate_score.py" "$GATE_JSON" "${GATE_MAX:-10000}" || { echo "HANDOVER: gate failed, old DRT kept"; exit 1; }
fi
if [ "$OLD" != "none" ]; then
  for p in $(pgrep -f "bin/openroad"); do
    if grep -a -q "$OLD/drt_snap" "/proc/$p/environ" 2>/dev/null; then kill "$p" && echo "HANDOVER: stopped old DRT pid $p $(date +%T)"; fi
  done
  sleep 10
fi
bash "$HERE/run_chip_drt.sh" "$CHIP" "$DRT" "$DT" > "$DRT.chain.log" 2>&1
tail -3 "$DRT.chain.log"
