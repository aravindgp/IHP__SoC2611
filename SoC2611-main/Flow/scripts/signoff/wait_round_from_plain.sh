#!/bin/bash
# Expose the result of an eco_plain.tcl run as a "round" for morning_20261109.sh: wait for ECO_PLAIN done, count the
# power shorts inside macros, write round<R>.log with the lines the chain script reads.
# usage: wait_round_from_plain.sh <plain.log> <out.odb> <drc.rpt> <R>
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
LOG=$1; ODB=$2; RPT=$3; R=$4; E=/workspace/chip_fp2/eco
MAC=/workspace/chip_fp2/handoff/macros_name_w_h_um.txt; PL=/workspace/chip_fp2/handoff/H12_cpueast.pl
while ! grep -q -a "ECO_PLAIN done" "$LOG" 2>/dev/null; do sleep 60; done
mkdir -p $E/round$R
ln -sf "$ODB" $E/round$R/eco.odb; ln -sf "$RPT" $E/round$R/eco_drc.rpt; ln -sf "$LOG" $E/round$R/eco.log
python3 -I $HERE/drc_per_macro.py "$RPT" $MAC $PL 8 2>/dev/null | head -1 > $E/round$R.log
echo "ECO_ROUND done $(date -u +%T) -> $E/round$R/eco.odb" >> $E/round$R.log
cat $E/round$R.log
