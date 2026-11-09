#!/usr/bin/env bash
# Equivalence check of the rewritten double-pumped RAM wrappers against the
# legacy (latch + clock-as-data) versions. Requires GHDL (>= 1.0).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
WD=${WORKDIR:-$ROOT/HW/asic/build/tb_ramw}
rm -rf "$WD"; mkdir -p "$WD"
A="ghdl -a --std=08 --workdir=$WD -frelaxed -Wno-hide"
$A "$ROOT/HW/src/config.vhd"
$A "$ROOT/HW/src/ztachip_pkg.vhd"
$A "$ROOT/HW/platform/asic/DPRAM.vhd"
$A "$ROOT/HW/platform/asic/DPRAM_BE.vhd"
$A "$ROOT/HW/platform/simulation/SYNC_LATCH.vhd"   # only the legacy copies use it
$A "$ROOT/HW/src/util/x2_phase.vhd"
$A "$ROOT/HW/src/util/ramw.vhd"
$A "$ROOT/HW/src/util/ramw2.vhd"
$A "$ROOT/HW/src/util/ram2r1w.vhd"
$A "$ROOT/HW/asic/tb/legacy/ramw_legacy.vhd"
$A "$ROOT/HW/asic/tb/legacy/ramw2_legacy.vhd"
$A "$ROOT/HW/asic/tb/legacy/ram2r1w_legacy.vhd"
$A "$ROOT/HW/asic/tb/tb_ramw_equiv.vhd"
ghdl -e --std=08 --workdir="$WD" -frelaxed tb_ramw_equiv
ghdl -r --std=08 --workdir="$WD" tb_ramw_equiv --assert-level=failure 2>&1 | tee "$WD/run.log"
grep -q "RAMW EQUIV TB: PASS" "$WD/run.log"
