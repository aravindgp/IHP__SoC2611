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
-- Firmware-level simulation harness for the ASIC core top (cocotb DUT).
--
-- dgrid_soc1_asic_top + the behavioural DDR model (HW/simulation/mem128.vhd)
-- preloaded with a firmware image (Intel HEX, generic HEX_FILE). Clocks are
-- generated here (fast) and only reset, UART and GPIO are driven/observed
-- from cocotb (HW/asic/cocotb/test_fw.py).
--
-- Clock periods are generics so the Python side can read them back; the
-- defaults mirror the SDC (250 MHz clk_x2, 100 MHz DDR, 24 MHz camera,
-- 25 MHz VGA).
----------

library std;
use std.standard.all;
LIBRARY ieee;
USE ieee.std_logic_1164.all;
use IEEE.numeric_std.all;
use work.ztachip_pkg.all;
use work.config.all;

entity tb_dgrid_soc1_fw is
   generic
   (
      HEX_FILE          : string := "fw.hex";
      CLK_X2_PERIOD     : time := 4 ns;
      CLK_DDR_PERIOD    : time := 10 ns;
      CLK_CAMERA_PERIOD : time := 41666 ps;
      CLK_VGA_PERIOD    : time := 40 ns
   );
   port
   (
      porst_n_in   : IN  STD_LOGIC;
      uart_rx_in   : IN  STD_LOGIC;
      uart_tx_out  : OUT STD_LOGIC;
      gpio_in      : IN  STD_LOGIC_VECTOR(3 downto 0);
      gpio_out     : OUT STD_LOGIC_VECTOR(3 downto 0);
      -- clocks exported for observation only
      clk_x2_out   : OUT STD_LOGIC;
      clk_ddr_out  : OUT STD_LOGIC
   );
end tb_dgrid_soc1_fw;

architecture sim of tb_dgrid_soc1_fw is

signal clk_x2     : std_logic := '0';
signal clk_ddr    : std_logic := '0';
signal clk_camera : std_logic := '0';
signal clk_vga    : std_logic := '0';
signal rst_ddr_n  : std_logic;

signal ddr_araddr  : std_logic_vector(31 downto 0);
signal ddr_arburst : std_logic_vector(1 downto 0);
signal ddr_arlen   : std_logic_vector(7 downto 0);
signal ddr_arready : std_logic;
signal ddr_arsize  : std_logic_vector(2 downto 0);
signal ddr_arvalid : std_logic;
signal ddr_awaddr  : std_logic_vector(31 downto 0);
signal ddr_awburst : std_logic_vector(1 downto 0);
signal ddr_awlen   : std_logic_vector(7 downto 0);
signal ddr_awready : std_logic;
signal ddr_awsize  : std_logic_vector(2 downto 0);
signal ddr_awvalid : std_logic;
signal ddr_bready  : std_logic;
signal ddr_bresp   : std_logic_vector(1 downto 0);
signal ddr_bvalid  : std_logic;
signal ddr_rdata   : std_logic_vector(exmem_data_width_c-1 downto 0);
signal ddr_rlast   : std_logic;
signal ddr_rready  : std_logic;
signal ddr_rresp   : std_logic_vector(1 downto 0);
signal ddr_rvalid  : std_logic;
signal ddr_wdata   : std_logic_vector(exmem_data_width_c-1 downto 0);
signal ddr_wlast   : std_logic;
signal ddr_wready  : std_logic;
signal ddr_wstrb   : std_logic_vector(exmem_data_width_c/8-1 downto 0);
signal ddr_wvalid  : std_logic;

begin

