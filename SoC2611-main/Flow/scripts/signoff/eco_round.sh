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
IN_ODB=$BASE PAIRS_FILE=$OUT/pairs.txt "$OR" -exit "$HERE/nets_pins_xy.tcl" > pins.log 2>&1 || { echo "pins failed"; exit 1; }
python3 -I "$HERE/pins_side.py" pins.log pairs.txt "$MAC" "$PL" 12 "$BLK" > moves.txt 2> moves.summary || exit 1
cat moves.summary
IN_ODB=$BASE OUT_ODB=$OUT/eco.odb MOVES_FILE=$OUT/moves.txt MAXDISP="250 40" END=$END THREADS=$T DRC_RPT=$OUT/eco_drc.rpt \
  "$OR" -exit "$HERE/eco_sidemove.tcl" > eco.log 2>&1 || { echo "eco failed"; tail -5 eco.log; exit 1; }
grep -a "ECO_SIDE" eco.log
grep -a "Number of violations" eco.log | grep -a -o "= [0-9]*" | tr '\n' ' '; echo
python3 -I "$HERE/drc_per_macro.py" eco_drc.rpt "$MAC" "$PL" 8 | cut -c1-180
echo "ECO_ROUND done $(date -u +%T) -> $OUT/eco.odb $OUT/eco_drc.rpt"
