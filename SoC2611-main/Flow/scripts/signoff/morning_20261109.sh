#!/bin/bash
# Morning chain for the 9 Nov 2026 09:00 UTC IHP deadline (replaces steps 2-4 of night_20261109.sh after the owner asked
# for more passes on round G):
#  1. wait for round G (24 passes); run up to CONT_END more repair passes on its db (eco_plain.tcl: restarted schedule,
#     existing wires kept) with a hard stop at 05:30 UTC; keep whichever db has the lower total;
#  2. finish chain: bondpad pins + DEF/Verilog, DEF -> GDS, CDL (parallel), seal ring + PDK fill + top-up + density;
#     corner-fill cleanup (fill_corner_clean.py) on both GDS variants if /workspace/chip_fp2/cornerclean_ok exists;
#  3. release v.1.2.0 staging in the IHP repo (whole-file PDK-fill, full-fill parts + xz, labels, hashes, note), push;
#  4. IHP minimum DRC on the full-fill GDS (keeps running).
set -u
HERE=/root/DGrid-SoC1/.claude/worktrees/asic-rtl-prep/HW/asic/signoff
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
E=/workspace/chip_fp2/eco; PL=/workspace/chip_fp2/handoff/H12_cpueast.pl
MAC=/workspace/chip_fp2/handoff/macros_name_w_h_um.txt
REL=/workspace/chip_fp2/release_1200; REPO=/workspace/ihp_ip_repo/IHP__DSOC2610; VER=v.1.2.0; TOP=dgrid_soc1_chip_top
NAME=SoC2611; CONT_END=${CONT_END:-8}
T_HARD=$(date -u -d '2026-11-09 05:30' +%s)
log() { echo "[morning $(date -u +%T)] $*"; }
inside_of() { grep -a -o "^[0-9]* power shorts inside" "$1" 2>/dev/null | awk '{print $1}'; }
last_total() { grep -a "Number of violations" "$1" 2>/dev/null | tail -1 | grep -o "[0-9]*\." | tr -d .; }

# ---------------------------------------------------------------- 1. round G + continuation
R=${ROUND:-G}; RF=${FALLBACK:-F}
log "waiting for round $R"
while ! grep -q -a -E "ECO_ROUND done|eco failed|pins failed" $E/round$R.log 2>/dev/null; do sleep 60; done
if [ -f $E/round$R/eco.odb ] && grep -q -a "ECO_ROUND done" $E/round$R.log; then BASE=$E/round$R/eco.odb; BRPT=$E/round$R/eco_drc.rpt; BLOG=$E/round$R/eco.log; BNAME=$R
else BASE=$E/round$RF/eco.odb; BRPT=$E/round$RF/eco_drc.rpt; BLOG=$E/round$RF/eco.log; BNAME=$RF; fi
inside=$(inside_of $E/round$BNAME.log); total=$(last_total $BLOG)
log "round $BNAME: inside=$inside total=$total"
now=$(date -u +%s)
if [ "$CONT_END" -gt 0 ] && [ "$now" -lt $((T_HARD - 1200)) ]; then
  log "continuation: $CONT_END repair passes on round $BNAME (hard stop 05:30 UTC)"
  IN_ODB=$BASE OUT_ODB=$E/round$BNAME/cont.odb END=$CONT_END THREADS=24 DRC_RPT=$E/round$BNAME/cont_drc.rpt \
    setsid $OR -exit $HERE/eco_plain.tcl > $E/round$BNAME/cont.log 2>&1 &
  pid=$!
  while kill -0 $pid 2>/dev/null; do
    if [ "$(date -u +%s)" -ge "$T_HARD" ]; then log "05:30 UTC: killing the continuation"; kill -TERM -- -$pid 2>/dev/null; sleep 15; kill -KILL -- -$pid 2>/dev/null; break; fi
    sleep 30
  done
  wait $pid 2>/dev/null
  if grep -q -a "ECO_PLAIN done" $E/round$BNAME/cont.log; then
    ctotal=$(last_total $E/round$BNAME/cont.log)
    cinside=$(python3 -I $HERE/drc_per_macro.py $E/round$BNAME/cont_drc.rpt $MAC $PL 8 2>/dev/null | head -1 | awk '{print $1}')
    log "continuation: passes $(grep -a 'Number of violations' $E/round$BNAME/cont.log | grep -o '= [0-9]*' | tr -d '= ' | tr '\n' ' ') inside=$cinside"
    if [ -n "$ctotal" ] && [ "$ctotal" -lt "$total" ]; then BASE=$E/round$BNAME/cont.odb; total=$ctotal; inside=${cinside:-$inside}; BNAME="$BNAME+$CONT_END"; log "using the continuation"; else log "continuation not better, using round $BNAME"; fi
  else log "continuation did not finish, using round $BNAME"; fi
