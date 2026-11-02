#!/usr/bin/env bash
# DEF -> GDS for the integrated chip (KLayout, DGSE def2stream fork), IHP SG13CMOS5L layer map.
#
# usage: stream_chip.sh <chip.def> <topcell> <out.gds> [padring_dir]
#   LEF: sg13cmos5l tech + stdcell + IO + all RM_IHPSG13 SRAMs + <padring_dir>/bondpad_70x70.lef
#   GDS: stdcell + IO + all SRAMs + <padring_dir>/bondpad_70x70.gds (only cells used by the DEF are kept)
#   padring_dir defaults to work/padring (make_padring.py output).
# Extra LEF/GDS: EXTRA_LEF / EXTRA_GDS env (space separated).
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$HERE/env.sh"
[ $# -ge 3 ] || { sed -n 2,9p "$0"; exit 2; }
DEF=$(readlink -f "$1"); TOP=$2; OUT=$(readlink -m "$3"); PRD=$(readlink -f "${4:-$HERE/work/padring}")
R=$PDK_ROOT/ihp-sg13cmos5l/libs.ref
LEFS="$R/sg13cmos5l_stdcell/lef/sg13cmos5l_tech.lef $R/sg13cmos5l_stdcell/lef/sg13cmos5l_stdcell.lef $R/sg13cmos5l_io/lef/sg13cmos5l_io.lef $PRD/bondpad_70x70.lef"
LEFS="$LEFS $(ls $R/sg13cmos5l_sram/lef/RM_IHPSG13_*.lef | tr '\n' ' ') ${EXTRA_LEF:-}"
GDSS="$R/sg13cmos5l_stdcell/gds/sg13cmos5l_stdcell.gds $R/sg13cmos5l_io/gds/sg13cmos5l_io.gds $PRD/bondpad_70x70.gds"
GDSS="$GDSS $(ls $R/sg13cmos5l_sram/gds/RM_IHPSG13_*.gds | tr '\n' ' ') ${EXTRA_GDS:-}"
mkdir -p "$(dirname "$OUT")"
LYT=$(dirname "$OUT")/sg13cmos5l_stream.lyt
python3 - "$KLAYOUT_TECH/sg13cmos5l.lyt" "$LYT" $LEFS <<'EOF'
import re, sys
src, dst, lefs = sys.argv[1], sys.argv[2], sys.argv[3:]
t = re.sub(r"<lef-files>.*?</lef-files>|<lef-files/>", "", open(src).read(), flags=re.S)
t = t.replace("</lefdef>", "".join(f"<lef-files>{l}</lef-files>" for l in lefs) + "</lefdef>", 1)
open(dst, "w").write(t)
EOF
cp "$KLAYOUT_TECH/sg13cmos5l.map" "$(dirname "$OUT")/sg13cmos5l.map"
echo "[stream_chip] $(date '+%F %T') $DEF -> $OUT"
T0=$SECONDS
rm -f "$OUT"
klayout -zz -rd design_name="$TOP" -rd in_def="$DEF" -rd in_files="$GDSS" -rd config_file= -rd seal_file= \
  -rd out_file="$OUT" -rd tech_file="$LYT" -rd layer_map="$KLAYOUT_TECH/sg13cmos5l.map" \
  -rm "$DGSE_ROOT/engine/flow/def2stream_dgse.py" > "$OUT.log" 2>&1
RC=$?
[ -s "$OUT" ] || RC=2
grep -E "ERROR|All LEF cells|No orphan" "$OUT.log" | head -20
echo "[stream_chip] rc=$RC in $((SECONDS-T0)) s, log $OUT.log"
exit $RC
