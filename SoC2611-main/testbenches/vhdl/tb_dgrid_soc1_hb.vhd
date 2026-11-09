---------------------------------------------------------------------------
-- cocotb harness for dgrid_soc1_chip_top: the chip with two HyperRAM
-- device models on its HyperBus (pad-level tri-state resolution, RWDS
-- delay line as on a board), firmware preloaded into device 0 from an
-- Intel HEX file. Same cocotb-facing ports as tb_dgrid_soc1_fw so
-- HW/asic/cocotb/test_fw.py runs unchanged.
---------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.config.all;
use work.ztachip_pkg.all;

entity tb_dgrid_soc1_hb is
   generic
   (
      HEX_FILE          : string  := "fw.hex";
      CLK_X2_PERIOD     : time    := 4 ns;      -- as tb_dgrid_soc1_fw (sim runs the FPGA-like 250/125 MHz)
      HB_POWERUP_CYCLES : natural := 20000;     -- chip default: >= tVCS (150 us) at the simulated 125 MHz core clock too (160 us)
      RWDS_DELAY        : time    := 2 ns;      -- board/pad delay of RWDS into the controller (~1/4 CK)
      HB_MEM_BYTES      : natural := 1048576    -- per device in the model (firmware + test window live below 1 MB)
   );
   port
   (
      porst_n_in   : IN  STD_LOGIC;
      uart_rx_in   : IN  STD_LOGIC;
      uart_tx_out  : OUT STD_LOGIC;
      gpio_in      : IN  STD_LOGIC_VECTOR(3 downto 0);
      gpio_out     : OUT STD_LOGIC_VECTOR(3 downto 0);
      clk_x2_out   : OUT STD_LOGIC;
      hb_error_out : OUT STD_LOGIC_VECTOR(1 downto 0)   -- sticky protocol/timing errors of the two device models
   );
end tb_dgrid_soc1_hb;

architecture sim of tb_dgrid_soc1_hb is
signal clk_x2    : std_logic := '0';
-- controller side
signal c_ck, c_resetn : std_logic;
signal c_csn     : std_logic_vector(0 downto 0);
signal c_rwds_i, c_rwds_o, c_rwds_oe : std_logic;
signal c_dq_o    : std_logic_vector(7 downto 0);
signal c_dq_oe   : std_logic;
-- device side
type dq_arr_t is array(0 to 1) of std_logic_vector(7 downto 0);
signal m_rwds_o, m_rwds_oe, m_dq_oe, m_err : std_logic_vector(1 downto 0);
signal m_dq_o    : dq_arr_t;
-- board wires
signal pin_dq    : std_logic_vector(7 downto 0);
signal pin_rwds  : std_logic;
-- firmware image goes into device 0 only
function hex_for(i : integer) return string is
begin
   if i = 0 then return HEX_FILE; else return ""; end if;
end function;
begin

clk_x2 <= not clk_x2 after CLK_X2_PERIOD/2;
clk_x2_out <= clk_x2;

dut : entity work.dgrid_soc1_chip_top
   generic map(HB_POWERUP_CYCLES => HB_POWERUP_CYCLES)
   port map
   (
      clk_x2_in      => clk_x2,
      porst_n_in     => porst_n_in,
      hb_ck_out      => c_ck,
      hb_csn_out     => c_csn,
      hb_resetn_out  => c_resetn,
      hb_rwds_in     => c_rwds_i,
      hb_rwds_out    => c_rwds_o,
      hb_rwds_oe_out => c_rwds_oe,
      hb_dq_in       => pin_dq,
      hb_dq_out      => c_dq_o,
      hb_dq_oe_out   => c_dq_oe,
      cam_pclk_in    => '0',
      cam_d_in       => (others=>'0'),
      cam_vs_in      => '0',
      cam_hs_in      => '0',
      cam_mclk_out   => open,
      cam_reset_out  => open,
      cam_pwdn_out   => open,
      cam_scl_out    => open,
      cam_sda_out    => open,
      cam_sda_oe_out => open,
      uart_tx_out    => uart_tx_out,
      uart_rx_in     => uart_rx_in,
      spi_sclk_out   => open,
      spi_mosi_out   => open,
      spi_miso_in    => '0',
      spi_csn_out    => open,
      gpio_out       => gpio_out,
      gpio_in        => gpio_in,
      jtag_tdo_out   => open
   );

-- pad-level resolution: controller and devices drive the shared wires
-- through their _oe; a board pull-down keeps RWDS/DQ defined when idle
pin_dq   <= c_dq_o when c_dq_oe='1' else (others=>'Z');
pin_rwds <= c_rwds_o when c_rwds_oe='1' else 'Z';
pin_dq   <= (others=>'L');
pin_rwds <= 'L';
c_rwds_i <= transport pin_rwds after RWDS_DELAY;

mem_g : for i in 0 to 0 generate
   mem_i : entity work.hyperram_model
      generic map
      (
         MEM_BYTES       => HB_MEM_BYTES,
         INITIAL_LATENCY => 6,
         FIXED_LATENCY   => true,
         HEX_FILE        => hex_for(i),     -- device 0 holds the firmware, device 1 stays blank
         TCSM_CHECK      => true,
         NAME            => "hyperram" & integer'image(i)
      )
      port map
      (
         ck        => c_ck,
         ckn       => '0',
         csn       => c_csn(i),
         resetn    => c_resetn,
         rwds_i    => pin_rwds,
         rwds_o    => m_rwds_o(i),
         rwds_oe   => m_rwds_oe(i),
         dq_i      => pin_dq,
         dq_o      => m_dq_o(i),
         dq_oe     => m_dq_oe(i),
         error_out => m_err(i)
      );
   pin_dq   <= m_dq_o(i) when m_dq_oe(i)='1' else (others=>'Z');
   pin_rwds <= m_rwds_o(i) when m_rwds_oe(i)='1' else 'Z';
end generate;

hb_error_out <= '0' & m_err(0);

end sim;
