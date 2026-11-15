#!/usr/bin/env bash
# Simulation of the routed netlist WITH its delays (13 November 2026): the netlist written by flatten_delay.py
# (cell and wire delays of one corner built in) in the event simulator Icarus Verilog, pad to pad, with the same
# testbench and firmware images as run_gl.sh. The clock period is chosen on the command line, so the chip can be
# run at its rated speed and, as a control, at a speed the timing analysis says is too fast.
# usage: run_delay.sh <work dir with chip_delay.v> <firmware .mem> <input clock period ns> [build|run|all] [+args]
#   env: RWDS_NS (board delay of the memory strobe, default 0: the chip has its own delay), TAG (name of the run)
#        OSS_CAD_SUITE (folder with bin/iverilog, bin/vvp), PDK_ROOT (folder with ihp-sg13cmos5l/libs.ref); give
#        folders as absolute paths
W=$1; MEM=$(realpath -m "$2"); PER=$3; WHAT=${4:-all}
G=$(cd "$(dirname "$0")" && pwd)
O=${OSS_CAD_SUITE:?set OSS_CAD_SUITE to the oss-cad-suite folder (with bin/iverilog)}/bin
PDK=${PDK_ROOT:?set PDK_ROOT to the folder that contains ihp-sg13cmos5l/libs.ref}/ihp-sg13cmos5l/libs.ref
TAG=${TAG:-p$PER}
log() { echo "[delay $(date -u +%H:%M:%S)] $*"; }
cd $W || exit 1
[ -s chip_delay.v ] || { log "no chip_delay.v in $W"; exit 1; }
if [ "$WHAT" != run ]; then
  t0=$SECONDS
  $O/iverilog -g2012 -DFUNCTIONAL -P tb_chip_gl.CLK_X2_NS=$PER -P tb_chip_gl.RWDS_DELAY=${RWDS_NS:-0.0} \
     -s tb_chip_gl -o chip_$TAG.vvp $G/tb_chip_gl.sv $G/hyperram_model.v \
     $PDK/sg13cmos5l_sram/verilog/RM_IHPSG13_*.v chip_delay.v > build_$TAG.log 2>&1
  log "compile: exit $? after $((SECONDS - t0)) s; $(ls -la chip_$TAG.vvp 2>/dev/null | awk '{print $5}') bytes"
  grep -a -i "error" build_$TAG.log | head -8 | cut -c1-200
  [ -s chip_$TAG.vvp ] || exit 1
fi
if [ "$WHAT" != build ]; then
  t0=$SECONDS
  log "run: image $MEM, input clock $PER ns"
  stdbuf -oL $O/vvp -n chip_$TAG.vvp +mem=$MEM "${@:5}" > run_$TAG.log 2>&1
  log "run: exit $? after $((SECONDS - t0)) s"
  grep -a "^UART\|^GLSIM\|HYPERRAM" run_$TAG.log | grep -v "GLSIM [0-9]* ms:" | cut -c1-220 | tail -16
fi
log "all done"