clk_x2     <= not clk_x2 after CLK_X2_PERIOD/2;
-- DDR-model clock = clk_x2/2 (edge-aligned, like the DUT's clk_main) so the model's FIFOs can use the 2x clock
process(clk_x2) begin if rising_edge(clk_x2) then clk_ddr <= not clk_ddr; end if; end process;
clk_camera <= not clk_camera after CLK_CAMERA_PERIOD/2;
clk_vga    <= not clk_vga after CLK_VGA_PERIOD/2;
clk_x2_out  <= clk_x2;
clk_ddr_out <= clk_ddr;

-- the DDR model wants a reset synchronous to its clock
ddr_rst_i : entity work.reset_sync
   port map(clock_in=>clk_ddr, arst_n_in=>porst_n_in, rst_n_out=>rst_ddr_n);

dut : entity work.dgrid_soc1_asic_top
   port map
   (
      clk_x2_in        => clk_x2,
      clk_camera_in    => clk_camera,
      clk_vga_in       => clk_vga,
      clk_ddr_in       => clk_ddr,
      porst_n_in       => porst_n_in,

      ddr_araddr_out   => ddr_araddr,
      ddr_arburst_out  => ddr_arburst,
      ddr_arlen_out    => ddr_arlen,
      ddr_arready_in   => ddr_arready,
      ddr_arsize_out   => ddr_arsize,
      ddr_arvalid_out  => ddr_arvalid,
      ddr_awaddr_out   => ddr_awaddr,
      ddr_awburst_out  => ddr_awburst,
      ddr_awlen_out    => ddr_awlen,
      ddr_awready_in   => ddr_awready,
      ddr_awsize_out   => ddr_awsize,
      ddr_awvalid_out  => ddr_awvalid,
      ddr_bready_out   => ddr_bready,
      ddr_bresp_in     => ddr_bresp,
      ddr_bvalid_in    => ddr_bvalid,
      ddr_rdata_in     => ddr_rdata,
      ddr_rlast_in     => ddr_rlast,
      ddr_rready_out   => ddr_rready,
      ddr_rresp_in     => ddr_rresp,
      ddr_rvalid_in    => ddr_rvalid,
      ddr_wdata_out    => ddr_wdata,
      ddr_wlast_out    => ddr_wlast,
      ddr_wready_in    => ddr_wready,
      ddr_wstrb_out    => ddr_wstrb,
      ddr_wvalid_out   => ddr_wvalid,

      apb_paddr_out    => open,
      apb_penable_out  => open,
      apb_pwrite_out   => open,
      apb_pwdata_out   => open,
      apb_pready_in    => '0',
      apb_prdata_in    => (others=>'0'),
      apb_pslverror_in => '0',

      gpio_out         => gpio_out,
      gpio_in          => gpio_in,
      uart_tx_out      => uart_tx_out,
      uart_rx_in       => uart_rx_in,
      spi_ss_out       => open,
      spi_sclk_out     => open,
      spi_mosi_out     => open,
      spi_cs_sd_out    => open,
      spi_cs_esp32_out => open,
      spi_miso_in      => '0',

      vga_hs_out       => open,
      vga_vs_out       => open,
      vga_r_out        => open,
      vga_g_out        => open,
      vga_b_out        => open,

      cam_scl_out      => open,
      cam_sda_out      => open,
      cam_sda_oe_out   => open,
      cam_reset_out    => open,
      cam_pwdn_out     => open,
      cam_mclk_out     => open,
      cam_pclk_in      => '0',
      cam_d_in         => (others=>'0'),
      cam_vs_in        => '0',
      cam_hs_in        => '0'
   );

ddr_i : entity work.mem128
   generic map(HEX_FILE => HEX_FILE)
   port map
   (
      SDRAM_clk       => clk_ddr,
      SDRAM_clk_x2    => clk_x2,
      SDRAM_reset     => rst_ddr_n,
      SDRAM_araddr    => ddr_araddr,
      SDRAM_arburst   => ddr_arburst,
      SDRAM_arlen     => ddr_arlen,
      SDRAM_arready   => ddr_arready,
      SDRAM_arsize    => ddr_arsize,
      SDRAM_arvalid   => ddr_arvalid,
      SDRAM_awaddr    => ddr_awaddr,
      SDRAM_awburst   => ddr_awburst,
      SDRAM_awlen     => ddr_awlen,
      SDRAM_awready   => ddr_awready,
      SDRAM_awsize    => ddr_awsize,
      SDRAM_awvalid   => ddr_awvalid,
      SDRAM_bready    => ddr_bready,
      SDRAM_bresp     => ddr_bresp,
      SDRAM_bvalid    => ddr_bvalid,
      SDRAM_rdata     => ddr_rdata,
      SDRAM_rlast     => ddr_rlast,
      SDRAM_rready    => ddr_rready,
      SDRAM_rresp     => ddr_rresp,
      SDRAM_rvalid    => ddr_rvalid,
      SDRAM_wdata     => ddr_wdata,
      SDRAM_wlast     => ddr_wlast,
      SDRAM_wready    => ddr_wready,
      SDRAM_wstrb     => ddr_wstrb,
      SDRAM_wvalid    => ddr_wvalid
   );

end sim;
