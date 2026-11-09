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
-- cocotb harness for the HyperBus controller (HW/asic/cocotb/test_hyperbus.py).
--
-- hyperbus_axi (CS_COUNT=2, short POWERUP_CYCLES) + two hyperram_model
-- devices (8 MB each, short tVCS) sharing CK/DQ/RWDS, with the pad-level
-- tri-state resolution done here (pin <= o when oe='1' else 'Z', weak
-- pull-downs on the shared lines). RWDS reaches the controller's capture
-- input through RWDS_DELAY, standing in for the on-chip strobe delay chain
-- that centres RWDS in the data eye (see hyperbus_rx.vhd).
--
-- The clock is generated here (CLK_PERIOD, 100 MHz default); reset comes
-- from cocotb through a reset synchroniser like on the chip. The AXI4 slave
-- side is exported to cocotb, plus the sticky model error flags.
----------

library std;
use std.standard.all;
LIBRARY ieee;
USE ieee.std_logic_1164.all;
use IEEE.numeric_std.all;

entity tb_hyperbus is
   generic
   (
      CLK_PERIOD      : time    := 10 ns;
      RWDS_DELAY      : time    := 5 ns;   -- ~1/4 CK at 50 MHz
      POWERUP_CYCLES  : natural := 200;
      TVCS_NS         : natural := 1000;
      INITIAL_LATENCY : natural := 6;
      FIXED_LATENCY   : boolean := true;
      MAX_CS_BYTES    : natural := 128;
      MEM_BYTES       : natural := 8388608   -- per device; smaller values only shorten the model init
   );
   port
   (
      reset_n_in      : IN  STD_LOGIC;
      clk_out         : OUT STD_LOGIC;
      axi_araddr_in   : IN  STD_LOGIC_VECTOR(31 downto 0);
      axi_arlen_in    : IN  STD_LOGIC_VECTOR(7 downto 0);
      axi_arsize_in   : IN  STD_LOGIC_VECTOR(2 downto 0);
      axi_arburst_in  : IN  STD_LOGIC_VECTOR(1 downto 0);
      axi_arvalid_in  : IN  STD_LOGIC;
      axi_arready_out : OUT STD_LOGIC;
      axi_rdata_out   : OUT STD_LOGIC_VECTOR(127 downto 0);
      axi_rresp_out   : OUT STD_LOGIC_VECTOR(1 downto 0);
      axi_rlast_out   : OUT STD_LOGIC;
      axi_rvalid_out  : OUT STD_LOGIC;
      axi_rready_in   : IN  STD_LOGIC;
      axi_awaddr_in   : IN  STD_LOGIC_VECTOR(31 downto 0);
      axi_awlen_in    : IN  STD_LOGIC_VECTOR(7 downto 0);
      axi_awsize_in   : IN  STD_LOGIC_VECTOR(2 downto 0);
      axi_awburst_in  : IN  STD_LOGIC_VECTOR(1 downto 0);
      axi_awvalid_in  : IN  STD_LOGIC;
      axi_awready_out : OUT STD_LOGIC;
      axi_wdata_in    : IN  STD_LOGIC_VECTOR(127 downto 0);
      axi_wstrb_in    : IN  STD_LOGIC_VECTOR(15 downto 0);
      axi_wlast_in    : IN  STD_LOGIC;
      axi_wvalid_in   : IN  STD_LOGIC;
      axi_wready_out  : OUT STD_LOGIC;
      axi_bresp_out   : OUT STD_LOGIC_VECTOR(1 downto 0);
      axi_bvalid_out  : OUT STD_LOGIC;
      axi_bready_in   : IN  STD_LOGIC;
      -- observation
      hb_csn_out      : OUT STD_LOGIC_VECTOR(1 downto 0);
      hb_ck_out       : OUT STD_LOGIC;
      hb_resetn_out   : OUT STD_LOGIC;
      model_error_out : OUT STD_LOGIC_VECTOR(1 downto 0)
   );
end tb_hyperbus;

architecture sim of tb_hyperbus is

signal clk        : std_logic := '0';
signal rst_n      : std_logic;

-- controller side
signal c_ck       : std_logic;
signal c_ckn      : std_logic;
signal c_csn      : std_logic_vector(1 downto 0);
signal c_resetn   : std_logic;
signal c_rwds_i   : std_logic;
signal c_rwds_o   : std_logic;
signal c_rwds_oe  : std_logic;
signal c_dq_o     : std_logic_vector(7 downto 0);
signal c_dq_oe    : std_logic;

