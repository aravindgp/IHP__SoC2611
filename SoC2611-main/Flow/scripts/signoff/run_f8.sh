#!/bin/bash
# Run F v8: on a run-F7 DRT snapshot, rip the nets that still carry DRT markers (from a check_drc report), run GRT
# WITHOUT the IO-band obstructions (they underflow GRT's capacity and attract routes into the band), clamp the few
# band guide boxes inside, re-add the obstructions for DRT, load the guides (no widening: DRT keeps GRT's corridors)
# and start DRT.  usage: run_f8.sh <snapshot.odb> <drc.rpt> <out_dir> [threads=30]
set -u
SNAP=$1; RPT=$2; OUT=$3; T=${4:-30}
HERE=$(cd "$(dirname "$0")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
PADS=/workspace/chip_drt/runD/padnets.txt
mkdir -p "$OUT/drt_snap"
cd "$OUT" || exit 1
echo "RUN_F8 start $(date +%T)"
python3 - "$RPT" "$OUT/marker_nets.txt" <<'EOF'
import re, sys
pat = re.compile(r"net:(\S+)")
nets = set()
for b in open(sys.argv[1], errors='replace').read().split("violation type:")[1:]:
    for n in pat.findall(b):
        if n not in ('VDD', 'VSS', 'IOVDD', 'IOVSS'):
            nets.add(n)
open(sys.argv[2], 'w').write('\n'.join(sorted(nets)) + '\n')
print(f"MARKER_NETS {len(nets)}")
EOF
IN_ODB=$SNAP OUT_ODB=$OUT/chip_noobs.odb "$OR" -exit -no_init "$HERE/chip_rm_obs.tcl" > 1_rmobs.log 2>&1 || { echo "rm_obs failed"; exit 1; }
grep -a CHIP_RM_OBS 1_rmobs.log
IN_ODB=$OUT/chip_noobs.odb OUT_ODB=$OUT/chip_ripped.odb NETS_TXT=$OUT/marker_nets.txt \
  "$OR" -exit -no_init "$HERE/chip_strip_margin.tcl" > 2_rip.log 2>&1 || { echo "rip failed"; exit 1; }
grep -a -i "strip\|destroy" 2_rip.log | tail -1
LAYER_ADJUST="TopMetal1 0.0" CONG_ITERS=10 IN_ODB=$OUT/chip_ripped.odb OUT_ODB=$OUT/chip_grt.odb \
  BPINS_TCL=$OUT/bpins_unused.tcl GUIDE=$OUT/route.guide THREADS=8 \
  "$OR" -exit -no_init "$HERE/chip_grt.tcl" > 3_grt.log 2>&1 || { echo "grt failed"; tail -5 3_grt.log; exit 1; }
grep -a -E "GRT-0303|CHIP_GRT done" 3_grt.log
grep -a -A7 "GRT-0096" 3_grt.log | grep -a -E "^Metal|^TopMetal"
python3 "$HERE/guide_band_nets.py" route.guide "$PADS" | tee 4_before.log
python3 "$HERE/guide_clamp.py" route.guide route_clamped.guide "$PADS" || exit 1
python3 "$HERE/guide_band_nets.py" route_clamped.guide "$PADS" | tee 4_gate.log
non=$(grep -a -o "[0-9]* NON-pad nets" 4_gate.log | grep -a -o "^[0-9]*")
if [ "${non:-9999}" -gt 0 ]; then echo "RUN_F8 GATE G1 FAILED ($non non-pad nets in band)"; exit 2; fi
echo "RUN_F8 GATE G1 PASSED"
IN_ODB=$OUT/chip_grt.odb OUT_ODB=$OUT/chip_obs.odb OBS_LAYERS="Metal1 Metal2 Metal3 Metal4 TopMetal1" \
  "$OR" -exit -no_init "$HERE/chip_io_obs.tcl" > 5_obs.log 2>&1 || { echo "obs failed"; exit 1; }
grep -a CHIP_IO_OBS 5_obs.log
IN_ODB=$OUT/chip_obs.odb OUT_ODB=$OUT/chip_guided.odb GUIDE=$OUT/route_clamped.guide \
  "$OR" -exit -no_init "$HERE/chip_load_guides.tcl" > 6_guides.log 2>&1 || { echo "load guides failed"; exit 1; }
grep -a CHIP_LOAD_GUIDES 6_guides.log
echo "RUN_F8 DRT start $(date +%T) threads $T"
STEP_IN=$OUT/chip_guided.odb STEP_OUT=$OUT/chip_droute.odb STEP_START=0 STEP_END=64 STEP_THREADS=$T \
  STEP_SNAPSHOT_DIR=$OUT/drt_snap STEP_DRC_RPT=$OUT/chip_route_drc.rpt \
  "$OR" -exit -no_init "$HERE/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" > drt_chip.log 2>&1
echo "RUN_F8 DRT exited rc=$? $(date +%T)"
