#!/bin/bash
# Pads into the routed core mid-DRT: core DRT snapshot -> chip ODB with pad ring + straps -> GRT of the pad nets
# -> <out>/chip_grt.odb ready for drt_steps.tcl (STEP_START=0 + STEP_SNAPSHOT_DIR). The detailed route then also
# repairs core wires that spilled into the pad-ring margin (pads are now obstacles) and routes the pad nets.
# usage: chip_drt_prep.sh <core_snapshot.odb> <out_dir> [threads=8]
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUT=$(readlink -m "$2")
T=${3:-8}
PDN=$HERE/../dgse/runs/cmos5l-01/pdn_c5l_sram_v2.tcl
bash "$HERE/run_chip_integrate.sh" "$1" "$HERE/work/padring" "$OUT" "$PDN" "$T" pdn || exit 1
. "$HERE/env.sh"
OR=${DGSE_OPENROAD_NIX:-openroad}
GIN=$OUT/chip_pdn.odb
if [ "${STRIP_MARGIN:-0}" = 1 ]; then
  python3 "$HERE/def_margin_nets.py" "$OUT/chip_pdn.def" "$OUT/margin_nets.txt" || exit 1
  IN_ODB=$OUT/chip_pdn.odb OUT_ODB=$OUT/chip_strip.odb NETS_TXT=$OUT/margin_nets.txt \
    "$OR" -no_init -no_splash -exit "$HERE/chip_strip_margin.tcl" > "$OUT/3b_strip.log" 2>&1 \
    || { echo "strip failed"; tail -20 "$OUT/3b_strip.log"; exit 1; }
  grep -a CHIP_STRIP "$OUT/3b_strip.log"
  GIN=$OUT/chip_strip.odb
fi
IN_ODB=$GIN OUT_ODB=$OUT/chip_grt.odb BPINS_TCL=$OUT/bpins.tcl GUIDE=$OUT/route.guide THREADS=$T \
  "$OR" -no_init -no_splash -exit "$HERE/chip_grt.tcl" > "$OUT/4_grt.log" 2>&1 || { echo "chip_grt failed"; tail -20 "$OUT/4_grt.log"; exit 1; }
grep -a -E "CHIP_GRT|GRT-0096|Total|GRT-0303" "$OUT/4_grt.log" | tail -12
