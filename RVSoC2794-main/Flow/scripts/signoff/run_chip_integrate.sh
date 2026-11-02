#!/usr/bin/env bash
# Post-route chip integration (pads + bondpads + pad power straps + pad-net routing) on a routed core ODB.
#
# usage: run_chip_integrate.sh <core.odb> <padring_dir> <out_dir> <pdn.tcl> [threads] [stop_after]
#   padring_dir : make_padring.py --portmap output (padring.tcl, pad_connect.tcl, bondpad_70x70.lef)
#   pdn.tcl     : the PDN script the core was built with (DGSE config pdn_tcl, or the platform pdn.tcl)
#   stop_after  : place | straps | pdn | (empty = all, incl. global + detailed route)
# Steps (logs in out_dir):
#   1. chip_integrate.tcl STOP_AFTER=place  -> chip_placed.odb  (pads, bondpads, netlist re-wired)
#   2. pad_pdn_straps.tcl                    -> straps.tcl (+.def) (pdngen pad->core-ring straps)
#   3. chip_integrate.tcl START_AT=pdn       -> chip.odb/.def/.v (straps merged, GRT + DRT)
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$HERE/env.sh"
[ $# -ge 4 ] || { sed -n 2,12p "$0"; exit 2; }
CORE=$(readlink -f "$1"); export PADRING_DIR=$(readlink -f "$2"); export OUT_DIR=$(readlink -m "$3")
export PDN_TCL=$(readlink -f "$4"); export THREADS=${5:-2}; STOP=${6:-}
mkdir -p "$OUT_DIR"
OR=${DGSE_OPENROAD_NIX:-openroad}
run() { # $1 = log name, rest = env assignments; runs chip_integrate.tcl or a given script
  local log=$1 script=$2; shift 2
  echo "[chip_integrate] $(date '+%T') $script ($*)"
  env "$@" "$OR" -no_init -no_splash -exit "$script" > "$OUT_DIR/$log" 2>&1
  local rc=$?
  grep -E "CHIP_INTEGRATE|PAD_PDN|^ERROR|\[ERROR" "$OUT_DIR/$log" | tail -15
  [ $rc = 0 ] || { echo "[chip_integrate] FAILED rc=$rc, see $OUT_DIR/$log"; exit $rc; }
}
run 1_place.log "$HERE/chip_integrate.tcl" IN_ODB="$CORE" STOP_AFTER=place START_AT=
[ "$STOP" = place ] && exit 0
run 2_straps.log "$HERE/pad_pdn_straps.tcl" IN_ODB="$OUT_DIR/chip_placed.odb" STRAPS_DEF="$OUT_DIR/straps.def" STRAPS_TCL="$OUT_DIR/straps.tcl"
[ "$STOP" = straps ] && exit 0
run 3_route.log "$HERE/chip_integrate.tcl" IN_ODB="$OUT_DIR/chip_placed.odb" START_AT=pdn \
    STRAPS_TCL="$OUT_DIR/straps.tcl" STOP_AFTER="$STOP"
echo "[chip_integrate] done: $OUT_DIR"
