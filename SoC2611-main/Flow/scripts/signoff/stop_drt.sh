#!/bin/bash
# Stop the running DRT whose environment names <tag>/drt_snap (never pkill -f: the pattern would match our own shells).
# usage: stop_drt.sh <tag>   e.g. stop_drt.sh drtH4
set -u
for p in $(pgrep -f "bin/openroad"); do
  if grep -a -q "$1/drt_snap" "/proc/$p/environ" 2>/dev/null; then kill "$p" && echo "STOP_DRT stopped $1 pid $p $(date -u +%T)"; fi
done
