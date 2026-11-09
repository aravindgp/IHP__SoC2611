#!/usr/bin/env bash
# One-shot physical signoff of a routed SoC2611 chip GDS on IHP SG13CMOS5L.
#
# usage: run_signoff.sh <chip.gds> <topcell> <chip.cdl> [-o DIR] [--die 6600] [--has-sealring]
#                       [--no-fill] [--no-topup] [--pdk-density] [-j N] [--srams] [--blackbox PAT]...
#   --srams: LVS view also reduces the RM_IHPSG13 SRAM macros to metal (recommended for the chip)
#   1. seal ring  : make_sealring.py --input (skipped with --has-sealring, e.g. GDS from make_padring)
#   2. fill       : fill_tiled.py (PDK Activ/GatPoly + Metal1-4/TopMetal1 fill recipes, 1 mm tiles;
#                   with --srams the RM_IHPSG13 macros are abstracted to outlines)
#                   + fill_topup.py (fills what the PDK lattice left between routes/cells; --no-topup skips)
#   3. density    : density_fast.py (= density.drc numbers in minutes; DIR/density.json)
#   4. DRC        : run_drc.sh full (main tables + antenna), waivers/drc_waivers.txt; the PDK density
#                   deck (16 h on the full chip) only with --pdk-density
#   5. LVS        : make_lvs_view.py (IO cells -> metal only) + run_lvs.sh --deep vs chip.cdl (make_chip_cdl.sh)
# Writes DIR/<top>_final.gds (the GDS to submit) and DIR/{drc,lvs}/.
# Check memory first: full-chip DRC in deep mode needs several GB per process.
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$HERE/env.sh"
[ $# -ge 3 ] || { sed -n 2,13p "$0"; exit 2; }
GDS=$(readlink -f "$1"); TOP=$2; CDL=$(readlink -f "$3"); shift 3
OUT=./signoff_$TOP; DIE=6600; SEAL=1; FILL=1; MP=4; BB=(); SRAMS=0; TOPUP=1; PDKDENS=0
while [ $# -gt 0 ]; do
  case $1 in
    -o) OUT=$2; shift ;;
    --die) DIE=$2; shift ;;
    --has-sealring) SEAL=0 ;;
    --no-fill) FILL=0 ;;
    --no-topup) TOPUP=0 ;;
    --pdk-density) PDKDENS=1 ;;
    -j) MP=$2; shift ;;
    --blackbox) BB+=(--blackbox "$2"); shift ;;
    --srams) SRAMS=1 ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
  shift
done
mkdir -p "$OUT"; OUT=$(readlink -f "$OUT")
CUR=$GDS
if [ $SEAL = 1 ]; then
  python3 "$HERE/make_sealring.py" --input "$CUR" --top "$TOP" --width "$DIE" --height "$DIE" \
    -o "$OUT/${TOP}_sealring.gds" || exit 2
  CUR=$OUT/${TOP}_sealring.gds
fi
if [ $FILL = 1 ]; then
  ABS=(); [ $SRAMS = 1 ] && ABS=(--abstract-macros 'RM_IHPSG13_.*')
  if [ $TOPUP = 1 ]; then
    python3 "$HERE/fill_tiled.py" "$CUR" "$OUT/${TOP}_pdkfill.gds" --top "$TOP" --tile 1000 -j "${FILL_J:-2}" "${ABS[@]}" || exit 2
    python3 "$HERE/fill_topup.py" "$OUT/${TOP}_pdkfill.gds" "$OUT/${TOP}_final.gds" --top "$TOP" -j "${TOPUP_J:-12}" || exit 2
  else
    python3 "$HERE/fill_tiled.py" "$CUR" "$OUT/${TOP}_final.gds" --top "$TOP" --tile 1000 -j "${FILL_J:-2}" "${ABS[@]}" || exit 2
  fi
else
  cp "$CUR" "$OUT/${TOP}_final.gds"
fi
python3 "$HERE/density_fast.py" "$OUT/${TOP}_final.gds" --top "$TOP" -j "${DENS_J:-12}" --attrib \
  --json "$OUT/density.json" | tee "$OUT/density.txt"; DENS=${PIPESTATUS[0]}
DOPT=(--no-density); [ $PDKDENS = 1 ] && DOPT=()
bash "$HERE/run_drc.sh" "$OUT/${TOP}_final.gds" "$TOP" -o "$OUT/drc" -j "$MP" "${DOPT[@]}"; DRC=$?
# LVS on the LVS view: IO cells reduced to metal, IO subckts emptied (the open deck does not match
# IHP's IO cells even standalone -- see make_lvs_view.py).  Fill stays in (floating, harmless).
LIBS=("$PDK_ROOT/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/gds/sg13cmos5l_io.gds")
[ $SRAMS = 1 ] && LIBS+=("$PDK_ROOT"/ihp-sg13cmos5l/libs.ref/sg13cmos5l_sram/gds/RM_IHPSG13_*.gds)
python3 "$HERE/make_lvs_view.py" "$OUT/${TOP}_final.gds" "$OUT/${TOP}_lvsview.gds" "$CDL" "$OUT/${TOP}_lvsview.cdl" "${LIBS[@]}" || exit 2
bash "$HERE/run_lvs.sh" "$OUT/${TOP}_lvsview.gds" "$TOP" "$OUT/${TOP}_lvsview.cdl" -o "$OUT/lvs" --deep "${BB[@]}"; LVS=$?
echo "[signoff] density rc=$DENS (0 = all density rules pass)  DRC rc=$DRC (0 = clean after waivers)  LVS rc=$LVS (0 = match)  final GDS: $OUT/${TOP}_final.gds"
[ $DENS = 0 ] && [ $DRC = 0 ] && [ $LVS = 0 ]
