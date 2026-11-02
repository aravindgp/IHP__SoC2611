#!/usr/bin/env bash
# Run an OpenROAD Tcl script in the signoff environment:  run_tcl.sh <script.tcl> <log> [VAR=value ...]
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$HERE/env.sh"
S=$1; LOG=$2; shift 2
env "$@" ${DGSE_OPENROAD_NIX:-openroad} -no_init -no_splash -exit "$S" > "$LOG" 2>&1
rc=$?
grep -E "HOLD|SLACK|ECO_|^\[ERROR|Error" "$LOG" | head -30
exit $rc
