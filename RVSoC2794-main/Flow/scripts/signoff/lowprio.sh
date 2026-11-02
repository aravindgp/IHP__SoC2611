#!/bin/bash
# lowprio.sh <cmd...>: run a side job next to a DGSE DRT with OOM priority 1000 (the kernel kills it, and its
# children, before the router) and nice 10.
echo 1000 > /proc/self/oom_score_adj
exec nice -n 10 "$@"
