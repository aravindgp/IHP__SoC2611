#!/bin/bash
# drc_capped.sh <gds> <top> <out_dir> [mem_gb=40] [cpus=6] [run_drc.sh options...]
# Run run_drc.sh next to a DGSE DRT without endangering it: one table process at a time (-j 1),
# virtual memory capped (a runaway table dies with bad_alloc instead of growing to 77 GB, measured
# CPU_OFF=k (env) pins to the NC cpus ending k before the last one, so parallel jobs do not share cpus.
# 2 Nov on the pwellblock table of the full chip), OOM priority 1000, nice 10, pinned to `cpus`
# CPUs of the container's cpuset, and --density_thr=<cpus>: the PDK run_drc.py uses density_thr as the
# thread count of EVERY deck (default os.cpu_count() = 256 host cores); 256 threads reserved >40 GB of
# virtual memory at 4.7 GB RSS and the capped run blocked at the cap (2 Nov 01:05-02:20).
GDS=$1; TOP=$2; OUT=$3; MEM=${4:-40}; NC=${5:-6}; shift 5 2>/dev/null || shift $#
HERE=$(cd "$(dirname "$0")" && pwd)
CPUS=$(python3 -c "
import sys
s = open('/sys/fs/cgroup/cpuset/cpuset.cpus').read().strip()
c = []
for p in s.split(','):
    a, _, b = p.partition('-'); c += range(int(a), int(b or a) + 1)
off = int('${CPU_OFF:-0}'); print(','.join(map(str, c[len(c) - off - $NC:len(c) - off])))")
ulimit -v $((MEM * 1024 * 1024))
echo "[drc_capped] mem cap ${MEM} GB, cpus ${CPUS}, -j 1: $GDS"
case " $* " in *" -- "*) TAIL=(--density_thr="$NC") ;; *) TAIL=(-- --density_thr="$NC") ;; esac
case " $* " in *density_thr*) TAIL=() ;; esac
exec bash "$HERE/lowprio.sh" taskset -c "$CPUS" bash "$HERE/run_drc.sh" "$GDS" "$TOP" -o "$OUT" -j 1 "$@" "${TAIL[@]}"
