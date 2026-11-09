#!/bin/bash
# One side-move ECO round on a routed chip db: from the base db's DRC report build the (net, macro) pairs of the
# power shorts inside macros, dump those nets' pins, plan the moves (pins_side.py: minority-side cells across the
# macro row, blockage/macro/channel aware), apply them with an incremental global route and a plain detailed route
# (eco_sidemove.tcl), then count the inside-macro shorts of the result.
# usage: eco_round.sh <base.odb> <base_drc.rpt> <out_dir> <place.pl> <blockages.txt> [end_passes=8] [threads=8]
set -u
BASE=$(readlink -m "$1"); RPT=$(readlink -m "$2"); OUT=$(readlink -m "$3"); PL=$4; BLK=$5; END=${6:-8}; T=${7:-8}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
MAC=/workspace/chip_fp2/handoff/macros_name_w_h_um.txt
mkdir -p "$OUT"; cd "$OUT" || exit 1
echo "ECO_ROUND start $(date -u +%T) base=$BASE rpt=$RPT"
python3 -I "$HERE/drc_pairs.py" "$RPT" "$MAC" "$PL" > pairs.txt 2> pairs.summary || exit 1
cat pairs.summary
# OBS=1: put Metal2/Metal4 routing obstructions inside every macro (pin band kept) before the round, so the
# incremental global route of the re-routed nets sees zero capacity there (measured: inside-macro shorts -24 %)
if [ "${OBS:-0}" = 1 ]; then
  IN_ODB=$BASE OUT_ODB=$OUT/base_obs.odb LAYERS="Metal2 Metal4" MARGIN=0 PIN_KEEP=2 "$OR" -exit "$HERE/macro_obs.tcl" > obs.log 2>&1 || { echo "obs failed"; exit 1; }
  grep -a "MACRO_OBS" obs.log; BASE=$OUT/base_obs.odb
fi
# EXTRA_ALL=1: re-route every crossing net of the DRC report (not only the nets of moved cells), as the obstruction
# test did; the nets whose cells are all on one side get a fresh global route with the obstructions in place
if [ "${EXTRA_ALL:-0}" = 1 ]; then
  awk 'NF==3{print $2}' pairs.txt | sort -u > extra_nets.txt; export EXTRA_NETS=$OUT/extra_nets.txt
  echo "ECO_ROUND extra nets to re-route: $(wc -l < extra_nets.txt)"
fi
IN_ODB=$BASE PAIRS_FILE=$OUT/pairs.txt "$OR" -exit "$HERE/nets_pins_xy.tcl" > pins.log 2>&1 || { echo "pins failed"; exit 1; }
python3 -I "$HERE/pins_side.py" pins.log pairs.txt "$MAC" "$PL" 12 "$BLK" > moves.txt 2> moves.summary || exit 1
cat moves.summary
# the legalizer (cap 250/40 um) can fail on a cell with no free site that close to its target: drop those cells
# from the plan and retry (up to 3 times)
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  IN_ODB=$BASE OUT_ODB=$OUT/eco.odb MOVES_FILE=$OUT/moves.txt MAXDISP="250 40" END=$END THREADS=$T DRC_RPT=$OUT/eco_drc.rpt \
    "$OR" -exit "$HERE/eco_sidemove.tcl" > eco.log 2>&1 && break
  if grep -a -q "DPL-0036" eco.log && [ "$attempt" -lt 10 ]; then
    grep -a "DPL-0035" eco.log | awk '{print $3}' | sort -u > "$OUT/dropped_$attempt.txt"
    grep -a -v -F -f "$OUT/dropped_$attempt.txt" "$OUT/moves.txt" > "$OUT/moves_retry.txt" && mv "$OUT/moves_retry.txt" "$OUT/moves.txt"
    echo "ECO_ROUND legalizer rejected $(wc -l < "$OUT/dropped_$attempt.txt") cell(s), retrying with $(grep -a -c '^MOVE' "$OUT/moves.txt") moves"
    continue
  fi
  echo "eco failed"; tail -5 eco.log; exit 1
done
grep -a "ECO_SIDE" eco.log
grep -a "Number of violations" eco.log | grep -a -o "= [0-9]*" | tr '\n' ' '; echo
python3 -I "$HERE/drc_per_macro.py" eco_drc.rpt "$MAC" "$PL" 8 | cut -c1-180
echo "ECO_ROUND done $(date -u +%T) -> $OUT/eco.odb $OUT/eco_drc.rpt"
