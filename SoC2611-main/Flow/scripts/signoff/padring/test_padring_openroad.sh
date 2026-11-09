#!/usr/bin/env bash
# Cross-check the generated pad ring: OpenROAD places it from padring.tcl, result compared with padring.gds.
# usage: test_padring_openroad.sh [padring_dir]   (default ../work/padring)
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$HERE/../env.sh"
export PADRING_DIR=$(readlink -f "${1:-$HERE/../work/padring}")
OR=${DGSE_OPENROAD_NIX:-openroad}
"$OR" -no_init -no_splash -exit "$HERE/test_padring_openroad.tcl" > "$PADRING_DIR/openroad_padring.log" 2>&1
grep -q PADRING_OPENROAD_OK "$PADRING_DIR/openroad_padring.log" || { echo "OpenROAD failed:"; grep -E "ERROR|Error" "$PADRING_DIR/openroad_padring.log" | head; tail -5 "$PADRING_DIR/openroad_padring.log"; exit 2; }
python3 "$HERE/compare_padring.py" "$PADRING_DIR/padring_openroad.def" "$PADRING_DIR/padring.gds"