fi
log "routing base for the GDS: $BNAME ($BASE) inside=$inside total=$total"

# ---------------------------------------------------------------- 2. finish chain
mkdir -p $REL $REL/cdl
IN_ODB=$BASE BPINS_TCL=/workspace/chip_fp2/chipH13/bpins.tcl OUT_DIR=$REL $OR -exit $HERE/chip_finish.tcl > $REL/finish.log 2>&1 || { log "chip_finish failed"; exit 1; }
log "chip_finish done"
bash $HERE/stream_chip.sh $REL/chip.def $TOP $REL/chip.gds > $REL/stream.log 2>&1 || { log "stream failed"; exit 1; }
log "stream done $(stat -c %s $REL/chip.gds) bytes"
( bash $HERE/make_chip_cdl.sh $REL/chip.v $REL/chip.def $TOP $REL/cdl/chip.cdl > $REL/cdl.log 2>&1; echo "cdl rc=$?" >> $REL/cdl.log ) &
cdlpid=$!
bash $HERE/release_gds_chain.sh $REL/chip.gds $TOP $REL 6600 2 8 > $REL/chain.log 2>&1 || { log "release_gds_chain failed"; tail -3 $REL/chain.log; exit 1; }
log "release_gds_chain done: $(ls $REL/*.gds | tr '\n' ' ')"
PDKFILL=$REL/${TOP}_pdkfill.gds; FULL=$REL/${TOP}_final.gds
if [ -f /workspace/chip_fp2/cornerclean_ok ]; then
  for v in pdkfill final; do
    klayout -b -r $HERE/fill_corner_clean.py -rd gds=$REL/${TOP}_$v.gds -rd out=$REL/${TOP}_${v}_cc.gds -rd top=$TOP > $REL/cornerclean_$v.log 2>&1 \
      && grep -a FILL_CORNER_CLEAN $REL/cornerclean_$v.log && log "corner clean $v done" || log "corner clean $v failed, using the uncleaned file"
  done
  [ -f $REL/${TOP}_pdkfill_cc.gds ] && PDKFILL=$REL/${TOP}_pdkfill_cc.gds
  [ -f $REL/${TOP}_final_cc.gds ] && FULL=$REL/${TOP}_final_cc.gds
fi
wait $cdlpid; log "cdl: $(tail -1 $REL/cdl.log)"

