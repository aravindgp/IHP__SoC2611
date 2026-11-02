#!/usr/bin/env bash
# IHP SG13CMOS5L density fill (PDK KLayout filler macros, batch mode).
#
# usage: run_fill.sh <in.gds> <out.gds> [--no-activ] [--no-metal]
#   Runs libs.tech/klayout/tech/scripts/filler.py, which executes
#     macros/sg13cmos5l_filler_ActGatP.lym  (Activ 1/22 + GatPoly 5/22 fill)
#     macros/sg13cmos5l_filler_Metal.lym    (Metal1-4 x/22 + TopMetal1 126/22 fill)
#   Fill goes inside EdgeSeal.holes, i.e. the layout MUST already contain the seal ring
#   (make_sealring.py --input, or the pad-ring GDS); keep-outs: x/23 nofill layers, NoMetFiller 160/0.
#   The input layout must be the final merged chip (top cell = only top cell).
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$HERE/env.sh"
[ $# -ge 2 ] || { sed -n 2,11p "$0"; exit 2; }
IN=$(readlink -f "$1"); OUT=$(readlink -m "$2"); shift 2
RD=()
for o in "$@"; do
  case $o in
    --no-activ) RD+=(-rd no_activ=1) ;;
    --no-metal) RD+=(-rd no_metal=1) ;;
    *) echo "unknown option $o"; exit 2 ;;
  esac
done
mkdir -p "$(dirname "$OUT")"
echo "[run_fill] $(date '+%F %T') $IN -> $OUT"
T0=$SECONDS
klayout -zz -r "$KLAYOUT_TECH/scripts/filler.py" -rd output_file="$OUT" "${RD[@]}" "$IN" > "$OUT.log" 2>&1
RC=$?
echo "[run_fill] rc=$RC in $((SECONDS-T0)) s, log $OUT.log"
[ -s "$OUT" ] || { echo "[run_fill] no output"; tail -20 "$OUT.log"; exit 2; }
exit $RC
