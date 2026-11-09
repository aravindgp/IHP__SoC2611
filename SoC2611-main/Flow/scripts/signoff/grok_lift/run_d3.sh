#!/usr/bin/env bash
# d3 = d2 (staged lift of slice[27] 63.36 um east, 0.5 um PDN halo) + the two fixes found on d2's report:
#   - EXTRA_NETS also holds the 12 nets whose stale guides crossed the new footprint although they were not stripped
#     (guides_crossing_footprint.py on d2_guides.txt: dp_sink3 net3511, dp_sink2 net203, n66833[209], ...);
#   - MACRO_EXT=1: the global router blocks one gcell round every macro, so no guide ends in the 99.4 %-covered border
#     gcells of the moved macro.
# usage: run_d3.sh [NAME=d3] [THREADS=16] [END=3]; env WAIT_PID = process to wait for before starting (memory gate)
N=${1:-d3}; T=${2:-16}; END=${3:-3}
D=/workspace/chip_fp2/eco/lift
G=<design-repo>/HW/asic/signoff/grok_lift
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
if [ -n "${WAIT_PID:-}" ]; then while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 60; done; fi
echo "[run_d3 $(date +%H:%M:%S)] start $N"
cd /root/.claude/jobs/658ac326/tmp
IN_ODB=/workspace/chip_fp2/eco/roundI/guidetest.odb OUT_ODB=$D/$N.odb SHIFT_FILE=$G/shift_d1_s27_east63.txt \
EXTRA_NETS=$D/extra_d3.txt PDN_HALO_UM=0.5 MACRO_EXT=${MACRO_EXT:-1} MAX_NETS=900 THREADS=$T DRT=plain END=$END \
DRC_RPT=$D/${N}_drc.rpt GUIDE_OUT=$D/${N}_guides.txt STRIP_LOG=$D/${N}_strip.txt \
$OR -exit $G/eco_lift_staged.tcl > $D/$N.log 2>&1
echo "[run_d3 $(date +%H:%M:%S)] done rc=$?"
grep -a -E "GRT-0009|ECO_LIFT gate|Number of violations|ECO_LIFT done|Error|ERROR" $D/$N.log | tail -12
bash /root/.claude/jobs/658ac326/tmp/grok_onehour/out/d1_watch.sh $D/$N.log $D/${N}_drc.rpt | tail -1
