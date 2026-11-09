#!/usr/bin/env bash
# Dry-run all candidate shift lists on the same db (read-only, run in parallel, ~5 min): footprint / strip / push /
# PDN numbers side by side.   usage: compare_options.sh <IN_ODB>   (env SIGNOFF, OUTD)
set -u
IN=$1; OUTD=${OUTD:-/workspace/knot2/out}; SIGNOFF=${SIGNOFF:?set SIGNOFF}
mkdir -p $OUTD/cmp
for s in shift_d1_s27_east63 shift_b_col3_east40 shift_b_col3_east63 shift_K2; do
  bash $SIGNOFF/run_tcl.sh $OUTD/nets_under_footprint.tcl $OUTD/cmp/$s.log IN_ODB=$IN SHIFT_FILE=$OUTD/$s.txt \
      STRIP_OUT=$OUTD/cmp/$s.strip.txt > /dev/null &
done
wait
for s in shift_d1_s27_east63 shift_b_col3_east40 shift_b_col3_east63 shift_K2; do
  echo "== $s"; grep -E "^(STRIP|PUSH|PDN|FOOT ERROR)" $OUTD/cmp/$s.log
done
