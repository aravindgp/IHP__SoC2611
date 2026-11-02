#!/bin/bash
# drc_tables.sh <gds> <top> <out_dir> [parallel=3] [mem_gb=40] [cpus_per_job=4]
# Full-chip DRC as one capped job per rule table (drc_capped.sh), `parallel` at a time on disjoint cpus,
# in the order metal/via -> front-end -> latch-up/forbidden/pin. One KLayout process with every table
# sat 5.5 h in "connectivity setup" on the chip (2 Nov); per table, a stuck or runaway table costs only
# itself. Results: <out_dir>/<table>/ (lyrdb + logs), summary: <out_dir>/summary.txt.
GDS=$1; TOP=$2; OUT=$3; P=${4:-3}; MEM=${5:-40}; NC=${6:-4}
HERE=$(cd "$(dirname "$0")" && pwd)
BEOL="metal1 metaln via1 vian topvia1 topmetal1 passiv pad sealring metalslits lbe metalnfiller topmetal1filler"
FEOL="nwell pwellblock activ gatpoly cont contbar psd thickgateox nbulay activfiller gatpolyfiller"
LAST="latchup forbidden pin"
mkdir -p "$OUT"
run_one() {  # $1 = slot, $2 = table
  local slot=$1 t=$2
  echo "[drc_tables] $(TZ=Asia/Kolkata date +%H:%M) start $t (slot $slot)"
  CPU_OFF=$((slot * NC)) bash "$HERE/drc_capped.sh" "$GDS" "$TOP" "$OUT/$t" "$MEM" "$NC" \
      --no-antenna --no-density -- --table="$t" > "$OUT/$t.log" 2>&1
  echo "[drc_tables] $(TZ=Asia/Kolkata date +%H:%M) done  $t rc=$? $(grep -h -E '^TOTAL' "$OUT/$t"/summary.txt 2>/dev/null)"
}
export -f run_one; export HERE GDS TOP OUT MEM NC
i=0
for t in $BEOL $FEOL $LAST; do echo "$((i % P)) $t"; i=$((i + 1)); done \
  | xargs -P "$P" -L 1 bash -c 'run_one "$0" "$1"'
grep -h -E "^TOTAL|unwaived" "$OUT"/*/summary.txt 2>/dev/null | sed 's/^/  /' > "$OUT/summary.txt"
echo "[drc_tables] all tables done; per-table totals in $OUT/summary.txt"
