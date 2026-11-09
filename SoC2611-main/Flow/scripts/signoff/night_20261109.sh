#!/bin/bash
# Night autopilot for the 9 Nov 2026 10:00 CET (09:00 UTC) IHP deadline.
#  1. wait for ECO round E; chain rounds F, G, ... (EXTRA_ALL=1, 24 passes, obstructions already in the db) from the
#     previous round's db until the inside-macro shorts are 0; no new round starts after 03:00 UTC and a running
#     round is killed at 06:00 UTC (the previous round's db is then used);
#  2. finish chain on the best db: bondpad pins + DEF/Verilog, DEF -> GDS, CDL (in parallel), seal ring + PDK fill +
#     top-up fill + density (release_gds_chain.sh);
#  3. stage release v.1.2.0 in the IHP repo like v.1.1.0: whole file = PDK-fill variant (< 100 MB), full-fill
#     (density-clean) variant as two parts and as .xz, labels, SHA-256, release note; commit + push;
#  4. start the IHP minimum DRC on the full-fill GDS (keeps running after this script).
# Antenna repair is deliberately skipped (rehearsal: 2 h 21 min and 9,085 collateral violations; not in the
# precheck's minimum deck).  Log: /workspace/chip_fp2/night_20261109.log
set -u
HERE=<design-repo>/HW/asic/signoff
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
E=/workspace/chip_fp2/eco
PL=/workspace/chip_fp2/handoff/H12_cpueast.pl; BLK=/workspace/chip_fp2/dpass/H13-pockets_blockages.txt
REL=/workspace/chip_fp2/release_1200; REPO=/workspace/ihp_ip_repo/IHP__DSOC2610; VER=v.1.2.0; TOP=soc2611_chip_top
NAME=SoC2611
T_NOROUND=$(date -u -d '2026-11-09 03:00' +%s); T_HARD=$(date -u -d '2026-11-09 06:00' +%s)
log() { echo "[night $(date -u +%T)] $*"; }
inside_of() { grep -a -o "^[0-9]* power shorts inside" "$1" 2>/dev/null | awk '{print $1}'; }
last_total() { grep -a "Number of violations" "$1" 2>/dev/null | tail -1 | grep -o "[0-9]*\." | tr -d .; }

# ---------------------------------------------------------------- 1. rounds
log "waiting for round E"
while ! grep -q -a -E "ECO_ROUND done|eco failed|pins failed" $E/roundE.log 2>/dev/null; do sleep 60; done
prev=E
if [ ! -f $E/roundE/eco.odb ] || ! grep -q -a "ECO_ROUND done" $E/roundE.log; then log "round E failed, base = round D"; prev=D; fi
inside=$(inside_of $E/round$prev.log); [ -n "$inside" ] || inside=999
log "round $prev: inside=$inside total=$(last_total $E/round$prev/eco.log)"
for nxt in F G H I J; do
  now=$(date -u +%s)
  [ "$now" -le "$T_NOROUND" ] || { log "after 03:00 UTC: no new round"; break; }
  [ "$inside" -gt 0 ] || { log "inside-macro shorts 0: rounds done"; break; }
  log "round $nxt start from round $prev"
  EXTRA_ALL=1 setsid bash $HERE/eco_round.sh $E/round$prev/eco.odb $E/round$prev/eco_drc.rpt $E/round$nxt $PL $BLK 24 24 > $E/round$nxt.log 2>&1 &
  pid=$!
  while kill -0 $pid 2>/dev/null; do
    if [ "$(date -u +%s)" -ge "$T_HARD" ]; then log "06:00 UTC: killing round $nxt"; kill -TERM -- -$pid 2>/dev/null; sleep 20; kill -KILL -- -$pid 2>/dev/null; break; fi
    sleep 60
  done
  wait $pid 2>/dev/null
  if ! grep -q -a "ECO_ROUND done" $E/round$nxt.log; then log "round $nxt did not finish ($(tail -1 $E/round$nxt.log | cut -c1-100)); keeping round $prev"; break; fi
  inside=$(inside_of $E/round$nxt.log); [ -n "$inside" ] || inside=999
  log "round $nxt: inside=$inside total=$(last_total $E/round$nxt/eco.log)"
  prev=$nxt
