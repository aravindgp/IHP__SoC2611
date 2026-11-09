#!/bin/bash
# Stage a release in the IHP repo from a finished release_gds_chain output directory and push it.
# usage: stage_release.sh <rel_dir> <version> <round_label> <inside_shorts> <both_supply_nets> <total_violations>
# Whole file = PDK-fill variant (< 100 MB gz), full-fill variant as two 95 MB parts (+ .xz if < 99 MB), labels, hashes.
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REL=$1; VER=$2; RND=$3; INSIDE=$4; BOTH=$5; TOTAL=$6
REPO=/workspace/ihp_ip_repo/IHP__DSOC2610; TOP=soc2611_chip_top; NAME=SoC2611
log() { echo "[stage $(date -u +%T)] $*"; }
cd $REPO || exit 1
git pull -q --ff-only origin main 2>/dev/null
python3 -I $HERE/ihp_release.py $REPO $NAME $REL/${TOP}_pdkfill.gds $TOP $REL/chip.v $REL/cdl/chip.cdl $VER > $REL/release.log 2>&1 || { log "ihp_release failed"; tail -3 $REL/release.log; exit 1; }
log "whole file staged"
python3 -I $HERE/ihp_sealring_label.py $REPO/release/$VER/gds/$NAME.gds.gz $REL/${NAME}_pdkfill_labeled.gds.gz > $REL/label.log 2>&1 && cp $REL/${NAME}_pdkfill_labeled.gds.gz $REPO/release/$VER/gds/$NAME.gds.gz
SCR=$REL/repo_full; mkdir -p $SCR/doc; cp $REPO/doc/info.json $SCR/doc/info.json
python3 -I $HERE/ihp_release.py $SCR $NAME $REL/${TOP}_final.gds $TOP $REL/chip.v $REL/cdl/chip.cdl $VER > $REL/release_full.log 2>&1
python3 -I $HERE/ihp_sealring_label.py $SCR/release/$VER/gds/$NAME.gds.gz $REL/${NAME}_fullfill_labeled.gds.gz > $REL/label_full.log 2>&1
rm -f $REPO/release/$VER/gds/${NAME}_fullfill.gds.gz.*.part
split -d -b 95M $REL/${NAME}_fullfill_labeled.gds.gz $REPO/release/$VER/gds/${NAME}_fullfill.gds.gz. --additional-suffix=.part
log "full-fill parts staged"
gzip -dc $REL/${NAME}_fullfill_labeled.gds.gz | xz -T 8 -6 > $REL/${NAME}_fullfill.gds.xz
xzsz=$(stat -c %s $REL/${NAME}_fullfill.gds.xz)
if [ "$xzsz" -lt 99000000 ]; then cp $REL/${NAME}_fullfill.gds.xz $REPO/release/$VER/gds/; log "xz variant $xzsz bytes added"; else log "xz variant $xzsz bytes too big, not added"; fi
cd $REPO/release/$VER && sha256sum gds/* netlist/* > $REL/sha256.txt
[ -s $REL/density.txt ] && cp $REL/density.txt $REPO/release/$VER/density_fullfill.txt
[ -s $REL/density_pdkfill.txt ] && cp $REL/density_pdkfill.txt $REPO/release/$VER/density_pdkfill.txt
DENS="density check: running at staging time, result file follows"
[ -s $REL/density.txt ] && DENS="density: $(tail -1 $REL/density.txt)"
{
  echo "# $NAME $VER - release note ($(date -u '+%-d %B %Y, %H:%M UTC'))"; echo
  echo "> **Status: PRELIMINARY, not for fabrication.** Routed state after ECO round $RND:"
  echo "> $INSIDE power shorts inside the SRAM macros, $BOTH nets touching VDD and VSS both, $TOTAL detailed-route violations in total"
  echo "> (about 1,200 of them signal-to-signal shorts in one congestion knot around the dp_sink3 / dp_fetch SRAM block)."
  echo "> Antenna repair, LVS and timing sign-off not run on this GDS. $DENS."; echo
  echo "## Contents"
  echo "- \`gds/$NAME.gds.gz\`: whole file (the one \`doc/info.json\` points at), seal ring + label, PDK lattice fill only (under GitHub's 100 MB limit)."
  echo "- \`gds/${NAME}_fullfill.gds.gz.00.part\` + \`.01.part\`: same routing with PDK fill + top-up fill; reassemble with \`cat\` and check the hash below."
  [ "$xzsz" -lt 99000000 ] && echo "- \`gds/${NAME}_fullfill.gds.xz\`: the same full-fill GDS as one xz file."
  echo "- \`netlist/$NAME.cdl.gz\`, \`netlist/$NAME.v.gz\`: LVS netlist and post-route Verilog."; echo
  echo "## SHA-256"; echo '```'; cat $REL/sha256.txt; echo "fullfill reassembled: $(sha256sum $REL/${NAME}_fullfill_labeled.gds.gz | cut -c1-64)"; echo '```'; echo
  echo "## Source state"
  echo "Floorplan H13 + ECO rounds A-$RND (\`SoC2611-main/Flow/scripts/signoff/eco_round.sh\`), OpenROAD dcf36133, IHP-Open-PDK sg13cmos5l unmodified."
  echo "Same day, on a trial database (round H + explicit channel guides), the supply shorts are at zero; see \`../../STATUS_2026-11-09.md\`."
  echo "Known open items: the signal-short knot, antenna, hold timing, LVS, waivers."
} > $REPO/release/$VER/ReleaseNote.md
cd $REPO && git add release/$VER doc/info.json && git -c user.name=aravindgp -c user.email= commit -q -m "release $VER: routed state after ECO round $RND ($INSIDE inside-macro shorts, $BOTH supply-short nets, $TOTAL violations), seal ring, fill, netlists, hashes" && git push -q origin main 2>&1 | tail -1
log "release $VER pushed: $(git log --oneline -1)"
