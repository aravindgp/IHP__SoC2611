-- Plain-GHDL speed probe: tb_dgrid_soc1_fw with constant stimulus so the
-- simulation runs without cocotb (ghdl -r tb_speed --stop-time=... --stats).
library ieee;
use ieee.std_logic_1164.all;

entity tb_speed is
   generic(HEX_FILE : string := "fw.hex");
end tb_speed;

architecture sim of tb_speed is
signal porst_n : std_logic := '0';
signal tx      : std_logic;
signal gpio_o  : std_logic_vector(3 downto 0);
signal clk_x2, clk_ddr : std_logic;
begin
   porst_n <= '1' after 1 us;
   dut : entity work.tb_dgrid_soc1_fw
      generic map(HEX_FILE => HEX_FILE)
      port map(porst_n_in => porst_n, uart_rx_in => '1', uart_tx_out => tx,
               gpio_in => "1001", gpio_out => gpio_o, clk_x2_out => clk_x2, clk_ddr_out => clk_ddr);
end sim;