done
BASE=$E/round$prev/eco.odb
log "routing base for the GDS: round $prev ($BASE), inside=$inside"

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
wait $cdlpid; log "cdl: $(tail -1 $REL/cdl.log)"

# ---------------------------------------------------------------- 3. release staging v.1.2.0
cd $REPO || exit 1
git pull -q --ff-only origin main 2>/dev/null
python3 -I $HERE/ihp_release.py $REPO $NAME $REL/${TOP}_pdkfill.gds $TOP $REL/chip.v $REL/cdl/chip.cdl $VER > $REL/release.log 2>&1 || { log "ihp_release failed"; tail -3 $REL/release.log; exit 1; }
python3 -I $HERE/ihp_sealring_label.py $REPO/release/$VER/gds/$NAME.gds.gz $REL/${NAME}_pdkfill_labeled.gds.gz > $REL/label.log 2>&1 && cp $REL/${NAME}_pdkfill_labeled.gds.gz $REPO/release/$VER/gds/$NAME.gds.gz
# full-fill variant staged in a scratch copy, then split into < 100 MB parts and an .xz
SCR=$REL/repo_full; mkdir -p $SCR/doc; cp $REPO/doc/info.json $SCR/doc/info.json
python3 -I $HERE/ihp_release.py $SCR $NAME $REL/${TOP}_final.gds $TOP $REL/chip.v $REL/cdl/chip.cdl $VER > $REL/release_full.log 2>&1
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
  echo "> **Status: PRELIMINARY, built overnight for the 9 November deadline.** Routed state after ECO round $prev:"
  echo "> $inside power shorts inside the SRAM macros remain, total detailed-route violations $(last_total $E/round$prev/eco.log)."
  echo "> Antenna repair, LVS and timing sign-off not run on this GDS. DRC (IHP minimum deck) running, result to follow."; echo
  echo "## Contents"
  echo "- \`gds/$NAME.gds.gz\`: whole file (the one \`doc/info.json\` points at), seal ring + label, PDK lattice fill only (under GitHub's 100 MB limit)."
  echo "- \`gds/${NAME}_fullfill.gds.gz.00.part\` + \`.01.part\`: same routing with PDK fill + top-up fill, density clean; reassemble with \`cat\` and check the hash below."
  [ "$xzsz" -lt 99000000 ] && echo "- \`gds/${NAME}_fullfill.gds.xz\`: the same full-fill GDS as one xz file."
  echo "- \`netlist/$NAME.cdl.gz\`, \`netlist/$NAME.v.gz\`: LVS netlist and post-route Verilog."
  echo "- \`density_fullfill.txt\`, \`density_pdkfill.txt\`: density_fast.py results of both variants."; echo
  echo "## SHA-256"; echo '```'; cat $REL/sha256.txt; echo "fullfill reassembled: $(sha256sum $REL/${NAME}_fullfill_labeled.gds.gz | cut -c1-64)"; echo '```'; echo
  echo "## Source state"
  echo "Floorplan H13 + side-move / obstruction ECO rounds A-$prev (\`SoC2611-main/Flow/scripts/signoff/eco_round.sh\`), OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified."
  echo "Known open items: shorts inside the SRAM macros listed above, antenna, hold timing, LVS, waivers."
} > $REPO/release/$VER/ReleaseNote.md
cd $REPO && git add release/$VER doc/info.json && git -c user.name=aravindgp -c user.email=sai@soc2611semi.com commit -q -m "release $VER: overnight routed state (ECO round $prev, $inside inside-macro shorts), seal ring, fill, density, netlists, hashes" && git push -q origin main 2>&1 | tail -1
log "release $VER pushed: $(git log --oneline -1)"

# ---------------------------------------------------------------- 4. DRC on the full-fill GDS (runs on)
nohup bash $HERE/run_drc.sh $REL/${TOP}_final.gds $TOP -m minimum -o /workspace/chip_fp2/drc_1200_min -j 8 > /workspace/chip_fp2/drc_1200_min.log 2>&1 &
log "IHP minimum DRC started on $REL/${TOP}_final.gds"
log "NIGHT DONE"
