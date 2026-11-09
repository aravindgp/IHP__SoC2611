#!/usr/bin/env bash
# After the staged ECO <E> (eco_lift_staged.tcl, DRT=plain) has written <E>.odb: count, power-grid check, Metal1 spacing
# along the moved macro's bottom edge, then the explicit channel guides for the supply-short nets (same recipe as the
# d1 guide test: supply nets from the report -> exact pin dump -> guide_channels.py -> eco_guides.tcl END=3) and the
# power-grid check on the guided result.  usage: d2_followon.sh <E> [THREADS=16]   (files in /workspace/chip_fp2/eco/lift)
E=${1:-d2}; T=${2:-16}; HALO=${3:-8}; GRID=${4:-4}
# HALO 8 (d1 guide test used 3): with 3 the A* stacked four nets into the one 8 um column next to the 256x32 slice's
# east edge (x 2826-2834), through the old jog, and they collided at its top-right corner (6 elbow-square markers).
WAIT_PID=${WAIT_PID:-}   # memory gate: wait for this process (the v.1.3.1 chain) before any OpenROAD load
D=/workspace/chip_fp2/eco/lift
S=/root/DGrid-SoC1/.claude/worktrees/asic-rtl-prep/HW/asic/signoff
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
W=/root/.claude/jobs/658ac326/tmp/grok_onehour/out/d1_watch.sh
MAC=/workspace/chip_fp2/handoff/macros_name_w_h_um.txt
PL=$D/d1_place.pl
log() { echo "[followon $(date +%H:%M:%S)] $*"; }
while ! grep -q "ECO_LIFT done" $D/$E.log 2>/dev/null; do sleep 60; done
log "$E done"
bash $W $D/$E.log $D/${E}_drc.rpt | tail -1
if [ -n "$WAIT_PID" ]; then while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 60; done; log "memory gate open (pid $WAIT_PID gone)"; fi
# Metal1 spacing markers along the moved macro's bottom edge (y 2929-2931, x 2883-3121)
awk '/^violation type:/{t=$0} /bbox =/{gsub(/[(),]/," "); x=($3+$6)/2; y=($4+$7)/2; l=$NF; if (y>=2929&&y<=2931&&x>=2880&&x<=3125) {n++; if (l=="Metal1") m1++}} END{printf "EDGE_Y2930 markers=%d metal1=%d\n", n, m1}' $D/${E}_drc.rpt
cd /root/.claude/jobs/658ac326/tmp
IN_ODB=$D/$E.odb MOVES=$D/${E}_moves.txt ERR_DIR=$D/pg_$E $OR -exit $S/grok_lift/pg_check.tcl > $D/pg_$E.log 2>&1
grep -a "PG_CHECK\|unconnected\|PSM-00[3-9]" $D/pg_$E.log | head -8
python3 -I $S/grok_lift/supply_nets_from_rpt.py $D/${E}_drc.rpt $D/${E}_pwr_nets.txt $D/${E}_pwr_pairs.txt
if [ ! -s $D/${E}_pwr_nets.txt ]; then log "no supply-short nets on $E; nothing to guide"; exit 0; fi
IN_ODB=$D/$E.odb PAIRS_FILE=$D/${E}_pwr_pairs.txt $OR -exit $S/nets_pins_xy_exact.tcl > $D/${E}_pwr_pins.log 2>&1
log "pins dumped: $(grep -a -c '^PIN' $D/${E}_pwr_pins.log) lines"
cd $D && python3 -I $S/guide_channels.py ${E}_pwr_pins.log ${E}_pwr_nets.txt $MAC $PL $D/guides_${E}pwr.txt $GRID $HALO || exit 1
log "guides: $(wc -l < $D/guides_${E}pwr.txt) boxes"
cd /root/.claude/jobs/658ac326/tmp
IN_ODB=$D/$E.odb OUT_ODB=$D/${E}g.odb GUIDES_FILE=$D/guides_${E}pwr.txt END=3 THREADS=$T DRC_RPT=$D/${E}g_drc.rpt $OR -exit $S/eco_guides.tcl > $D/${E}g.log 2>&1
log "guided run done"
bash $W $D/${E}g.log $D/${E}g_drc.rpt | tail -1
IN_ODB=$D/${E}g.odb MOVES=$D/${E}_moves.txt ERR_DIR=$D/pg_${E}g $OR -exit $S/grok_lift/pg_check.tcl > $D/pg_${E}g.log 2>&1
grep -a "PG_CHECK" $D/pg_${E}g.log
log "all done"
