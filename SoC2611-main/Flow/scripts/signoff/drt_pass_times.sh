#!/bin/bash
# Per-pass table of a DRT run: pass, end time (IST, from the snapshot file mtime), minutes since the previous pass,
# violations after the pass (from drt_chip.log).  usage: drt_pass_times.sh <drt_dir>
set -u
D=$1
S=$D/drt_snap
L=$D/drt_chip.log
grep -a "Number of violations" "$L" | grep -a -o "[0-9]*\.$" | tr -d . > "$D/.viol.txt"
: > "$D/.snaps.txt"
for f in $(ls "$S" | sed 's/drt_iter//; s/.odb//' | sort -n); do
  t=$(stat -c %Y "$S/drt_iter$f.odb")
  echo "$f $t $(TZ=Asia/Kolkata date -d @$t '+%d-%b %H:%M')" >> "$D/.snaps.txt"
done
paste -d ' ' "$D/.snaps.txt" "$D/.viol.txt" | awk 'BEGIN{prev=0; print "pass  end (IST)     minutes  violations"} {d=(prev?($2-prev)/60:0); printf "%4d  %s %s  %5.0f  %s\n", $1, $3, $4, d, $5; prev=$2}'
