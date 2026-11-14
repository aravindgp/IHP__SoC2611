#!/usr/bin/env bash
# DRC check of the GDS in this folder with the IHP SG13CMOS5L KLayout deck, minimum rule set (the foundry precheck),
# deep mode. Made to be picked up from GitHub on any Linux machine: the GDS is next to this script, the rule deck
# is fetched from the public IHP-Open-PDK repository at the commit the design was built with.
#
# usage: bash run_drc_check.sh [tables at a time=3] [threads per table=4]        all 27 tables and the density deck
#        TABLES=gatpolyfiller DENSITY=0 bash run_drc_check.sh 1 8                one table only
# env:   TABLES="..." (default: all 27)   DENSITY=1|0 (density deck in its own slot)   WORK=<dir> (default ./work)
#        DRY=1 (fetch the deck, print the commands, do not run)
# needs: git, Python 3, KLayout 0.30.x (klayout on the PATH and: pip install klayout docopt), 64 GB of memory for
#        3 tables at a time (the GatPoly filler table alone takes up to 35 GB at 4 threads), 5 GB of disk.
# Times on a 32-core machine: GatPoly filler table 3 hours at 4 threads, seal ring table 2.8 hours, density deck
# 2.7 hours, the other tables 7 to 60 minutes each.
# The Nwell table is left out: in the minimum rule set all four of its rules (NW.b, NW.b1, NW.f1, NW.f1.digibnd)
# are switched off, and the table then only builds the connectivity of the whole chip, which does not finish.
set -u
cd "$(dirname "$(readlink -f "$0")")"
NAME=SoC2611; TOP=SoC2611
PDK_SHA=dcb03b1e2d24250bccbb2e8783d55d2b4f734f14
MP=${1:-3}; THR=${2:-4}
WORK=${WORK:-$PWD/work}; mkdir -p "$WORK/drc_out/tables" "$WORK/drc_out/rest"
P=$WORK/drc_out/progress.log
[ -s gds/$NAME.gds.gz ] || { echo "gds/$NAME.gds.gz missing"; exit 1; }
if [ -s gds/$NAME.gds.gz.sha256 ]; then ( cd gds && sha256sum -c $NAME.gds.gz.sha256 ) || { echo "GDS hash differs"; exit 1; }; fi
if [ ! -s "$WORK/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/klayout/tech/drc/run_drc.py" ]; then
  git clone -q --filter=blob:none --no-checkout https://github.com/IHP-GmbH/IHP-Open-PDK "$WORK/IHP-Open-PDK" || exit 1
  git -C "$WORK/IHP-Open-PDK" sparse-checkout set ihp-sg13cmos5l/libs.tech/klayout ihp-sg13g2/libs.tech/klayout || exit 1
  git -C "$WORK/IHP-Open-PDK" checkout -q $PDK_SHA || { echo "cannot check out IHP-Open-PDK $PDK_SHA"; exit 1; }
fi
echo "[drc] rule deck: IHP-Open-PDK $(git -C "$WORK/IHP-Open-PDK" rev-parse HEAD)" | tee -a "$P"
DRC="$WORK/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/klayout/tech/drc"
[ -s "$WORK/$NAME.gds" ] || gunzip -c gds/$NAME.gds.gz > "$WORK/$NAME.gds"
export QT_QPA_PLATFORM=offscreen
TABLES=${TABLES:-"activ activfiller cont contbar forbidden forbidden_cmos5l gatpoly gatpolyfiller latchup lbe metal1 metaln metalnfiller metalslits nbulay pad passiv pin psd pwellblock sealring thickgateox topmetal1 topmetal1filler topvia1 via1 vian"}
DENSITY=${DENSITY:-1}
NT=$(( $(echo $TABLES | wc -w) + DENSITY ))
TB=""; for t in $TABLES; do TB="$TB --table=$t"; done
RUN="python3 $DRC/run_drc.py --path=$WORK/$NAME.gds --topcell=$TOP --run_mode=deep --minimum_drc --disable_extra_rules --density_thr=$THR"
if [ -n "${DRY:-}" ]; then echo "$RUN --run_dir=$WORK/drc_out/tables --mp=$MP $TB"; [ "$DENSITY" = 1 ] && echo "$RUN --run_dir=$WORK/drc_out/rest --mp=1 --density_only"; exit 0; fi
echo "[drc] start $(date -u '+%F %T') UTC on $(hostname), KLayout $(klayout -v 2>/dev/null | head -1), $MP tables at a time, density slot: $DENSITY, $THR threads per table; tables: $TABLES" | tee -a "$P"
( while sleep 600; do echo "[drc] $(date -u '+%F %T') UTC  tables finished: $(cat "$WORK"/drc_out/run_drc.stdout "$WORK"/drc_out/run_drc_rest.stdout 2>/dev/null | grep -a -c "KLayout DRC run for") of $NT  memory of klayout: $(ps -C klayout -o rss= | awk '{s+=$1} END {printf "%.1f GB", s/1048576}')" >> "$P"; done ) &
W=$!
R2=""
if [ "$DENSITY" = 1 ]; then
  ( $RUN --run_dir="$WORK/drc_out/rest" --mp=1 --density_only > "$WORK/drc_out/run_drc_rest.stdout" 2>&1; echo "[drc] density deck end $(date -u '+%F %T') UTC, exit $?" >> "$P" ) &
  R2=$!
fi
$RUN --run_dir="$WORK/drc_out/tables" --mp=$MP $TB > "$WORK/drc_out/run_drc.stdout" 2>&1
echo "[drc] tables end $(date -u '+%F %T') UTC, exit $?" | tee -a "$P"
[ -n "$R2" ] && wait $R2
kill $W 2>/dev/null
echo "[drc] end $(date -u '+%F %T') UTC; tables finished: $(cat "$WORK"/drc_out/run_drc.stdout "$WORK"/drc_out/run_drc_rest.stdout 2>/dev/null | grep -a -c "KLayout DRC run for") of $NT; killed by the system: $(cat "$WORK"/drc_out/run_drc.stdout "$WORK"/drc_out/run_drc_rest.stdout 2>/dev/null | grep -a -c '^Killed')" | tee -a "$P"
grep -a -h "KLayout DRC run for\|DRC Check Passed\|violations" "$WORK"/drc_out/run_drc.stdout "$WORK"/drc_out/run_drc_rest.stdout 2>/dev/null | sed 's/^.*: KLayout/KLayout/; s/^.*| //' | tail -40 | tee -a "$P"
echo "[drc] send back: $P"
