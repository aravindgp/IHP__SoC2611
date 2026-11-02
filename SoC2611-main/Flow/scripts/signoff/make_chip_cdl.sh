#!/usr/bin/env bash
# Chip-level LVS netlist: verilog2cdl (DGSE) of the integrated chip netlist, with the std-cell, SRAM and
# IO cell CDLs inlined (KLayout's SPICE reader truncates .INCLUDE paths at '-', and this repo path has one).
#
# usage: make_chip_cdl.sh <chip.v> <chip.def> <top> <out.cdl>
# SRAM CDLs get 's/ lvsres / res_metal1 /' (sg13g2 SRAM CDL resistor name vs CMOS5L LVS deck).
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$HERE/env.sh"
[ $# -ge 4 ] || { sed -n 2,6p "$0"; exit 2; }
V=$(readlink -f "$1"); DEF=$(readlink -f "$2"); TOP=$3; OUT=$(readlink -m "$4")
R=$PDK_ROOT/ihp-sg13cmos5l/libs.ref
D=$(dirname "$OUT"); mkdir -p "$D"
CELLS=$D/cells_merged.cdl
python3 "$HERE/merge_cell_cdl.py" "$CELLS" "$R/sg13cmos5l_stdcell/cdl/sg13cmos5l_stdcell.cdl" \
  "$R"/sg13cmos5l_sram/cdl/RM_IHPSG13_*.cdl "$R/sg13cmos5l_io/cdl/sg13cmos5l_io.cdl" || exit 2
python3 "$DGSE_ROOT/scripts/verilog2cdl.py" --netlist "$V" --top "$TOP" --cdl "$CELLS" --out "$OUT.top" --def "$DEF" \
  > "$OUT.log" 2>&1 || { echo "[make_chip_cdl] verilog2cdl failed"; tail "$OUT.log"; exit 2; }
# inline: drop the .INCLUDE, prepend the merged cell CDL (de-duplicated subckts are fine: same file once)
python3 "$HERE/fix_cdl_io_supplies.py" "$CELLS" "$OUT.top" "$TOP" "$OUT.top2" || exit 2
{ cat "$CELLS"; grep -v -i '^\.include' "$OUT.top2"; } > "$OUT"
echo "[make_chip_cdl] $OUT ($(grep -c -i '^\.subckt' "$OUT") subckts); log $OUT.log"
tail -3 "$OUT.log"
