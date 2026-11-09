#!/usr/bin/env bash
# When <E>'s follow-on (d2_followon.sh: guides + 3 passes + pg_check) has written "all done", run the plain 16-pass
# clean-up on its guided database <E>g.odb.  usage: after_followon_plain.sh <E> <out name> [THREADS=12] [END=16]
E=$1; N=$2; T=${3:-12}; END=${4:-16}
D=/workspace/chip_fp2/eco/lift
S=/root/DGrid-SoC1/.claude/worktrees/asic-rtl-prep/HW/asic/signoff
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
MAX_POWER=${MAX_POWER:-5}; MAX_INMACRO=${MAX_INMACRO:-40}; MAX_RSS_GB=${MAX_RSS_GB:-100}
while ! grep -q "all done" $D/${E}_followon.log 2>/dev/null; do sleep 60; done
grep -a "PG_CHECK\|D1_COUNT" $D/${E}_followon.log | tail -4
# gates (Grok, 9 Nov evening): guided db has < MAX_POWER supply markers, both rails pass, in-macro markers dropped
power=$(grep -a D1_COUNT $D/${E}_followon.log | tail -1 | sed 's/.*power=\([0-9]*\).*/\1/')
rails=$(grep -a -c "PG_CHECK V[DS][DS] ok" $D/pg_${E}g.log)
inmacro=$(python3 -I $S/drc_breakdown.py $D/${E}g_drc.rpt /workspace/chip_fp2/handoff/macros_name_w_h_um.txt $D/d1_place.pl | grep "in-macro" | awk '{s+=$1} END{print s+0}')
echo "[plain $(date +%H:%M:%S)] gates: power=$power (<$MAX_POWER) rails_ok=$rails (2) in-macro=$inmacro (<$MAX_INMACRO)"
if [ -z "$power" ] || [ "$power" -ge "$MAX_POWER" ] || [ "$rails" -ne 2 ] || [ "$inmacro" -ge "$MAX_INMACRO" ]; then
  echo "[plain $(date +%H:%M:%S)] NO-GO: $N not started"; exit 2
fi
# memory gate: total resident memory of our processes
while true; do
  rss=$(ps -eo rss --no-headers | awk '{s+=$1} END{printf "%d", s/1048576}')
  [ "$rss" -lt "$MAX_RSS_GB" ] && break
  echo "[plain $(date +%H:%M:%S)] waiting for memory: ${rss} GB resident"; sleep 120
done
echo "[plain $(date +%H:%M:%S)] ${E}g ready (${rss} GB resident); start $N: END=$END THREADS=$T"
cd /root/.claude/jobs/658ac326/tmp
IN_ODB=$D/${E}g.odb OUT_ODB=$D/$N.odb END=$END THREADS=$T DRC_RPT=$D/${N}_drc.rpt $OR -exit $S/eco_plain.tcl > $D/$N.log 2>&1
echo "[plain $(date +%H:%M:%S)] done $N rc=$?"
bash /root/.claude/jobs/658ac326/tmp/grok_onehour/out/d1_watch.sh $D/$N.log $D/${N}_drc.rpt | tail -14 | cut -c1-120
