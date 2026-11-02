#!/usr/bin/env bash
# IHP SG13CMOS5L LVS (KLayout, official PDK deck libs.tech/klayout/tech/lvs/run_lvs.py).
#
# usage: run_lvs.sh <gds> <topcell> <netlist.cdl|.spice> [options]
#   -o DIR       run directory (default ./lvs_<topcell>)
#   --deep       hierarchical extraction (recommended for full chip / macros; default flat)
#   --implicit N comma list of nets to join by label (e.g. "VDD,VSS" for split power rails)
#   --no-taps    skip ntap1/ptap1 extraction (schematic without tap devices, e.g. std cells)
#   --ports-ok   ignore top-level port mismatches (use for blocks without top pins)
#   --blackbox P blank_circuit(P) on both netlists (repeatable; e.g. 'RM_IHPSG13_*' for SRAMs,
#                'sg13cmos5l_IOPad*' for IO cells); runs a patched copy of the PDK deck
#   -- ARGS      extra args to run_lvs.py (e.g. --purge --purge_nets --combine_devices)
# The schematic netlist may be a single CDL that .INCLUDEs others; for a full chip use the
# merged stdcell + SRAM + IO CDL plus the verilog2cdl'ed top (see README).
# Exit: 0 = netlists match, 1 = mismatch, 2 = tool error.
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$HERE/env.sh"
[ $# -ge 3 ] || { sed -n 2,14p "$0"; exit 2; }
GDS=$(readlink -f "$1"); TOP=$2; NET=$(readlink -f "$3"); shift 3
OUT=./lvs_$TOP; MODE=flat; EXTRA=(); BB=()
while [ $# -gt 0 ]; do
  case $1 in
    -o) OUT=$2; shift ;;
    --deep) MODE=deep ;;
    --implicit) EXTRA+=(--implicit_nets="$2"); shift ;;
    --no-taps) EXTRA+=(--disable_tap_extraction) ;;
    --ports-ok) EXTRA+=(--ignore_top_ports_mismatch) ;;
    --blackbox) BB+=(--blackbox "$2"); shift ;;
    --) shift; EXTRA+=("$@"); break ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
  shift
done
mkdir -p "$OUT"; OUT=$(readlink -f "$OUT")
echo "[run_lvs] $(date '+%F %T') mode=$MODE gds=$GDS top=$TOP netlist=$NET"
RUNNER=$KLAYOUT_TECH/lvs/run_lvs.py
if [ ${#BB[@]} -gt 0 ]; then
  python3 "$HERE/patch_lvs_deck.py" "$OUT/deck" "${BB[@]}" || exit 2
  RUNNER=$OUT/deck/run_lvs.py
fi
T0=$SECONDS
python3 "$RUNNER" --layout="$GDS" --netlist="$NET" --topcell="$TOP" \
  --run_dir="$OUT" --run_mode="$MODE" "${EXTRA[@]}" >"$OUT/run_lvs.stdout" 2>&1
RC=$?
echo "[run_lvs] klayout finished rc=$RC in $((SECONDS-T0)) s; outputs in $OUT"
ls "$OUT"/*.lvsdb 2>/dev/null | sed 's/^/[run_lvs] lvsdb: /'
ls "$OUT"/*.cir 2>/dev/null | sed 's/^/[run_lvs] extracted: /'
if grep -qiE "Congratulations! Netlists match|netlists match" "$OUT/run_lvs.stdout"; then
  echo "[run_lvs] RESULT: MATCH"; exit 0
elif grep -qiE "don't match|do not match|mismatch" "$OUT/run_lvs.stdout"; then
  echo "[run_lvs] RESULT: MISMATCH"; grep -iE "error|mismatch|don't match" "$OUT/run_lvs.stdout" | tail -15
  exit 1
fi
echo "[run_lvs] RESULT: UNKNOWN (rc=$RC)"; tail -25 "$OUT/run_lvs.stdout"; exit 2
