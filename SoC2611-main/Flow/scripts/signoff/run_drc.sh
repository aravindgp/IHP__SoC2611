#!/usr/bin/env bash
# IHP SG13CMOS5L physical DRC (KLayout, official PDK deck).
#
# usage: run_drc.sh <gds|gds.gz|oas> <topcell> [options]
#   -o DIR          run directory            (default: ./drc_<topcell>)
#   -m full|minimum full = all main rule tables + density + antenna (default)
#                   minimum = IHP "minimum layout rule set" (foundry precheck) + density
#   --maximal       also run rule_decks/sg13cmos5l_maximal.drc (legacy sg13g2-derived full deck;
#                   NOT needed for CMOS5L per run_drc.py help; used >13 GB on the empty 6.6 mm pad
#                   ring and did not finish in 5 min -> off by default, never on a full chip here)
#   --block         block/macro run: waive global/windowed density (waivers/block_density.txt)
#   -j N            parallel klayout processes (default 4; each ~1-3 GB on a full chip)
#   -w FILE         waiver file for the summary (default: signoff/waivers/drc_waivers.txt)
#   --no-antenna    skip antenna deck
#   --no-density    skip density deck
#   --flat          KLayout flat mode instead of deep (hierarchical)
#   -- ARGS         extra args passed to the PDK run_drc.py
# Exit status: 0 = no unwaived violations, 1 = unwaived violations, 2 = tool error.
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$HERE/env.sh"

[ $# -ge 2 ] || { sed -n 2,14p "$0"; exit 2; }
GDS=$(readlink -f "$1"); TOP=$2; shift 2
OUT=./drc_$TOP; MODE=full; MP=4; WAIVERS=$HERE/waivers/drc_waivers.txt
ANT=1; DENS=1; RUNMODE=deep; EXTRA=(); MAXIMAL=0; BLOCK=0
while [ $# -gt 0 ]; do
  case $1 in
    -o) OUT=$2; shift ;;
    -m) MODE=$2; shift ;;
    -j) MP=$2; shift ;;
    -w) WAIVERS=$2; shift ;;
    --no-antenna) ANT=0 ;;
    --no-density) DENS=0 ;;
    --flat) RUNMODE=flat ;;
    --maximal) MAXIMAL=1 ;;
    --block) BLOCK=1 ;;
    --) shift; EXTRA=("$@"); break ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
  shift
done
mkdir -p "$OUT"; OUT=$(readlink -f "$OUT")
rm -f "$OUT"/*.lyrdb "$OUT"/summary.*

ARGS=(--path="$GDS" --topcell="$TOP" --run_dir="$OUT" --mp="$MP" --run_mode="$RUNMODE")
if [ "$MODE" = minimum ]; then
  ARGS+=(--minimum_drc)
else
  [ $ANT = 1 ] && ARGS+=(--antenna)
fi
[ $DENS = 0 ] && ARGS+=(--no_density)
[ $MAXIMAL = 0 ] && ARGS+=(--disable_extra_rules)
[ $DENS = 1 ] && ARGS+=(--density_thr="$MP")

echo "[run_drc] $(date '+%F %T') deck=$KLAYOUT_TECH/drc/run_drc.py mode=$MODE gds=$GDS top=$TOP"
T0=$SECONDS
python3 "$KLAYOUT_TECH/drc/run_drc.py" "${ARGS[@]}" "${EXTRA[@]}" \
  >"$OUT/run_drc.stdout" 2>&1
RC=$?
echo "[run_drc] klayout finished rc=$RC in $((SECONDS-T0)) s"
ls "$OUT"/*.lyrdb >/dev/null 2>&1 || { echo "[run_drc] no lyrdb produced (rc=$RC), see $OUT/run_drc.stdout"; tail -20 "$OUT/run_drc.stdout"; exit 2; }
grep -q "ERROR" "$OUT/run_drc.stdout" && { echo "[run_drc] WARNING: errors in log:"; grep ERROR "$OUT/run_drc.stdout" | head; }
WARG=(); [ -f "$WAIVERS" ] && WARG=(--waivers "$WAIVERS")
[ $BLOCK = 1 ] && WARG+=(--waivers "$HERE/waivers/block_density.txt")
python3 "$HERE/summarize_lyrdb.py" "${WARG[@]}" --json "$OUT/summary.json" $(ls "$OUT"/*_full.lyrdb 2>/dev/null || echo "$OUT") | tee "$OUT/summary.txt"
exit "${PIPESTATUS[0]}"
