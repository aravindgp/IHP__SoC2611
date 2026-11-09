------------------------------------------------------------------------------
-- Equivalence testbench: legacy double-pumped RAM wrappers (clock level used
-- as a mux select + transparent output latch) versus the ASIC-clean rewrite
-- (x2_phase flag + flop capture) for ramw, ramw2 and ram2r1w.
--
-- Both versions are driven with identical random stimulus from the core
-- clock domain and their outputs are compared at every core clock rising
-- edge, which is the only point at which the rest of the design samples
-- them (no logic in HW/src is clocked by clock_x2).
--
-- Run with HW/asic/scripts/run_tb_ramw.sh (GHDL, --std=08).
------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use work.ztachip_pkg.all;

entity tb_ramw_equiv is
   generic
   (
      NCYCLES : natural := 20000
   );
end tb_ramw_equiv;

architecture sim of tb_ramw_equiv is

constant AW : natural := 4;   -- 16 words
constant DW : natural := 32;  -- bytes=4, halves of 16 bits

signal clk_x2  : std_logic := '0';
signal clk_r   : std_logic := '0';
signal clk     : std_logic;
signal done    : boolean := false;

-- common stimulus
signal address_a  : std_logic_vector(AW-1 downto 0) := (others=>'0');
signal byteena_a  : std_logic_vector(DW/8-1 downto 0) := (others=>'0');
signal data_a     : std_logic_vector(DW-1 downto 0) := (others=>'0');
signal wren_a     : std_logic := '0';
signal address_b  : std_logic_vector(AW-1 downto 0) := (others=>'0');
signal address2_b : std_logic_vector(AW-1 downto 0) := (others=>'0');

-- outputs
signal ramw_q_old, ramw_q_new     : std_logic_vector(DW-1 downto 0);
signal ramw2_q_old, ramw2_q_new   : std_logic_vector(DW-1 downto 0);
signal r2_q1_old, r2_q1_new       : std_logic_vector(DW-1 downto 0);
signal r2_q2_old, r2_q2_new       : std_logic_vector(DW-1 downto 0);
signal phase                      : std_logic;

begin

-- clock_x2: 4 ns period. core clock = divide-by-2 flop, like HW/simulation/main.vhd
clkgen: process
begin
   while not done loop
      clk_x2 <= '0';
      wait for 2 ns;
      clk_x2 <= '1';
      wait for 2 ns;
   end loop;
   -- a few more edges so the checkers can observe `done` and report
   for i in 1 to 8 loop
      clk_x2 <= '0';
      wait for 2 ns;
      clk_x2 <= '1';
      wait for 2 ns;
   end loop;
   wait;
end process;
process(clk_x2)
begin
   if rising_edge(clk_x2) then
      clk_r <= not clk_r;
   end if;
end process;
clk <= clk_r;

-------------------------------------------------------------------------
-- DUTs
-------------------------------------------------------------------------
ramw_old_i : entity work.ramw_legacy
   generic map(numwords_a=>2**AW, numwords_b=>2**AW, widthad_a=>AW, widthad_b=>AW, width_a=>DW, width_b=>DW)
   port map(clock=>clk, clock_x2=>clk_x2, address_a=>address_a, byteena_a=>byteena_a, data_a=>data_a,
            q_b=>ramw_q_old, wren_a=>wren_a, address_b=>address_b);
ramw_new_i : entity work.ramw
   generic map(numwords_a=>2**AW, numwords_b=>2**AW, widthad_a=>AW, widthad_b=>AW, width_a=>DW, width_b=>DW)
   port map(clock=>clk, clock_x2=>clk_x2, address_a=>address_a, byteena_a=>byteena_a, data_a=>data_a,
            q_b=>ramw_q_new, wren_a=>wren_a, address_b=>address_b);

ramw2_old_i : entity work.ramw2_legacy
   generic map(numwords_a=>2**AW, numwords_b=>2**AW, widthad_a=>AW, widthad_b=>AW, width_a=>DW, width_b=>DW)
   port map(clock=>clk, clock_x2=>clk_x2, address_a=>address_a, data_a=>data_a,
            q_b=>ramw2_q_old, wren_a=>wren_a, address_b=>address_b);
ramw2_new_i : entity work.ramw2
   generic map(numwords_a=>2**AW, numwords_b=>2**AW, widthad_a=>AW, widthad_b=>AW, width_a=>DW, width_b=>DW)
   port map(clock=>clk, clock_x2=>clk_x2, address_a=>address_a, data_a=>data_a,
            q_b=>ramw2_q_new, wren_a=>wren_a, address_b=>address_b);

