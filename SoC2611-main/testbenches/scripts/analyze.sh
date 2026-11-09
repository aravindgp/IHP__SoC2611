#!/usr/bin/env bash
# GHDL front-end gate for the SoC2611 RTL.
#
#   HW/asic/scripts/analyze.sh [asic|simulation] [top]
#
# Analyses the whole design (VHDL-2008) in dependency order against the
# chosen platform primitives, then elaborates `top` (default:
# soc2611_asic_top for the asic platform, soc_base otherwise). Fails on
# the first file that does not analyse and on an elaboration error, so it
# doubles as a lint pass for the ASIC hand-off. Set SYNTH=1 to also run
# `ghdl --synth` on the top and write a vendor-free Verilog netlist (slow).
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
PLAT=${1:-asic}
S=$ROOT/HW/src
P=$ROOT/HW/platform/$PLAT
A=$ROOT/HW/asic/rtl
WD=${WORKDIR:-$ROOT/HW/asic/build/analyze_$PLAT}
rm -rf "$WD"; mkdir -p "$WD"

RAMW_OVERRIDE=()
BOOTROM_PKG=$S/soc/boot_rom_pkg.vhd   # empty default ROM; asic/ihp use the generated HW/asic/rtl/boot_rom_pkg.vhd
CPU_CORE=( "$ROOT"/HW/riscv/sim/riscv.vhd )   # FPGA/sim core; asic/ihp: only the regenerated riscv_jtag
JTAG_CORE=()      # asic/ihp: regenerated VexRiscv riscv_jtag + its memory implementation
RISCV_DIR=sim      # simulation/FPGA core (reset vector 0x4000); asic/ihp use HW/riscv/asic (reset vector 0 = TCM boot ROM)
if [ "$PLAT" = asic ]; then
  TOP=${2:-soc2611_asic_top}
  CONFIG=$A/config.vhd
  RISCV_DIR=asic
  BOOTROM_PKG=$A/boot_rom_pkg.vhd
  JTAG_CORE=( "$ROOT"/HW/riscv/asic_jtag/ram_blackboxes_ref.vhd "$ROOT"/HW/riscv/asic_jtag/riscv.vhd ); CPU_CORE=( "${JTAG_CORE[@]}" )
  PLATFILES=( "$P"/CCD_SYNC.vhd "$P"/SLL.vhd "$P"/SLA.vhd "$P"/SRL.vhd "$P"/SRA.vhd
              "$P"/DPRAM.vhd "$P"/DPRAM_BE.vhd "$P"/DPRAM_DUAL_CLOCK.vhd "$P"/SPRAM.vhd "$P"/SPRAM_BE.vhd )
  EXTRA=( "$A"/reset_sync.vhd "$A"/clk_div2.vhd "$A"/clk_gate.vhd "$A"/soc2611_asic_top.vhd "$A"/hyperbus/hyperbus_rx.vhd "$A"/hyperbus/hyperbus_core.vhd "$A"/hyperbus/hyperbus_axi.vhd "$A"/soc2611_chip_top.vhd )
elif [ "$PLAT" = ihp ]; then
  # IHP memory layer: generic primitives from platform/asic, memories from platform/ihp (1P macros time-multiplexed at clk_x2)
  TOP=${2:-soc2611_asic_top}
  CONFIG=$A/config.vhd
  RISCV_DIR=asic
  BOOTROM_PKG=$A/boot_rom_pkg.vhd
  JTAG_CORE=( "$ROOT"/HW/platform/ihp/Ram_1w_1rs.vhd "$ROOT"/HW/riscv/asic_jtag/riscv.vhd ); CPU_CORE=( "${JTAG_CORE[@]}" )
  G=$ROOT/HW/platform/asic
  PLATFILES=( "$G"/CCD_SYNC.vhd "$G"/SLL.vhd "$G"/SLA.vhd "$G"/SRL.vhd "$G"/SRA.vhd
              "$P"/ihp_sram_pkg.vhd "$P"/ihp_sram_models.vhd "$P"/ihp_sram_macro_sel.vhd
              "$P"/ihp_sram_tile_1p.vhd "$P"/ihp_sram_tile_2p.vhd "$S"/util/x2_phase.vhd
              "$P"/DPRAM.vhd "$P"/DPRAM_BE.vhd "$P"/DPRAM_DUAL_CLOCK.vhd "$P"/SPRAM.vhd "$P"/SPRAM_BE.vhd )
  X2_IN_PLAT=1
  EXTRA=( "$A"/reset_sync.vhd "$A"/clk_div2.vhd "$A"/clk_gate.vhd "$A"/soc2611_asic_top.vhd "$A"/hyperbus/hyperbus_rx.vhd "$A"/hyperbus/hyperbus_core.vhd "$A"/hyperbus/hyperbus_axi.vhd "$A"/soc2611_chip_top.vhd )
  RAMW_OVERRIDE=( "$P"/ramw.vhd "$P"/ramw2.vhd )
  P=$G
