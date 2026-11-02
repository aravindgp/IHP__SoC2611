#!/bin/bash
# mem_watch.sh [kill_gb=110] [warn_gb=90]: cgroup memory (RSS) watchdog for side jobs next to a DGSE DRT.
# Prints a line every 5 min; above warn_gb it warns; above kill_gb it kills processes with oom_score_adj 1000
# (started via lowprio.sh), never the router.
K=${1:-110}; W=${2:-90}
f=/sys/fs/cgroup/memory/memory.stat
i=0
while true; do
  rss=$(awk '/^total_rss /{print int($2/1073741824)}' $f)
  if [ "$rss" -ge "$K" ]; then
    for p in $(ls /proc | grep -E '^[0-9]+$'); do
      [ "$(cat /proc/$p/oom_score_adj 2>/dev/null)" = 1000 ] && kill -9 "$p" 2>/dev/null
    done
    echo "MEM_KILL rss=${rss}G >= ${K}G: side jobs killed"
  elif [ "$rss" -ge "$W" ]; then
    echo "MEM_WARN rss=${rss}G"
  elif [ $((i % 5)) = 0 ]; then
    echo "MEM $(TZ=Asia/Kolkata date +%H:%M) rss=${rss}G"
  fi
  i=$((i + 1)); sleep 60
done
