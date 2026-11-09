#!/usr/bin/env bash
# Full-chip dress rehearsal of the post-DRT runbook on a partially routed core checkpoint:
# pads + pad power straps (stop before the pad-net route) -> GDS -> CDL -> seal ring, fill, DRC, LVS.
# The ~60 pad nets stay unrouted (LVS opens expected); everything else runs at full-chip size.
# usage: rehearse_chip.sh <core.odb> <out_dir> [threads]
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$HERE/env.sh"
[ $# -ge 2 ] || { sed -n 2,5p "$0"; exit 2; }
CORE=$(readlink -f "$1"); O=$(readlink -m "$2"); TH=${3:-4}
PDN=$HERE/../dgse/runs/cmos5l-01/pdn_c5l_sram_v2.tcl
mkdir -p "$O"
MEMF=/sys/fs/cgroup/memory.current; [ -f $MEMF ] || MEMF=/sys/fs/cgroup/memory/memory.usage_in_bytes   # cgroup v2 / v1
t() { echo "REHEARSAL_STAGE $1 $(TZ=Asia/Kolkata date +%H:%M:%S) mem=$(($(cat $MEMF)/1073741824))G"; }
# MEMORY (32 GB container): run this only with no DGSE DRT running. Full-chip fill needs ~12 GB per
# tile process (not the <3 GB of the 2 mm test), so the fill step must run at -j 2 at most.
t integrate
bash "$HERE/run_chip_integrate.sh" "$CORE" "$HERE/work/padring" "$O" "$PDN" "$TH" pdn || { echo REHEARSAL_FAIL integrate; exit 1; }
t write_v
IN_ODB=$O/chip_pdn.odb OUT_V=$O/chip.v OUT_DEF=$O/chip.def ${DGSE_OPENROAD_NIX:-openroad} -no_init -no_splash -exit \
    "$HERE/write_v.tcl" > "$O/4_writev.log" 2>&1 || { echo REHEARSAL_FAIL write_v; tail "$O/4_writev.log"; exit 1; }
t stream
bash "$HERE/stream_chip.sh" "$O/chip.def" soc2611_chip_top "$O/gds/chip.gds" "$HERE/work/padring" > "$O/5_stream.log" 2>&1 \
    || { echo REHEARSAL_FAIL stream; tail "$O/5_stream.log"; exit 1; }
ls -la "$O/gds"
t cdl
bash "$HERE/make_chip_cdl.sh" "$O/chip.v" "$O/chip.def" soc2611_chip_top "$O/lvs/chip.cdl" > "$O/6_cdl.log" 2>&1 \
    || { echo REHEARSAL_FAIL cdl; tail "$O/6_cdl.log"; exit 1; }
tail -3 "$O/6_cdl.log"
t signoff
bash "$HERE/run_signoff.sh" "$O/gds/chip.gds" soc2611_chip_top "$O/lvs/chip.cdl" -o "$O/signoff" --die 6600 -j 2 --srams > "$O/7_signoff.log" 2>&1
echo "REHEARSAL signoff rc=$?"; tail -25 "$O/7_signoff.log"
t done
