#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Run the self-checking GHDL testbench for the ASIC platform FP32_MUL /
# FP32_ADDSUB (HW/platform/asic) and prove both are synthesizable and
# latch-free with ghdl --synth.
#
# Usage:  HW/asic/scripts/run_tb_fp32.sh [WORK_DIR]
#         WORK_DIR defaults to $WORK_DIR or /tmp/fp32_tb_work
#         GHDL defaults to $GHDL or ghdl
# Exit status is non-zero on any analysis/elaboration/simulation failure,
# on any vector mismatch, or if synthesis fails or infers a latch.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HW_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORK_DIR="${1:-${WORK_DIR:-/tmp/fp32_tb_work}}"
GHDL="${GHDL:-ghdl}"
STD="--std=08"
VECTORS="$HW_DIR/asic/tb/vectors/fp32_vectors.txt"

mkdir -p "$WORK_DIR"
GA=("$GHDL" -a $STD --workdir="$WORK_DIR")

if [ ! -s "$VECTORS" ]; then
   echo "== generating vectors"
   python3 "$HW_DIR/asic/tb/gen_fp32_vectors.py" "$VECTORS"
fi

echo "== analyze"
"${GA[@]}" "$HW_DIR/src/config.vhd"
"${GA[@]}" "$HW_DIR/src/ztachip_pkg.vhd"
"${GA[@]}" "$HW_DIR/src/util/delayv.vhd"
"${GA[@]}" "$HW_DIR/platform/asic/FP32_MUL.vhd"
"${GA[@]}" "$HW_DIR/platform/asic/FP32_ADDSUB.vhd"
"${GA[@]}" "$HW_DIR/asic/tb/tb_fp32.vhd"

echo "== elaborate + run tb_fp32"
"$GHDL" -e $STD --workdir="$WORK_DIR" tb_fp32
# -gVECTORS: absolute path so the run does not depend on the cwd
"$GHDL" -r $STD --workdir="$WORK_DIR" tb_fp32 \
   -gVECTORS="$VECTORS" --assert-level=failure 2>&1 | tee "$WORK_DIR/tb_fp32.log"
RUN_RC=${PIPESTATUS[0]}
if [ "$RUN_RC" -ne 0 ]; then
   echo "FAIL: simulation exited with status $RUN_RC"
   exit 1
fi
if ! grep -q "FP32 TB: .* passed" "$WORK_DIR/tb_fp32.log"; then
   echo "FAIL: no summary line found"
   exit 1
fi
if grep -Eq "MISMATCH|mismatch|severity failure|\(error\)|\(failure\)" "$WORK_DIR/tb_fp32.log"; then
   echo "FAIL: mismatches reported"
   exit 1
fi

echo "== synthesis check (ghdl --synth, LATENCY=4)"
SYNTH_FAIL=0
for unit in FP32_MUL FP32_ADDSUB; do
   out="$WORK_DIR/synth_${unit}.vhd"
   log="$WORK_DIR/synth_${unit}.log"
   if ! "$GHDL" --synth $STD --workdir="$WORK_DIR" -gLATENCY=4 "$unit" > "$out" 2> "$log"; then
      echo "FAIL: ghdl --synth $unit failed:"
      cat "$log"
      SYNTH_FAIL=1
      continue
   fi
   if grep -qi "latch" "$log" "$out"; then
      echo "FAIL: latch inferred in $unit:"
      grep -i "latch" "$log" "$out"
      SYNTH_FAIL=1
      continue
   fi
   if grep -qi "warning\|error" "$log"; then
      echo "WARN: synthesis messages for $unit:"
      cat "$log"
   fi
   echo "synth $unit: OK ($(grep -c "" "$out") lines of netlist, no latches)"
done
[ "$SYNTH_FAIL" -eq 0 ] || exit 1

echo "== ALL PASSED"
