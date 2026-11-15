#!/usr/bin/env bash
# Simulation of the routed netlist of the chip, pad to pad, with the test firmware (13 November 2026).
# Steps: firmware image (fw/<fw>.c) built and written as a memory file for the HyperRAM model; the released
# netlist unpacked to the work folder and copied without row fillers and antenna diodes; cell models written from the
# timing library; everything compiled with Verilator; run.
# The simulation has no gate or wire delays: it proves the logic of the netlist that is in the GDS (every buffer,
# diode pass and clock change since synthesis included), the reset, the clock generator, the boot path and the
# pads. Timing is the job of the static timing analysis on the routed wires.
# usage: run_gl.sh <released netlist SoC2611.v.gz> <tag> [fw=quick] [build|run|all=all] [simulator +args]
#   firmware: quick (six checks, 12 characters of output), smoke (the same with full text, about 340 characters),
#             capture (camera frame to memory; give +cam=1000 +expect=1)
#   simulator +args: +expect=<n> +cam=<frames> +timeout_ms=<ms>   (the firmware image is passed as +mem=)
#   env: OSS_CAD_SUITE (folder with bin/verilator), RISCV_PREFIX (e.g. riscv-none-elf-), PDK_ROOT (folder with
#        ihp-sg13cmos5l/libs.ref), WORK (work folder, default ./work/<tag>); give folders as absolute paths;
#        XINIT=0 (all registers start at 0) | unique (random start values, seed SEED); JOBS (compile jobs, 16);
#        FW_CFLAGS, GPARAMS (verilator -G parameters)
# One compiled simulator serves every firmware: after the first 'all', use 'run'.
set -u
NET=$(realpath -m "$1"); TAG=$2; FW=${3:-quick}; WHAT=${4:-all}
G=$(cd "$(dirname "$0")" && pwd)
FWDIR=$G/fw
W=$(realpath -m "${WORK:-./work/$TAG}")
OSS=${OSS_CAD_SUITE:?set OSS_CAD_SUITE to the oss-cad-suite folder (with bin/verilator)}
RV=${RISCV_PREFIX:?set RISCV_PREFIX to the RISC-V GCC prefix, e.g. riscv-none-elf- or /opt/riscv/bin/riscv-none-elf-}
PDK=${PDK_ROOT:?set PDK_ROOT to the folder that contains ihp-sg13cmos5l/libs.ref}/ihp-sg13cmos5l/libs.ref
XINIT=${XINIT:-0}; SEED=${SEED:-1}; JOBS=${JOBS:-16}
log() { echo "[gl $(date -u +%H:%M:%S)] $*"; }
mkdir -p $W/fw
cd $W || exit 1
[ -s $NET ] || { log "no $NET"; exit 1; }

# 1. firmware
if [ "$FW" = capture ]; then
  FW_CFLAGS="${FW_CFLAGS:-} -DCAM_EXPECT=$(python3 -I $G/cam_expect.py | cut -d' ' -f1)u"
fi
${RV}gcc -march=rv32im -mabi=ilp32 -O2 -ffreestanding -nostdlib -nostartfiles -fno-builtin -Wall -Wextra \
   -DDP_FIFO_MAX=63 ${FW_CFLAGS:-} -T $FWDIR/link.ld -o $W/fw/$FW.elf $FWDIR/start.S $FWDIR/$FW.c -lgcc || { log "firmware build failed"; exit 1; }
${RV}objcopy -O ihex $W/fw/$FW.elf $W/fw/$FW.hex
${RV}objdump -d $W/fw/$FW.elf > $W/fw/$FW.lst
python3 -I $G/ihex2mem.py $W/fw/$FW.hex $W/fw/$FW.mem

if [ "$WHAT" != run ]; then
  # 2. netlist without cells that have no logic, and the cell models
  if [ ! -s $W/chip_logic.v ] || [ $NET -nt $W/chip_logic.v ]; then
    gunzip -c $NET > $W/SoC2611.v || exit 1
    python3 -I $G/strip_netlist.py --split-pads $W/SoC2611.v $W/chip_logic.v
  fi
  # every input pin must have a driver: an open input is a defect of the chip, not of the simulation
  python3 -I $G/netlist_floating.py $W/chip_logic.v $PDK/sg13cmos5l_stdcell/lib/sg13cmos5l_stdcell_typ_1p20V_25C.lib > $W/floating.txt 2>&1
  grep -a "^# input pins of standard cells without\|^# nets that are read" $W/floating.txt
  # standard cells written out as logic (the simulator cannot resolve 347,000 cell instances in useful time)
  python3 -I $G/flatten_netlist.py $W/chip_logic.v $PDK/sg13cmos5l_stdcell/lib/sg13cmos5l_stdcell_typ_1p20V_25C.lib $W/chip_flat.v || exit 1
  # 3. compile
  log "verilator: start (registers start at: $XINIT)"
  export PATH=$OSS/bin:$PATH
  t0=$SECONDS
  $OSS/bin/verilator --binary --timing -j $JOBS --build-jobs $JOBS --top-module tb_chip_gl \
     -O2 --x-assign 0 --x-initial $XINIT --no-assert -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
     +define+FUNCTIONAL --output-split 30000 -CFLAGS "-O1" ${GPARAMS:-} \
     --Mdir $W/obj_$XINIT -o sim_gl \
     $G/tb_chip_gl.sv $G/hyperram_model.v $G/pads_split.v \
     $PDK/sg13cmos5l_sram/verilog/RM_IHPSG13_*.v $W/chip_flat.v > $W/verilator_$XINIT.log 2>&1
  rc=$?
  log "verilator: exit $rc after $((SECONDS - t0)) s"
  grep -a "%Error" $W/verilator_$XINIT.log | head -12 | cut -c1-220
  [ -x $W/obj_$XINIT/sim_gl ] || { log "no simulator binary"; tail -5 $W/verilator_$XINIT.log | cut -c1-220; exit 1; }
fi
if [ "$WHAT" != build ]; then
  log "run: firmware $FW, registers start at $XINIT, seed $SEED"
  t0=$SECONDS
  stdbuf -oL $W/obj_$XINIT/sim_gl +mem=$W/fw/$FW.mem +verilator+rand+reset+$([ "$XINIT" = 0 ] && echo 0 || echo 2) +verilator+seed+$SEED "${@:5}" \
     > $W/run_${FW}_${XINIT}_$SEED.log 2>&1
  log "run: exit $? after $((SECONDS - t0)) s"
  grep -a "^UART\|^GLSIM\|HYPERRAM" $W/run_${FW}_${XINIT}_$SEED.log | grep -v "GLSIM [0-9]* ms:" | cut -c1-240
fi
log "all done"