# ---------------------------------------------------------------- 3. release staging v.1.2.0
cd $REPO || exit 1
git pull -q --ff-only origin main 2>/dev/null
python3 -I $HERE/ihp_release.py $REPO $NAME $PDKFILL $TOP $REL/chip.v $REL/cdl/chip.cdl $VER > $REL/release.log 2>&1 || { log "ihp_release failed"; tail -3 $REL/release.log; exit 1; }
python3 -I $HERE/ihp_sealring_label.py $REPO/release/$VER/gds/$NAME.gds.gz $REL/${NAME}_pdkfill_labeled.gds.gz > $REL/label.log 2>&1 && cp $REL/${NAME}_pdkfill_labeled.gds.gz $REPO/release/$VER/gds/$NAME.gds.gz
SCR=$REL/repo_full; mkdir -p $SCR/doc; cp $REPO/doc/info.json $SCR/doc/info.json
python3 -I $HERE/ihp_release.py $SCR $NAME $FULL $TOP $REL/chip.v $REL/cdl/chip.cdl $VER > $REL/release_full.log 2>&1
python3 -I $HERE/ihp_sealring_label.py $SCR/release/$VER/gds/$NAME.gds.gz $REL/${NAME}_fullfill_labeled.gds.gz > $REL/label_full.log 2>&1
rm -f $REPO/release/$VER/gds/${NAME}_fullfill.gds.gz.*.part
split -d -b 95M $REL/${NAME}_fullfill_labeled.gds.gz $REPO/release/$VER/gds/${NAME}_fullfill.gds.gz. --additional-suffix=.part
gzip -dc $REL/${NAME}_fullfill_labeled.gds.gz | xz -T 8 -6 > $REL/${NAME}_fullfill.gds.xz
xzsz=$(stat -c %s $REL/${NAME}_fullfill.gds.xz)
if [ "$xzsz" -lt 99000000 ]; then cp $REL/${NAME}_fullfill.gds.xz $REPO/release/$VER/gds/; log "xz variant $xzsz bytes added"; else log "xz variant $xzsz bytes too big for GitHub, not added"; fi
cd $REPO/release/$VER && sha256sum gds/* netlist/* > $REL/sha256.txt
cp $REL/density.txt $REPO/release/$VER/density_fullfill.txt 2>/dev/null; cp $REL/density_pdkfill.txt $REPO/release/$VER/density_pdkfill.txt 2>/dev/null
{
  echo "# $NAME $VER - release note ($(date -u '+%-d %B %Y, %H:%M UTC'))"; echo
  echo "> **Status: PRELIMINARY, built overnight for the 9 November deadline.** Routed state after ECO round $BNAME:"
  echo "> $inside power shorts inside the SRAM macros remain, total detailed-route violations $total."
  echo "> Antenna repair, LVS and timing sign-off not run on this GDS. DRC (IHP minimum deck) running, result to follow."; echo
  echo "## Contents"
  echo "- \`gds/$NAME.gds.gz\`: whole file (the one \`doc/info.json\` points at), seal ring + label, PDK lattice fill only (under GitHub's 100 MB limit)."
  echo "- \`gds/${NAME}_fullfill.gds.gz.00.part\` + \`.01.part\`: same routing with PDK fill + top-up fill, density clean; reassemble with \`cat\` and check the hash below."
  [ "$xzsz" -lt 99000000 ] && echo "- \`gds/${NAME}_fullfill.gds.xz\`: the same full-fill GDS as one xz file."
  echo "- \`netlist/$NAME.cdl.gz\`, \`netlist/$NAME.v.gz\`: LVS netlist and post-route Verilog."
  echo "- \`density_fullfill.txt\`, \`density_pdkfill.txt\`: density_fast.py results of both variants."; echo
  echo "## SHA-256"; echo '```'; cat $REL/sha256.txt; echo "fullfill reassembled: $(sha256sum $REL/${NAME}_fullfill_labeled.gds.gz | cut -c1-64)"; echo '```'; echo
  echo "## Source state"
  echo "Floorplan H13 + side-move / obstruction ECO rounds A-G (\`SoC2611-main/Flow/scripts/signoff/eco_round.sh\`), OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified."
  echo "Known open items: shorts inside the SRAM macros listed above, antenna, hold timing, LVS, waivers."
} > $REPO/release/$VER/ReleaseNote.md
cd $REPO && git add release/$VER doc/info.json && git -c user.name=aravindgp -c user.email=sai@deepgridsemi.com commit -q -m "release $VER: routed state after ECO round $BNAME ($inside inside-macro shorts, $total violations), seal ring, fill, density, netlists, hashes" && git push -q origin main 2>&1 | tail -1
log "release $VER pushed: $(git log --oneline -1)"

# ---------------------------------------------------------------- 4. DRC on the full-fill GDS (runs on)
nohup bash $HERE/run_drc.sh $FULL $TOP -m minimum -o /workspace/chip_fp2/drc_1200_min -j 8 > /workspace/chip_fp2/drc_1200_min.log 2>&1 &
log "IHP minimum DRC started on $FULL"
log "MORNING DONE"