else
  TOP=${2:-soc_base}
  CONFIG=$S/config.vhd
  PLATFILES=( "$P"/SYNC_LATCH.vhd "$P"/CCD_SYNC.vhd "$P"/SLL.vhd "$P"/SLA.vhd "$P"/SRL.vhd "$P"/SRA.vhd
              "$P"/DPRAM.vhd "$P"/DPRAM_BE.vhd "$P"/DPRAM_DUAL_CLOCK.vhd "$P"/SPRAM.vhd "$P"/SPRAM_BE.vhd )
  EXTRA=( )
fi

# util/x2_phase.vhd must be analysed before the wrappers that instantiate it
# directly (and only once, or GHDL marks those wrappers obsolete)
UTIL=( )
[ "${X2_IN_PLAT:-0}" = 1 ] || UTIL=( "$S"/util/x2_phase.vhd )
for f in "$S"/util/*.vhd; do
  b=$(basename "$f")
  [ "$b" = x2_phase.vhd ] && continue
  if [ ${#RAMW_OVERRIDE[@]} -gt 0 ] && { [ "$b" = ramw.vhd ] || [ "$b" = ramw2.vhd ]; }; then continue; fi
  UTIL+=( "$f" )
done
UTIL+=( "${RAMW_OVERRIDE[@]}" )

FILES=(
  "$CONFIG" "$S"/ztachip_pkg.vhd
  "${PLATFILES[@]}"
  "${UTIL[@]}"
  "$P"/FP32_MUL.vhd "$P"/FP32_ADDSUB.vhd
  "$S"/fpu/*.vhd "$S"/alu/*.vhd "$S"/ialu/*.vhd "$S"/pcore/*.vhd "$S"/dp/*.vhd "$S"/top/*.vhd
  "$S"/soc/axi/*.vhd "$S"/soc/peripherals/*.vhd "$BOOTROM_PKG" "$S"/soc/tcm.vhd
  "${CPU_CORE[@]}"
  "$S"/soc/soc_base.vhd
  "${EXTRA[@]}"
)

ok=0; fail=0
for f in "${FILES[@]}"; do
  if [ ! -f "$f" ]; then echo "MISSING ${f#$ROOT/}"; fail=$((fail+1)); continue; fi
  if out=$(ghdl -a --std=08 --workdir="$WD" -frelaxed -Wno-hide -Wno-shared "$f" 2>&1); then
    ok=$((ok+1))
  else
    fail=$((fail+1)); echo "FAIL ${f#$ROOT/}"; echo "$out" | head -5 | sed 's/^/    /'
  fi
done
echo "analyze: ok=$ok fail=$fail (platform=$PLAT)"
[ $fail -eq 0 ] || exit 1

if ghdl -e --std=08 --workdir="$WD" -frelaxed "$TOP" 2>&1 | tee "$WD/elab.log" | grep -qiE 'error'; then
  echo "elaborate $TOP: FAIL (see $WD/elab.log)"; exit 1
fi
echo "elaborate $TOP: OK"

if [ "${SYNTH:-0}" = 1 ]; then
  echo "synthesizing $TOP with ghdl --synth (this takes a while)..."
  # GHDL 1.0 writes a VHDL netlist (newer GHDL also accepts --out=verilog)
  if ghdl --synth --std=08 --workdir="$WD" -frelaxed "$TOP" > "$WD/$TOP.netlist.vhdl" 2> "$WD/synth.log"; then
    echo "synth: OK -> $WD/$TOP.netlist.vhdl ($(wc -l < "$WD/$TOP.netlist.vhdl") lines)"
    grep -ciE 'latch' "$WD/synth.log" | sed 's/^/synth latch warnings: /'
  else
    echo "synth: FAIL (see $WD/synth.log)"; tail -5 "$WD/synth.log"; exit 1
  fi
fi
