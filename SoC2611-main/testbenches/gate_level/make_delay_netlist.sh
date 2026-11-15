#!/usr/bin/env bash
# The netlist with built-in delays of a ROUTED database, for run_delay.sh (13 November 2026):
#   1. Verilog netlist of the database (kept if already there), pads split, cells without logic removed
#   2. delay file (SDF) of the corner from the timing analysis on the extracted wires
#   3. flatten_delay.py: standard cells as logic with the cell and wire delays of the delay file
# Needs the build flow: the routed OpenROAD database (<name>.odb), the parasitics of its routed wires
# (<name>_routed.spef), and the build flow scripts write_v_only.tcl, sta_chip.tcl and sta_write_sdf.tcl. None of
# them is in the public repository, which has the routed netlist only (release/<version>/netlist/SoC2611.v.gz).
# On the released netlist alone, run_gl.sh runs (the simulation without delays); this script does not.
# usage: make_delay_netlist.sh <name> <tag> [corner=typ] [THREADS=4]
#        database $DB_DIR/<name>.odb with $DB_DIR/<name>_routed.spef (spef_sta.sh or thru_sta.sh)
#        result   <WORK>_sdf_<corner>/chip_delay.v
#   env: DB_DIR, FLOW_SCRIPTS (folder with the three build flow scripts), OPENROAD (the openroad binary),
#        SDC (constraints of the chip, e.g. SoC2611-main/constraints/design.sdc), PDK_ROOT (folder with
#        ihp-sg13cmos5l/libs.ref), WORK (work folder, default ./work/<tag>)
N=$1; TAG=$2; C=${3:-typ}; T=${4:-4}
D=${DB_DIR:?set DB_DIR to the build flow folder with <name>.odb and <name>_routed.spef}
W=${WORK:-./work/$TAG}
S=${FLOW_SCRIPTS:?set FLOW_SCRIPTS to the build flow folder with write_v_only.tcl, sta_chip.tcl, sta_write_sdf.tcl}
G=$(cd "$(dirname "$0")" && pwd)
OR=${OPENROAD:?set OPENROAD to the openroad binary}
SDC=${SDC:?set SDC to the constraints of the chip, e.g. SoC2611-main/constraints/design.sdc}
LIB=${PDK_ROOT:?set PDK_ROOT to the folder that contains ihp-sg13cmos5l/libs.ref}/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/lib/sg13cmos5l_stdcell_typ_1p20V_25C.lib
log() { echo "[mkdelay $(date -u +%H:%M:%S)] $*"; }
[ -s $D/$N.odb ] && [ -s $D/${N}_routed.spef ] || { echo "missing $D/$N.odb or its wire file"; exit 1; }
O=${W}_sdf_$C
mkdir -p $W $O
if [ ! -s $W/chip.v ]; then
  IN_ODB=$D/$N.odb OUT_V=$W/chip.v $OR -exit $S/write_v_only.tcl > $W/write_v.log 2>&1
  # the test bench instantiates SoC2611, the top module name of the released netlist; the build flow names it differently
  sed -i -E '0,/^module /s/^module [^ ]+ /module SoC2611 /' $W/chip.v
  log "netlist of $N: $(ls -la $W/chip.v 2>/dev/null | awk '{print $5}') bytes"
fi
[ -s $W/chip.v ] || { echo "no netlist"; exit 1; }
if [ ! -s $W/chip_logic.v ] || [ $W/chip.v -nt $W/chip_logic.v ]; then
  python3 -I $G/strip_netlist.py --split-pads $W/chip.v $W/chip_logic.v || exit 1
fi
IN_ODB=$D/$N.odb SDC=$SDC CORNER=$C THREADS=$T NPATHS=1 RC_MODE=spef SPEF_FILE=$D/${N}_routed.spef \
  SDF_OUT=$O/chip_$C.sdf EXTRA_TCL="$S/sta_write_sdf.tcl" $OR -exit $S/sta_chip.tcl > $O/write_sdf.log 2>&1
grep -a "WRITE_SDF\|STA_SLACK" $O/write_sdf.log | cut -c1-200
[ -s $O/chip_$C.sdf ] || { echo "no delay file"; exit 1; }
python3 -I $G/flatten_delay.py $W/chip_logic.v $LIB $O/chip_$C.sdf $O/chip_delay.v > $O/flatten_delay.log 2>&1 || { tail -3 $O/flatten_delay.log; exit 1; }
tail -1 $O/flatten_delay.log | cut -c1-220
log "done: $O/chip_delay.v"
