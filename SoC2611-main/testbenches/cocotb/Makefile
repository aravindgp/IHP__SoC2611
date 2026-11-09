# cocotb firmware-level tests for soc2611_asic_top (GHDL, VHDL-2008).
#
#   make                 # build firmware, compile RTL, run all tests
#   make FW=smoke        # choose the firmware image (HW/asic/fw/<FW>.c)
#   make FAST_UART=1     # sim-only config: 10x faster UART (HW/asic/tb/config_sim.vhd)
#   make SIM_BUILD=/tmp/x COCOTB_TESTCASE=test_firmware_suite
#
# Requires: ghdl (>= 1.0 with VPI), cocotb >= 2.0 (`pip install cocotb`),
# riscv64-unknown-elf-gcc (Ubuntu: gcc-riscv64-unknown-elf).
SIM ?= ghdl
TOPLEVEL_LANG ?= vhdl
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../../..)
FW ?= smoke
FWDIR := $(ROOT)/HW/asic/fw
HEX := $(FWDIR)/build/$(FW).hex

# ordered compile list: filelist.f minus comments, plus the DDR model and harness
# MEM=ihp selects HW/asic/filelist_ihp.f (IHP 1P time-multiplexed macro wrappers) instead of the reference models
MEM ?= asic
FILELIST_F := $(if $(filter ihp,$(MEM)),filelist_ihp.f,filelist.f)
FILELIST := $(addprefix $(ROOT)/,$(shell grep -vE '^\s*(//|$$)' $(ROOT)/HW/asic/$(FILELIST_F)))
# FAST_UART=1: swap the config package for the sim-only one (12.5 MHz
# main_clock_c -> 10x fewer cycles per UART bit). Default = real ASIC config.
ifeq ($(FAST_UART),1)
FILELIST := $(patsubst $(ROOT)/HW/asic/rtl/config.vhd,$(ROOT)/HW/asic/tb/config_sim.vhd,$(FILELIST))
export MAIN_CLOCK_HZ := 12500000
endif
# CHIP=hb: the QFN64 chip top (soc2611_chip_top) with two HyperRAM device models on its HyperBus
# instead of the generic ASIC top with the DDR model; test_fw.py is the same.
CHIP ?= asic
ifeq ($(CHIP),hb)
VHDL_SOURCES := $(FILELIST) \
                $(ROOT)/HW/asic/tb/hyperram_model.vhd \
                $(ROOT)/HW/asic/tb/tb_soc2611_hb.vhd
TOPLEVEL := tb_soc2611_hb
else
VHDL_SOURCES := $(FILELIST) \
                $(ROOT)/HW/simulation/mem128.vhd \
                $(ROOT)/HW/asic/tb/tb_soc2611_fw.vhd

TOPLEVEL := tb_soc2611_fw
endif
COCOTB_TEST_MODULES ?= test_fw
export PYTHONPATH := $(ROOT)/HW/asic/cocotb:$(PYTHONPATH)

# --std=08 must reach import, elaboration AND run (GHDL_ARGS is used by all three)
GHDL_ARGS += --std=08 -frelaxed   # -frelaxed: the HyperRAM model keeps its 8 MB array in a shared variable
COMPILE_ARGS += -frelaxed -Wno-hide -Wno-shared
SIM_ARGS += -gHEX_FILE=$(HEX) --ieee-asserts=disable
export FW_HEX := $(HEX)
# DP instruction FIFO depth seen by T01: 2**dp_instr_fifo_depth_c-1 (config.vhd); 63 for the ASIC lean config
DP_FIFO_MAX ?= 63
export DP_FIFO_MAX
export CFLAGS_EXTRA := -DDP_FIFO_MAX=$(DP_FIFO_MAX)
export FW_NAME := $(FW)

# the firmware image must be (re)built BEFORE the simulation runs: cocotb's
# results target depends on CUSTOM_SIM_DEPS (a plain `sim: $(HEX)` after the
# include would run the simulation first, with a stale image)
CUSTOM_SIM_DEPS += $(HEX)

include $(shell cocotb-config --makefiles)/Makefile.sim

$(HEX): $(FWDIR)/$(FW).c $(FWDIR)/start.S $(FWDIR)/link.ld $(FWDIR)/build.sh
	$(FWDIR)/build.sh $(FW)