r2_old_i : entity work.ram2r1w_legacy
   generic map(numwords_a=>2**AW, numwords_b=>2**AW, widthad_a=>AW, widthad_b=>AW, width_a=>DW, width_b=>DW)
   port map(clock=>clk, clock_x2=>clk_x2, address_a=>address_a, byteena_a=>byteena_a, data_a=>data_a, wren_a=>wren_a,
            address1_b=>address_b, q1_b=>r2_q1_old, address2_b=>address2_b, q2_b=>r2_q2_old);
r2_new_i : entity work.ram2r1w
   generic map(numwords_a=>2**AW, numwords_b=>2**AW, widthad_a=>AW, widthad_b=>AW, width_a=>DW, width_b=>DW)
   port map(clock=>clk, clock_x2=>clk_x2, address_a=>address_a, byteena_a=>byteena_a, data_a=>data_a, wren_a=>wren_a,
            address1_b=>address_b, q1_b=>r2_q1_new, address2_b=>address2_b, q2_b=>r2_q2_new);

phase_i : entity work.x2_phase
   port map(clock_in=>clk, clock_x2_in=>clk_x2, phase_out=>phase);

-------------------------------------------------------------------------
-- Stimulus: new random inputs right after every core clock edge (as flops would)
-------------------------------------------------------------------------
stim: process
   variable seed1 : positive := 12345;
   variable seed2 : positive := 6789;
   variable r     : real;
   procedure rnd_slv(signal s : out std_logic_vector; constant w : natural) is
      variable v : std_logic_vector(w-1 downto 0);
   begin
      for i in 0 to w-1 loop
         uniform(seed1, seed2, r);
         if r > 0.5 then v(i) := '1'; else v(i) := '0'; end if;
      end loop;
      s <= v;
   end procedure;
begin
   for n in 1 to NCYCLES loop
      wait until rising_edge(clk);
      rnd_slv(address_a, AW);
      rnd_slv(address_b, AW);
      rnd_slv(address2_b, AW);
      rnd_slv(data_a, DW);
      rnd_slv(byteena_a, DW/8);
      uniform(seed1, seed2, r);
      -- bursts of writes early on so the memories get filled, then 50/50
      if n < 200 or r > 0.5 then wren_a <= '1'; else wren_a <= '0'; end if;
   end loop;
   wait until rising_edge(clk);
   done <= true;
   wait;
end process;

-------------------------------------------------------------------------
-- Checkers
-------------------------------------------------------------------------
check: process
   variable cycles     : natural := 0;
   variable mismatches : natural := 0;
begin
   -- warm-up: let both versions get through their first few accesses
   for i in 1 to 8 loop
      wait until rising_edge(clk);
   end loop;
   while not done loop
      wait until rising_edge(clk);
      cycles := cycles + 1;
      if ramw_q_new /= ramw_q_old then
         mismatches := mismatches + 1;
         report "ramw mismatch at cycle " & integer'image(cycles) severity error;
      end if;
      if ramw2_q_new /= ramw2_q_old then
         mismatches := mismatches + 1;
         report "ramw2 mismatch at cycle " & integer'image(cycles) severity error;
      end if;
      if r2_q1_new /= r2_q1_old then
         mismatches := mismatches + 1;
         report "ram2r1w q1 mismatch at cycle " & integer'image(cycles) severity error;
      end if;
      if r2_q2_new /= r2_q2_old then
         mismatches := mismatches + 1;
         report "ram2r1w q2 mismatch at cycle " & integer'image(cycles) severity error;
      end if;
      -- make sure the comparison is not vacuous (data must be known by now)
      if cycles = 400 then
         assert not is_x(ramw_q_new) and not is_x(r2_q1_new) and not is_x(r2_q2_new) and not is_x(ramw2_q_new)
            report "outputs still unknown after warm-up" severity failure;
      end if;
   end loop;
   if mismatches = 0 then
      report "RAMW EQUIV TB: PASS cycles=" & integer'image(cycles) & " mismatches=0" severity note;
   else
      report "RAMW EQUIV TB: FAIL cycles=" & integer'image(cycles) & " mismatches=" & integer'image(mismatches) severity failure;
   end if;
   wait;
end process;

-- x2_phase must reproduce the core clock level after every x2 edge
phase_check: process
begin
   for i in 1 to 8 loop
      wait until rising_edge(clk_x2);
   end loop;
   while not done loop
      wait until rising_edge(clk_x2);
      wait for 1 ns;
      assert phase = clk report "x2_phase: phase /= clock level" severity failure;
   end loop;
   wait;
end process;

end sim;
