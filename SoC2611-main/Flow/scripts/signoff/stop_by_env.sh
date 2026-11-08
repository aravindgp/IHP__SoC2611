#!/bin/bash
# Stop the openroad processes whose environment contains the given substring (e.g. an ECO output directory).
# usage: stop_by_env.sh <substring>
for p in $(pgrep -f "bin/openroad"); do
  if grep -a -q "$1" "/proc/$p/environ" 2>/dev/null; then kill "$p" && echo "STOP_BY_ENV stopped pid $p ($1) $(date -u +%T)"; fi
done