-- device sides
type dq_arr_t is array(0 to 1) of std_logic_vector(7 downto 0);
signal m_rwds_o   : std_logic_vector(1 downto 0);
signal m_rwds_oe  : std_logic_vector(1 downto 0);
signal m_dq_o     : dq_arr_t;
signal m_dq_oe    : std_logic_vector(1 downto 0);
signal m_err      : std_logic_vector(1 downto 0);

-- board wires
signal pin_dq     : std_logic_vector(7 downto 0);
signal pin_rwds   : std_logic;

begin

clk <= not clk after CLK_PERIOD/2;
clk_out <= clk;

rst_i : entity work.reset_sync
   port map(clock_in=>clk, arst_n_in=>reset_n_in, rst_n_out=>rst_n);

dut : entity work.hyperbus_axi
   generic map
   (
      CS_COUNT => 2,
      INITIAL_LATENCY => INITIAL_LATENCY,
      FIXED_LATENCY => FIXED_LATENCY,
      MAX_CS_BYTES => MAX_CS_BYTES,
      POWERUP_CYCLES => POWERUP_CYCLES
   )
   port map
   (
      clock_in => clk,
      reset_in => rst_n,
      axi_araddr_in => axi_araddr_in,
      axi_arlen_in => axi_arlen_in,
      axi_arsize_in => axi_arsize_in,
      axi_arburst_in => axi_arburst_in,
      axi_arvalid_in => axi_arvalid_in,
      axi_arready_out => axi_arready_out,
      axi_rdata_out => axi_rdata_out,
      axi_rresp_out => axi_rresp_out,
      axi_rlast_out => axi_rlast_out,
      axi_rvalid_out => axi_rvalid_out,
      axi_rready_in => axi_rready_in,
      axi_awaddr_in => axi_awaddr_in,
      axi_awlen_in => axi_awlen_in,
      axi_awsize_in => axi_awsize_in,
      axi_awburst_in => axi_awburst_in,
      axi_awvalid_in => axi_awvalid_in,
      axi_awready_out => axi_awready_out,
      axi_wdata_in => axi_wdata_in,
      axi_wstrb_in => axi_wstrb_in,
      axi_wlast_in => axi_wlast_in,
      axi_wvalid_in => axi_wvalid_in,
      axi_wready_out => axi_wready_out,
      axi_bresp_out => axi_bresp_out,
      axi_bvalid_out => axi_bvalid_out,
      axi_bready_in => axi_bready_in,
      hb_ck_out => c_ck,
      hb_ckn_out => c_ckn,
      hb_csn_out => c_csn,
      hb_resetn_out => c_resetn,
      hb_rwds_i => c_rwds_i,
      hb_rwds_o => c_rwds_o,
      hb_rwds_oe => c_rwds_oe,
      hb_dq_i => pin_dq,
      hb_dq_o => c_dq_o,
      hb_dq_oe => c_dq_oe
   );

-- pad-level tri-states (controller side)
pin_dq   <= c_dq_o when c_dq_oe='1' else (others=>'Z');
pin_rwds <= c_rwds_o when c_rwds_oe='1' else 'Z';
-- weak pull-downs on the shared lines
pin_dq   <= (others=>'L');
pin_rwds <= 'L';
-- on-chip RWDS delay chain (strobe centring for the read capture)
c_rwds_i <= transport pin_rwds after RWDS_DELAY;

mem_g : for i in 0 to 1 generate
   mem_i : entity work.hyperram_model
      generic map
      (
         MEM_BYTES => MEM_BYTES,
         INITIAL_LATENCY => INITIAL_LATENCY,
         FIXED_LATENCY => FIXED_LATENCY,
         HEX_FILE => "",
         TCSM_CHECK => true,
         TVCS_NS => TVCS_NS,
         NAME => "hyperram" & integer'image(i)
      )
      port map
      (
         ck => c_ck,
         ckn => c_ckn,
         csn => c_csn(i),
         resetn => c_resetn,
         rwds_i => pin_rwds,
         rwds_o => m_rwds_o(i),
         rwds_oe => m_rwds_oe(i),
         dq_i => pin_dq,
         dq_o => m_dq_o(i),
         dq_oe => m_dq_oe(i),
         error_out => m_err(i)
      );
   pin_dq   <= m_dq_o(i) when m_dq_oe(i)='1' else (others=>'Z');
   pin_rwds <= m_rwds_o(i) when m_rwds_oe(i)='1' else 'Z';
end generate;

hb_csn_out <= c_csn;
hb_ck_out <= c_ck;
hb_resetn_out <= c_resetn;
model_error_out <= m_err;

end sim;
