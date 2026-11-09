------------------------------------------------------------------------------
-- Copyright [2014] [Ztachip Technologies Inc]
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
-- http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
------------------------------------------------------------------------------
----------
-- SIMULATION-ONLY variant of HW/asic/rtl/config.vhd (same package name).
--
-- Identical to the ASIC configuration except main_clock_c, which only sets
-- the UART baud divider and the timer tick. Declaring the core clock as
-- 12.5 MHz makes one UART bit 108 core cycles instead of 1085, so the
-- firmware-level cocotb suite runs ~10x faster. Selected with
-- `make FAST_UART=1` in HW/asic/cocotb; the default build uses the real
-- ASIC config.
----------

library std;
use std.standard.all;
LIBRARY ieee;
USE ieee.std_logic_1164.all;
use IEEE.numeric_std.all;

package config is
constant pid_gen_max_c: integer:=4;
constant min_mem_depth_c:integer:=512;
constant exmem_data_width_c:integer:=128;
constant main_clock_c:integer:=12500000;   -- SIM ONLY (ASIC: 125000000)
constant fpu_enabled_c:boolean:=FALSE;
constant MAX_TENSOR_LOG2_SIZE: integer:=24;

-----------------------------------------------------------------
-- ASIC lean configuration (IHP SG13CMOS5L test chip, QFN64):
-- 8 PCOREs, camera in / VGA out, 4 KB TCM, 16 KB scratchpad (SW: SRAM_DEPTH 14),
-- throughput FIFOs halved. See HW/asic/dgse/RUN-ihp-synth-01.md.
-----------------------------------------------------------------
constant camera_enabled_c:boolean:=TRUE;
constant vga_enabled_c:boolean:=FALSE;
constant camera_stream_depth_c:integer:=8;
constant tcm_depth_c:integer:=12;
constant sram_bank_depth_c:integer:=13;
constant dp_data_fifo_depth_c:integer:=8;
constant ddr_read_pend_depth_c:integer:=8;
constant axi_rdata_fifo_depth_c:integer:=8;
constant dp_instr_fifo_depth_c:integer:=6;
constant cpu_jtag_c:boolean:=TRUE;   -- TRUE: VexRiscv riscv_jtag (JTAG debug TAP, reset vector 0, Ram_1w_1rs memories)
constant hart_enabled_c:boolean:=FALSE;   -- FALSE: one register-file context per PCORE (no 2nd HART), x-registers halved (V. Nguyen)
constant axi_cmd_fifo_depth_c:integer:=3;        -- log2 depth of the axi_merge per-port command FIFOs (3 = 8 entries, flops)
constant axi_rdata_port_fifo_depth_c:integer:=3;  -- log2 depth of the axi_merge read-data FIFOs on ports 0/1 (port 2 stays 7)
end;
