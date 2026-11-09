#!/usr/bin/env bash
# Equivalence check of the IHP SRAM-macro memory wrappers (HW/platform/ihp)
# against the behavioural ASIC wrappers (HW/platform/asic), plus ramw/ramw2/
# ram2r1w on both and DPRAM_DUAL_CLOCK (afifo storage) with two clocks.
# Requires GHDL (>= 1.0). Optional: NCYCLES=<n> (default 20000).
#
#   HW/asic/scripts/run_tb_ihp_mem.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
WD=${WORKDIR:-$ROOT/HW/asic/build/tb_ihp_mem}
GHDL=${GHDL:-ghdl}
NCYCLES=${NCYCLES:-20000}
rm -rf "$WD"; mkdir -p "$WD"
S=$ROOT/HW/src
GOLD="$GHDL -a --std=08 --work=golden --workdir=$WD -frelaxed -Wno-hide -Wno-shared"
IHP="$GHDL -a --std=08 --work=ihp --workdir=$WD -frelaxed -Wno-hide -Wno-shared"
TB="$GHDL -a --std=08 --work=work --workdir=$WD -P$WD -frelaxed -Wno-hide"

# golden: asic flop models + the generic double-pumped wrappers of HW/src/util
$GOLD "$S/config.vhd"
$GOLD "$S/ztachip_pkg.vhd"
$GOLD "$ROOT/HW/platform/asic/DPRAM.vhd"
$GOLD "$ROOT/HW/platform/asic/DPRAM_BE.vhd"
$GOLD "$ROOT/HW/platform/asic/SPRAM.vhd"
$GOLD "$ROOT/HW/platform/asic/SPRAM_BE.vhd"
$GOLD "$ROOT/HW/platform/asic/DPRAM_DUAL_CLOCK.vhd"
$GOLD "$S/util/x2_phase.vhd"
$GOLD "$S/util/ramw.vhd"
$GOLD "$S/util/ramw2.vhd"
$GOLD "$S/util/ram2r1w.vhd"

# ihp: macro models, tilers, wrappers, platform ramw/ramw2 + the generic ram2r1w
$IHP "$S/config.vhd"
$IHP "$S/ztachip_pkg.vhd"
$IHP "$ROOT/HW/platform/ihp/ihp_sram_pkg.vhd"
$IHP "$ROOT/HW/platform/ihp/ihp_sram_models.vhd"
$IHP "$ROOT/HW/platform/ihp/ihp_sram_macro_sel.vhd"
$IHP "$ROOT/HW/platform/ihp/ihp_sram_tile_1p.vhd"
$IHP "$ROOT/HW/platform/ihp/ihp_sram_tile_2p.vhd"
$IHP "$S/util/x2_phase.vhd"
$IHP "$ROOT/HW/platform/ihp/DPRAM.vhd"
$IHP "$ROOT/HW/platform/ihp/DPRAM_BE.vhd"
$IHP "$ROOT/HW/platform/ihp/SPRAM.vhd"
$IHP "$ROOT/HW/platform/ihp/SPRAM_BE.vhd"
$IHP "$ROOT/HW/platform/ihp/DPRAM_DUAL_CLOCK.vhd"
$IHP "$ROOT/HW/platform/ihp/ramw.vhd"
$IHP "$ROOT/HW/platform/ihp/ramw2.vhd"
$IHP "$S/util/ram2r1w.vhd"

$TB "$ROOT/HW/asic/tb/tb_ihp_mem_equiv.vhd"
$GHDL -e --std=08 --workdir="$WD" -P"$WD" -frelaxed tb_ihp_mem_equiv_cfg
$GHDL -r --std=08 --workdir="$WD" -P"$WD" tb_ihp_mem_equiv_cfg -gNCYCLES="$NCYCLES" --assert-level=failure 2>&1 | tee "$WD/run.log" | grep -v 'NUMERIC_STD.TO_INTEGER: metavalue'   # start-up 'U' addresses
grep -q "IHP MEM EQUIV TB: PASS" "$WD/run.log"
echo "PASS lines: $(grep -c '(report note): PASS' "$WD/run.log")"
