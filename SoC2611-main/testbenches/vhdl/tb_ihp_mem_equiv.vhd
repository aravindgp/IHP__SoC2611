------------------------------------------------------------------------------
-- Equivalence testbench: IHP SRAM-macro memory wrappers (HW/platform/ihp,
-- library `ihp`) against the behavioural ASIC wrappers (HW/platform/asic,
-- library `golden`), seen from the core clock.
--
-- For every geometry of the DGrid-SoC1 inventory one `pair_*` block drives
-- the golden and the ihp wrapper with identical random traffic (small
-- address range to force collisions, same-address read/write in one cycle,
-- write bursts, idle stretches, random byte enables) and compares the read
-- data at every core clock rising edge (the only point where HW/src samples
-- it). First mismatch -> assertion failure with the cycle number.
--
-- Also compared: HW/src/util/ramw.vhd / ramw2.vhd (golden, on asic
-- DPRAM_BE/DPRAM) against HW/platform/ihp/ramw.vhd / ramw2.vhd, and
-- HW/src/util/ram2r1w.vhd on asic DPRAM_BE against the same ram2r1w on ihp
-- DPRAM_BE with two_port => true (bound through the configuration at the end
-- of this file, so HW/src stays untouched).
--
-- SPRAM/SPRAM_BE: a 1-port macro cannot read the old content of the word it
-- is writing in the same cycle; the ihp wrapper holds q_a in the cycle after a
-- write (documented deviation). Those cycles are excluded from the compare
-- and counted.
--
-- DPRAM_DUAL_CLOCK (afifo storage): `pair_dc` drives the golden flop model
-- and the ihp 2-port-macro wrapper from two clocks (unrelated 7 ns / 11 ns,
-- and write clock = 2x read clock / read clock = 2x write clock) with
-- FIFO-like traffic: a writer and a reader advance sequential pointers at
-- random, with the TB keeping the write address >= 2 words away from the
-- word being read (a 2P macro gives no guarantee for a cross-clock read of
-- the word being written; afifo never consumes such a read). q_b is
-- compared at every read-clock rising edge after warm-up.
--
-- Run with HW/asic/scripts/run_tb_ihp_mem.sh (GHDL, --std=08).
------------------------------------------------------------------------------

-------------------------------------------------------------------------
-- shared random stimulus
-------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

package tb_ihp_stim_pkg is
   type stim_state_t is record
      seed1, seed2 : positive;
      idle_left    : natural;   -- remaining idle (no write) cycles
      burst_left   : natural;   -- remaining forced-write cycles
   end record;
   procedure rnd_real(st : inout stim_state_t; r : out real);
   procedure rnd_slv(st : inout stim_state_t; signal s : out std_logic_vector; constant w : natural);
   procedure rnd_addr(st : inout stim_state_t; signal s : out std_logic_vector; constant aw, depth : natural);
   procedure rnd_wren(st : inout stim_state_t; signal wren : out std_logic; constant cycle, fill : natural);
end package;

package body tb_ihp_stim_pkg is

   procedure rnd_real(st : inout stim_state_t; r : out real) is
   begin
      uniform(st.seed1, st.seed2, r);
   end procedure;

   procedure rnd_slv(st : inout stim_state_t; signal s : out std_logic_vector; constant w : natural) is
      variable v : std_logic_vector(w-1 downto 0);
      variable r : real;
   begin
      for i in 0 to w-1 loop
         uniform(st.seed1, st.seed2, r);
         if r > 0.5 then v(i) := '1'; else v(i) := '0'; end if;
      end loop;
      s <= v;
   end procedure;

   -- 35 %: one of the 8 lowest words (collisions), else uniform over the memory
   procedure rnd_addr(st : inout stim_state_t; signal s : out std_logic_vector; constant aw, depth : natural) is
      variable r   : real;
      variable a   : natural;
      variable rng : natural;
   begin
      uniform(st.seed1, st.seed2, r);
      if r < 0.35 then
         rng := 8;
         if rng > depth then rng := depth; end if;
      else
         rng := depth;
      end if;
      uniform(st.seed1, st.seed2, r);
      a := natural(floor(r * real(rng)));
      if a >= rng then a := rng - 1; end if;
      s <= std_logic_vector(to_unsigned(a, aw));
   end procedure;

   -- no writes in the first cycles (x2_phase has no reset: its flag is
   -- undefined in the first core cycle after power-up, as for ramw; the
   -- design is in reset then), fill bursts early on, then write bursts (1..8),
   -- idle stretches (1..8), else 50/50
   procedure rnd_wren(st : inout stim_state_t; signal wren : out std_logic; constant cycle, fill : natural) is
      variable r : real;
   begin
      uniform(st.seed1, st.seed2, r);
      if cycle < 4 then
         wren <= '0';
      elsif cycle < fill then
         wren <= '1';
      elsif st.burst_left > 0 then
         st.burst_left := st.burst_left - 1;
         wren <= '1';
      elsif st.idle_left > 0 then
         st.idle_left := st.idle_left - 1;
         wren <= '0';
      elsif r < 0.08 then
         st.burst_left := 1 + natural(floor(r * 100.0));
         wren <= '1';
      elsif r < 0.16 then
         st.idle_left := 1 + natural(floor((r - 0.08) * 100.0));
         wren <= '0';
      elsif r < 0.58 then
         wren <= '1';
      else
         wren <= '0';
      end if;
   end procedure;

end package body;

-------------------------------------------------------------------------
-- pair_dp: DPRAM / DPRAM_BE (golden flop model vs ihp macros)
-------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.tb_ihp_stim_pkg.all;
library golden;
library ihp;

entity pair_dp is
   generic (
      TAG      : string;
      W        : natural;
      D        : natural;
      AW       : natural;
      BE       : boolean;            -- DPRAM_BE instead of DPRAM
      TWO_PORT : boolean := false;
      SEED     : positive := 1;
      NCYCLES  : natural := 20000
   );
   port (
      clk      : in  std_logic;
      clk_x2   : in  std_logic;
      finished : out boolean := false
   );
end entity;

architecture sim of pair_dp is
constant BW : natural := W/8;
signal address_a, address_b : std_logic_vector(AW-1 downto 0) := (others => '0');
signal data_a               : std_logic_vector(W-1 downto 0) := (others => '0');
signal byteena_a            : std_logic_vector(BW-1 downto 0) := (others => '1');
signal wren_a               : std_logic := '0';
signal q_gold, q_ihp        : std_logic_vector(W-1 downto 0);
signal stim_done            : boolean := false;
begin

g_be: if BE generate
   gold_i : entity golden.DPRAM_BE
      generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W)
      port map (address_a=>address_a, byteena_a=>byteena_a, clock0=>clk, data_a=>data_a, q_b=>q_gold,
                wren_a=>wren_a, address_b=>address_b);
   ihp_i : entity ihp.DPRAM_BE
      generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W, two_port=>TWO_PORT)
      port map (address_a=>address_a, byteena_a=>byteena_a, clock0=>clk, data_a=>data_a, q_b=>q_ihp,
                wren_a=>wren_a, address_b=>address_b, clock_x2=>clk_x2);
end generate;
g_nobe: if not BE generate
   gold_i : entity golden.DPRAM
      generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W)
      port map (address_a=>address_a, clock=>clk, data_a=>data_a, q_b=>q_gold, wren_a=>wren_a, address_b=>address_b);
   ihp_i : entity ihp.DPRAM
      generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W, two_port=>TWO_PORT)
      port map (address_a=>address_a, clock=>clk, data_a=>data_a, q_b=>q_ihp, wren_a=>wren_a, address_b=>address_b,
                clock_x2=>clk_x2);
end generate;

stim: process
   variable st : stim_state_t := (SEED*7919+1, SEED*104729+3, 0, 0);
   variable r  : real;
begin
   for n in 1 to NCYCLES loop
      wait until rising_edge(clk);
      rnd_addr(st, address_a, AW, D);
      rnd_addr(st, address_b, AW, D);
      rnd_real(st, r);
      if r < 0.15 then address_b <= address_a; end if;   -- forced same-address read/write
      rnd_slv(st, data_a, W);
      rnd_real(st, r);
      if r < 0.25 then byteena_a <= (others => '1'); else rnd_slv(st, byteena_a, BW); end if;
      rnd_wren(st, wren_a, n, 300 + 3*D);
   end loop;
   wait until rising_edge(clk);
   stim_done <= true;
   wait;
end process;

check: process
   variable cycles, known : natural := 0;
begin
   for i in 1 to 16 loop
      wait until rising_edge(clk);
   end loop;
   while not stim_done loop
      wait until rising_edge(clk);
      cycles := cycles + 1;
      assert q_ihp = q_gold
         report TAG & ": q_b mismatch at cycle " & integer'image(cycles) &
                " golden=" & to_hstring(q_gold) & " ihp=" & to_hstring(q_ihp)
         severity failure;
      if not is_x(q_gold) then known := known + 1; end if;
   end loop;
   assert known > cycles/4 report TAG & ": comparison mostly unknown data" severity failure;
   report "PASS " & TAG & " cycles=" & integer'image(cycles) & " known=" & integer'image(known);
   finished <= true;
   wait;
end process;

end architecture;

-------------------------------------------------------------------------
-- pair_sp: SPRAM / SPRAM_BE
-------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.tb_ihp_stim_pkg.all;
library golden;
library ihp;

entity pair_sp is
   generic (
      TAG     : string;
      W       : natural;
      D       : natural;
      AW      : natural;
      BE      : boolean;
      SEED    : positive := 1;
      NCYCLES : natural := 20000
   );
   port (
      clk      : in  std_logic;
      finished : out boolean := false
   );
end entity;

architecture sim of pair_sp is
constant BW : natural := W/8;
signal address_a     : std_logic_vector(AW-1 downto 0) := (others => '0');
signal data_a        : std_logic_vector(W-1 downto 0) := (others => '0');
signal byteena_a     : std_logic_vector(BW-1 downto 0) := (others => '1');
signal wren_a        : std_logic := '0';
signal q_gold, q_ihp : std_logic_vector(W-1 downto 0);
signal stim_done     : boolean := false;
begin

g_be: if BE generate
   gold_i : entity golden.SPRAM_BE
      generic map (numwords_a=>D, widthad_a=>AW, width_a=>W)
      port map (address_a=>address_a, clock0=>clk, data_a=>data_a, wren_a=>wren_a, byteena_a=>byteena_a, q_a=>q_gold);
   ihp_i : entity ihp.SPRAM_BE
      generic map (numwords_a=>D, widthad_a=>AW, width_a=>W)
      port map (address_a=>address_a, clock0=>clk, data_a=>data_a, wren_a=>wren_a, byteena_a=>byteena_a, q_a=>q_ihp);
end generate;
g_nobe: if not BE generate
   gold_i : entity golden.SPRAM
      generic map (numwords_a=>D, widthad_a=>AW, width_a=>W)
      port map (address_a=>address_a, clock0=>clk, data_a=>data_a, wren_a=>wren_a, q_a=>q_gold);
   ihp_i : entity ihp.SPRAM
      generic map (numwords_a=>D, widthad_a=>AW, width_a=>W)
      port map (address_a=>address_a, clock0=>clk, data_a=>data_a, wren_a=>wren_a, q_a=>q_ihp);
end generate;

stim: process
   variable st : stim_state_t := (SEED*7919+1, SEED*104729+3, 0, 0);
   variable r  : real;
begin
   for n in 1 to NCYCLES loop
      wait until rising_edge(clk);
      rnd_addr(st, address_a, AW, D);
      rnd_slv(st, data_a, W);
      rnd_real(st, r);
      if r < 0.25 then byteena_a <= (others => '1'); else rnd_slv(st, byteena_a, BW); end if;
      rnd_wren(st, wren_a, n, 300 + 3*D);
   end loop;
   wait until rising_edge(clk);
   stim_done <= true;
   wait;
end process;

check: process
   variable cycles, known, skipped : natural := 0;
   variable wr_prev : boolean := true;
begin
   for i in 1 to 16 loop
      wait until rising_edge(clk);
      wr_prev := (wren_a = '1');
   end loop;
   while not stim_done loop
      wait until rising_edge(clk);
      cycles := cycles + 1;
      -- q seen now is the result of the previous edge's access; after a write
      -- the golden shows the overwritten word, the macro holds (see header)
      if wr_prev then
         skipped := skipped + 1;
      else
         assert q_ihp = q_gold
            report TAG & ": q_a mismatch at cycle " & integer'image(cycles) &
                   " golden=" & to_hstring(q_gold) & " ihp=" & to_hstring(q_ihp)
            severity failure;
         if not is_x(q_gold) then known := known + 1; end if;
      end if;
      wr_prev := (wren_a = '1');
   end loop;
   assert known > (cycles - skipped)/4 report TAG & ": comparison mostly unknown data" severity failure;
   report "PASS " & TAG & " cycles=" & integer'image(cycles) & " known=" & integer'image(known) &
          " skipped_after_write=" & integer'image(skipped);
   finished <= true;
   wait;
end process;

end architecture;

-------------------------------------------------------------------------
-- pair_ramw: HW/src/util/ramw(2) on asic DPRAM(_BE) vs HW/platform/ihp/ramw(2)
-------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.tb_ihp_stim_pkg.all;
library golden;
library ihp;

entity pair_ramw is
   generic (
      TAG     : string;
      W       : natural;
      D       : natural;
      AW      : natural;
      BE      : boolean;            -- ramw (with byte enables) or ramw2
      SEED    : positive := 1;
      NCYCLES : natural := 20000
   );
   port (
      clk      : in  std_logic;
      clk_x2   : in  std_logic;
      finished : out boolean := false
   );
end entity;

architecture sim of pair_ramw is
constant BW : natural := W/8;
signal address_a, address_b : std_logic_vector(AW-1 downto 0) := (others => '0');
signal data_a               : std_logic_vector(W-1 downto 0) := (others => '0');
signal byteena_a            : std_logic_vector(BW-1 downto 0) := (others => '1');
signal wren_a               : std_logic := '0';
signal q_gold, q_ihp        : std_logic_vector(W-1 downto 0);
signal stim_done            : boolean := false;
begin

g_be: if BE generate
   gold_i : entity golden.ramw
      generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W)
      port map (clock=>clk, clock_x2=>clk_x2, address_a=>address_a, byteena_a=>byteena_a, data_a=>data_a,
                q_b=>q_gold, wren_a=>wren_a, address_b=>address_b);
   ihp_i : entity ihp.ramw
      generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W)
      port map (clock=>clk, clock_x2=>clk_x2, address_a=>address_a, byteena_a=>byteena_a, data_a=>data_a,
                q_b=>q_ihp, wren_a=>wren_a, address_b=>address_b);
end generate;
g_nobe: if not BE generate
   gold_i : entity golden.ramw2
      generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W)
      port map (clock=>clk, clock_x2=>clk_x2, address_a=>address_a, data_a=>data_a,
                q_b=>q_gold, wren_a=>wren_a, address_b=>address_b);
   ihp_i : entity ihp.ramw2
      generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W)
      port map (clock=>clk, clock_x2=>clk_x2, address_a=>address_a, data_a=>data_a,
                q_b=>q_ihp, wren_a=>wren_a, address_b=>address_b);
end generate;

stim: process
   variable st : stim_state_t := (SEED*7919+1, SEED*104729+3, 0, 0);
   variable r  : real;
begin
   for n in 1 to NCYCLES loop
      wait until rising_edge(clk);
      rnd_addr(st, address_a, AW, D);
      rnd_addr(st, address_b, AW, D);
      rnd_real(st, r);
      if r < 0.15 then address_b <= address_a; end if;
      rnd_slv(st, data_a, W);
      rnd_real(st, r);
      if r < 0.25 then byteena_a <= (others => '1'); else rnd_slv(st, byteena_a, BW); end if;
      rnd_wren(st, wren_a, n, 300 + 3*D);
   end loop;
   wait until rising_edge(clk);
   stim_done <= true;
   wait;
end process;

check: process
   variable cycles, known : natural := 0;
begin
   for i in 1 to 16 loop
      wait until rising_edge(clk);
   end loop;
   while not stim_done loop
      wait until rising_edge(clk);
      cycles := cycles + 1;
      assert q_ihp = q_gold
         report TAG & ": q_b mismatch at cycle " & integer'image(cycles) &
                " golden=" & to_hstring(q_gold) & " ihp=" & to_hstring(q_ihp)
         severity failure;
      if not is_x(q_gold) then known := known + 1; end if;
   end loop;
   assert known > cycles/4 report TAG & ": comparison mostly unknown data" severity failure;
   report "PASS " & TAG & " cycles=" & integer'image(cycles) & " known=" & integer'image(known);
   finished <= true;
   wait;
end process;

end architecture;

-------------------------------------------------------------------------
-- pair_r2: HW/src/util/ram2r1w on asic DPRAM_BE vs on ihp DPRAM_BE(two_port)
-- (component instances; bound by configuration tb_ihp_mem_equiv_cfg)
-------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.tb_ihp_stim_pkg.all;

entity pair_r2 is
   generic (
      TAG     : string;
      W       : natural;
      D       : natural;
      AW      : natural;
      SEED    : positive := 1;
      NCYCLES : natural := 20000
   );
   port (
      clk      : in  std_logic;
      clk_x2   : in  std_logic;
      finished : out boolean := false
   );
end entity;

architecture sim of pair_r2 is
component ram2r1w is
   generic (
        numwords_a : NATURAL; numwords_b : NATURAL; widthad_a : NATURAL;
        widthad_b : NATURAL; width_a : NATURAL; width_b : NATURAL
   );
   port (
        clock      : IN STD_LOGIC;
        clock_x2   : IN STD_LOGIC;
        address_a  : IN STD_LOGIC_VECTOR (widthad_a-1 DOWNTO 0);
        byteena_a  : IN STD_LOGIC_VECTOR (width_a/8-1 DOWNTO 0);
        data_a     : IN STD_LOGIC_VECTOR (width_a-1 DOWNTO 0);
        wren_a     : IN STD_LOGIC;
        address1_b : IN STD_LOGIC_VECTOR (widthad_b-1 DOWNTO 0);
        q1_b       : OUT STD_LOGIC_VECTOR (width_b-1 DOWNTO 0);
        address2_b : IN STD_LOGIC_VECTOR (widthad_b-1 DOWNTO 0);
        q2_b       : OUT STD_LOGIC_VECTOR (width_b-1 DOWNTO 0)
   );
end component;
constant BW : natural := W/8;
signal address_a, address1_b, address2_b : std_logic_vector(AW-1 downto 0) := (others => '0');
signal data_a               : std_logic_vector(W-1 downto 0) := (others => '0');
signal byteena_a            : std_logic_vector(BW-1 downto 0) := (others => '1');
signal wren_a               : std_logic := '0';
signal q1_gold, q1_ihp      : std_logic_vector(W-1 downto 0);
signal q2_gold, q2_ihp      : std_logic_vector(W-1 downto 0);
signal stim_done            : boolean := false;
begin

gold_i : ram2r1w
   generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W)
   port map (clock=>clk, clock_x2=>clk_x2, address_a=>address_a, byteena_a=>byteena_a, data_a=>data_a, wren_a=>wren_a,
             address1_b=>address1_b, q1_b=>q1_gold, address2_b=>address2_b, q2_b=>q2_gold);
dut_i : ram2r1w
   generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W)
   port map (clock=>clk, clock_x2=>clk_x2, address_a=>address_a, byteena_a=>byteena_a, data_a=>data_a, wren_a=>wren_a,
             address1_b=>address1_b, q1_b=>q1_ihp, address2_b=>address2_b, q2_b=>q2_ihp);

stim: process
   variable st : stim_state_t := (SEED*7919+1, SEED*104729+3, 0, 0);
   variable r  : real;
begin
   for n in 1 to NCYCLES loop
      wait until rising_edge(clk);
      rnd_addr(st, address_a, AW, D);
      rnd_addr(st, address1_b, AW, D);
      rnd_addr(st, address2_b, AW, D);
      rnd_real(st, r);
      if r < 0.15 then address1_b <= address_a; elsif r < 0.30 then address2_b <= address_a; end if;
      rnd_slv(st, data_a, W);
      rnd_real(st, r);
      if r < 0.25 then byteena_a <= (others => '1'); else rnd_slv(st, byteena_a, BW); end if;
      rnd_wren(st, wren_a, n, 300 + 3*D);
   end loop;
   wait until rising_edge(clk);
   stim_done <= true;
   wait;
end process;

check: process
   variable cycles, known : natural := 0;
begin
   for i in 1 to 16 loop
      wait until rising_edge(clk);
   end loop;
   while not stim_done loop
      wait until rising_edge(clk);
      cycles := cycles + 1;
      assert q1_ihp = q1_gold
         report TAG & ": q1_b mismatch at cycle " & integer'image(cycles) &
                " golden=" & to_hstring(q1_gold) & " ihp=" & to_hstring(q1_ihp)
         severity failure;
      assert q2_ihp = q2_gold
         report TAG & ": q2_b mismatch at cycle " & integer'image(cycles) &
                " golden=" & to_hstring(q2_gold) & " ihp=" & to_hstring(q2_ihp)
         severity failure;
      if not is_x(q1_gold) and not is_x(q2_gold) then known := known + 1; end if;
   end loop;
   assert known > cycles/4 report TAG & ": comparison mostly unknown data" severity failure;
   report "PASS " & TAG & " cycles=" & integer'image(cycles) & " known=" & integer'image(known);
   finished <= true;
   wait;
end process;

end architecture;

-------------------------------------------------------------------------
-- pair_dc: DPRAM_DUAL_CLOCK (golden flop model vs ihp 2-port macros),
-- independent write and read clocks
-------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.tb_ihp_stim_pkg.all;
library golden;
library ihp;

entity pair_dc is
   generic (
      TAG     : string;
      W       : natural;
      D       : natural;
      AW      : natural;
      SEED    : positive := 1;
      NCYCLES : natural := 20000     -- read-clock cycles compared
   );
   port (
      wclk     : in  std_logic;
      rclk     : in  std_logic;
      finished : out boolean := false
   );
end entity;

architecture sim of pair_dc is
signal address_a, address_b : std_logic_vector(AW-1 downto 0) := (others => '0');
signal data_a               : std_logic_vector(W-1 downto 0) := (others => '0');
signal wren_a               : std_logic := '0';
signal wren_rnd             : std_logic := '0';   -- random write pattern (bursts/idles), used one cycle later
signal q_gold, q_ihp        : std_logic_vector(W-1 downto 0);
-- FIFO-like pointers, counted modulo 2*D (TB-side oracle shared by both
-- domains). dist = (wptr - rptr) mod 2D; write address = read address iff
-- dist = 0 or D. The writer starts one word ahead and writes only for
-- 1 <= dist <= D-2, the reader advances only for dist >= 2, so dist stays in
-- [1, D-1] and the two addresses never coincide, even on coincident edges.
signal wptr                 : natural range 0 to 2*D-1 := 1;
signal rptr                 : natural range 0 to 2*D-1 := 0;
signal stim_done            : boolean := false;
begin

gold_i : entity golden.DPRAM_DUAL_CLOCK
   generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W)
   port map (address_a=>address_a, clock_a=>wclk, clock_b=>rclk, data_a=>data_a, q_b=>q_gold,
             wren_a=>wren_a, address_b=>address_b);
ihp_i : entity ihp.DPRAM_DUAL_CLOCK
   generic map (numwords_a=>D, numwords_b=>D, widthad_a=>AW, widthad_b=>AW, width_a=>W, width_b=>W)
   port map (address_a=>address_a, clock_a=>wclk, clock_b=>rclk, data_a=>data_a, q_b=>q_ihp,
             wren_a=>wren_a, address_b=>address_b);

-- writer (wclk): writes the word at wptr with random enable/bursts/idles, only
-- while 1 <= dist <= D-2, so the written word is never the word read now nor
-- the one the reader may step to in the same instant (that needs dist >= 2)
writer: process
   variable st  : stim_state_t := (SEED*7919+1, SEED*104729+3, 0, 0);
   variable we  : std_logic;
   variable dist : natural;   -- (wptr - rptr) mod 2D; not `d`: VHDL is case-insensitive, it would hide generic D
   variable n   : natural := 0;
begin
   wren_a <= '0';
   while not stim_done loop
      wait until rising_edge(wclk);
      n := n + 1;
      dist := (wptr + 2*D - rptr) mod (2*D);
      rnd_wren(st, wren_rnd, n, 8);
      we := wren_rnd;                       -- previous cycle's random pattern
      if dist < 1 or dist > D-2 then
         we := '0';
      end if;
      wren_a <= we;
      address_a <= std_logic_vector(to_unsigned(wptr mod D, AW));
      rnd_slv(st, data_a, W);
      if we = '1' then
         wptr <= (wptr + 1) mod (2*D);
      end if;
   end loop;
   wren_a <= '0';
   wait;
end process;

-- reader (rclk): address_b = rptr every cycle (read every cycle, as afifo);
-- advances at random (~55 %) only while at least 2 words are ahead of it
reader: process
   variable st : stim_state_t := (SEED*31337+5, SEED*7907+11, 0, 0);
   variable r  : real;
   variable dist : natural;
begin
   for n in 1 to NCYCLES + 16 loop
      wait until rising_edge(rclk);
      dist := (wptr + 2*D - rptr) mod (2*D);
      rnd_real(st, r);
      if dist >= 2 and r < 0.55 then
         rptr <= (rptr + 1) mod (2*D);
         address_b <= std_logic_vector(to_unsigned((rptr + 1) mod D, AW));
      end if;
   end loop;
   wait until rising_edge(rclk);
   stim_done <= true;
   wait;
end process;

check: process
   variable cycles, known, moved : natural := 0;
   variable prev_rptr : natural := 0;
begin
   for i in 1 to 16 loop
      wait until rising_edge(rclk);
   end loop;
   prev_rptr := rptr;
   while not stim_done loop
      wait until rising_edge(rclk);
      cycles := cycles + 1;
      assert q_ihp = q_gold
         report TAG & ": q_b mismatch at read cycle " & integer'image(cycles) &
                " golden=" & to_hstring(q_gold) & " ihp=" & to_hstring(q_ihp)
         severity failure;
      if not is_x(q_gold) then known := known + 1; end if;
      if rptr /= prev_rptr then moved := moved + 1; end if;
      prev_rptr := rptr;
   end loop;
   assert known > cycles/4 report TAG & ": comparison mostly unknown data" severity failure;
   assert moved > cycles/8 report TAG & ": reader hardly advanced (writer starved?)" severity failure;
   report "PASS " & TAG & " read_cycles=" & integer'image(cycles) & " known=" & integer'image(known) &
          " reads_advanced=" & integer'image(moved);
   finished <= true;
   wait;
end process;

end architecture;

-------------------------------------------------------------------------
-- top
-------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library golden;
library ihp;

entity tb_ihp_mem_equiv is
   generic (
      NCYCLES : natural := 20000
   );
end entity;

architecture sim of tb_ihp_mem_equiv is

component pair_r2 is
   generic (TAG : string; W, D, AW : natural; SEED : positive := 1; NCYCLES : natural := 20000);
   port (clk, clk_x2 : in std_logic; finished : out boolean);
end component;

constant NPAIRS : natural := 37;
signal fin     : boolean_vector(0 to NPAIRS-1) := (others => false);
signal all_fin : boolean := false;
signal clk_x2  : std_logic := '0';
signal clk_r   : std_logic := '0';
signal clk     : std_logic;
signal phase   : std_logic;
signal clk7    : std_logic := '0';   -- 7 ns and 11 ns: unrelated clocks for the dual-clock pairs
signal clk11   : std_logic := '0';

begin

-- clock_x2: 4 ns period; core clock = divide-by-2 flop (as clk_div2 in the ASIC top)
clkgen: process
begin
   while not all_fin loop
      clk_x2 <= '0'; wait for 2 ns;
      clk_x2 <= '1'; wait for 2 ns;
   end loop;
   for i in 1 to 8 loop
      clk_x2 <= '0'; wait for 2 ns;
      clk_x2 <= '1'; wait for 2 ns;
   end loop;
   report "IHP MEM EQUIV TB: PASS pairs=" & integer'image(NPAIRS);
   wait;
end process;
process(clk_x2)
begin
   if rising_edge(clk_x2) then
      clk_r <= not clk_r;
   end if;
end process;
clk <= clk_r;
clkgen7: process
begin
   while not all_fin loop
      clk7 <= '0'; wait for 3500 ps;
      clk7 <= '1'; wait for 3500 ps;
   end loop;
   wait;
end process;
clkgen11: process
begin
   while not all_fin loop
      clk11 <= '0'; wait for 5500 ps;
      clk11 <= '1'; wait for 5500 ps;
   end loop;
   wait;
end process;

process(fin)
   variable a : boolean;
begin
   a := true;
   for i in fin'range loop
      a := a and fin(i);
   end loop;
   all_fin <= a;
end process;

-- DPRAM_BE, 1-port time-multiplexed
p00: entity work.pair_dp generic map ("DPRAM_BE 272x256", 272, 256, 8, true,  false, 1, NCYCLES) port map (clk, clk_x2, fin(0));
p01: entity work.pair_dp generic map ("DPRAM_BE 64x1024", 64, 1024, 10, true, false, 2, NCYCLES) port map (clk, clk_x2, fin(1));
p02: entity work.pair_dp generic map ("DPRAM_BE 72x64",   72,   64, 6, true,  false, 3, NCYCLES) port map (clk, clk_x2, fin(2));
-- DPRAM_BE, 2-port
p03: entity work.pair_dp generic map ("DPRAM_BE 128x256 two_port", 128, 256, 8, true, true, 4, NCYCLES) port map (clk, clk_x2, fin(3));
p04: entity work.pair_dp generic map ("DPRAM_BE 32x1024 two_port", 32, 1024, 10, true, true, 5, NCYCLES) port map (clk, clk_x2, fin(4));
-- DPRAM, 1-port time-multiplexed
p05: entity work.pair_dp generic map ("DPRAM 133x256", 133, 256, 8, false, false, 6, NCYCLES) port map (clk, clk_x2, fin(5));
p06: entity work.pair_dp generic map ("DPRAM 380x256", 380, 256, 8, false, false, 7, NCYCLES) port map (clk, clk_x2, fin(6));
p07: entity work.pair_dp generic map ("DPRAM 64x256",   64, 256, 8, false, false, 8, NCYCLES) port map (clk, clk_x2, fin(7));
p08: entity work.pair_dp generic map ("DPRAM 132x256", 132, 256, 8, false, false, 9, NCYCLES) port map (clk, clk_x2, fin(8));
p09: entity work.pair_dp generic map ("DPRAM 73x256",   73, 256, 8, false, false, 10, NCYCLES) port map (clk, clk_x2, fin(9));
p10: entity work.pair_dp generic map ("DPRAM 67x256",   67, 256, 8, false, false, 11, NCYCLES) port map (clk, clk_x2, fin(10));
p11: entity work.pair_dp generic map ("DPRAM 132x128", 132, 128, 7, false, false, 12, NCYCLES) port map (clk, clk_x2, fin(11));
p12: entity work.pair_dp generic map ("DPRAM 58x256",   58, 256, 8, false, false, 13, NCYCLES) port map (clk, clk_x2, fin(12));
p13: entity work.pair_dp generic map ("DPRAM 58x64",    58,  64, 6, false, false, 14, NCYCLES) port map (clk, clk_x2, fin(13));
p14: entity work.pair_dp generic map ("DPRAM 35x128",   35, 128, 7, false, false, 15, NCYCLES) port map (clk, clk_x2, fin(14));
-- DPRAM two_port without byte enables (2P_64x32 without bit mask is eligible)
p15: entity work.pair_dp generic map ("DPRAM 64x64 two_port", 64, 64, 6, false, true, 16, NCYCLES) port map (clk, clk_x2, fin(15));
-- small memories: flop branch
p16: entity work.pair_dp generic map ("DPRAM 58x32 (flops)",  58, 32, 5, false, false, 17, NCYCLES) port map (clk, clk_x2, fin(16));
p17: entity work.pair_dp generic map ("DPRAM 8x256 (flops)",   8, 256, 8, false, false, 18, NCYCLES) port map (clk, clk_x2, fin(17));
-- shallow memories that became macros with the 8-word / 512-bit flop threshold
p33: entity work.pair_dp generic map ("DPRAM 33x16 (axi_ram_read resp_fifo)", 33, 16, 4, false, false, 41, NCYCLES) port map (clk, clk_x2, fin(33));
p34: entity work.pair_dp generic map ("DPRAM 776x16", 776, 16, 4, false, false, 42, NCYCLES) port map (clk, clk_x2, fin(34));
p35: entity work.pair_dp generic map ("DPRAM 37x32", 37, 32, 5, false, false, 43, NCYCLES) port map (clk, clk_x2, fin(35));
p36: entity work.pair_dp generic map ("DPRAM 5x256", 5, 256, 8, false, false, 44, NCYCLES) port map (clk, clk_x2, fin(36));
-- SPRAM / SPRAM_BE
p18: entity work.pair_sp generic map ("SPRAM 24x512",     24,  512,  9, false, 19, NCYCLES) port map (clk, fin(18));
p19: entity work.pair_sp generic map ("SPRAM_BE 128x1024", 128, 1024, 10, true, 20, NCYCLES) port map (clk, fin(19));
-- ramw / ramw2
p20: entity work.pair_ramw generic map ("ramw 272x256",  272, 256, 8, true,  21, NCYCLES) port map (clk, clk_x2, fin(20));
p21: entity work.pair_ramw generic map ("ramw 144x32",   144,  32, 5, true,  22, NCYCLES) port map (clk, clk_x2, fin(21));
p22: entity work.pair_ramw generic map ("ramw2 128x256", 128, 256, 8, false, 23, NCYCLES) port map (clk, clk_x2, fin(22));
-- ram2r1w (configuration binds dut_i's DPRAM_BE to ihp with two_port => true)
p23: pair_r2 generic map ("ram2r1w 128x256", 128, 256, 8, 24, NCYCLES) port map (clk, clk_x2, fin(23));
p24: pair_r2 generic map ("ram2r1w 32x1024", 32, 1024, 10, 25, NCYCLES) port map (clk, clk_x2, fin(24));
-- DPRAM_DUAL_CLOCK (afifo): 2-port macros, write clock / read clock unrelated (7/11 ns), reverse (11/7),
-- write = 2x read (clk_x2/clk), read = 2x write (clk/clk_x2); 3x32 is the flop branch
p25: entity work.pair_dc generic map ("DPRAM_DUAL_CLOCK 145x32 w7/r11",  145, 32, 5, 26, NCYCLES) port map (clk7,   clk11,  fin(25));
p26: entity work.pair_dc generic map ("DPRAM_DUAL_CLOCK 64x32 w7/r11",    64, 32, 5, 27, NCYCLES) port map (clk7,   clk11,  fin(26));
p27: entity work.pair_dc generic map ("DPRAM_DUAL_CLOCK 58x32 w7/r11",    58, 32, 5, 28, NCYCLES) port map (clk7,   clk11,  fin(27));
p28: entity work.pair_dc generic map ("DPRAM_DUAL_CLOCK 145x32 w11/r7",  145, 32, 5, 29, NCYCLES) port map (clk11,  clk7,   fin(28));
p29: entity work.pair_dc generic map ("DPRAM_DUAL_CLOCK 145x32 wx2/r1",  145, 32, 5, 30, NCYCLES) port map (clk_x2, clk,    fin(29));
p30: entity work.pair_dc generic map ("DPRAM_DUAL_CLOCK 64x32 wx2/r1",    64, 32, 5, 31, NCYCLES) port map (clk_x2, clk,    fin(30));
p31: entity work.pair_dc generic map ("DPRAM_DUAL_CLOCK 58x32 w1/rx2",    58, 32, 5, 32, NCYCLES) port map (clk,    clk_x2, fin(31));
p32: entity work.pair_dc generic map ("DPRAM_DUAL_CLOCK 3x32 w7/r11 (flops)", 3, 32, 5, 33, NCYCLES) port map (clk7, clk11, fin(32));

-- x2_phase must reproduce the core clock level after every x2 edge
phase_i : entity ihp.x2_phase
   port map (clock_in=>clk, clock_x2_in=>clk_x2, phase_out=>phase);
phase_check: process
begin
   for i in 1 to 8 loop
      wait until rising_edge(clk_x2);
   end loop;
   while not all_fin loop
      wait until rising_edge(clk_x2);
      wait for 1 ns;
      assert phase = clk report "x2_phase: phase /= clock level" severity failure;
   end loop;
   wait;
end process;

end architecture;

-------------------------------------------------------------------------
-- configuration: ram2r1w pairs
-------------------------------------------------------------------------
library golden;
library ihp;
use ihp.ztachip_pkg.all;   -- component DPRAM_BE as declared for ram2r1w

configuration tb_ihp_mem_equiv_cfg of tb_ihp_mem_equiv is
   for sim
      for all : pair_r2
         use entity work.pair_r2(sim);
         for sim
            for gold_i : ram2r1w
               use entity golden.ram2r1w(ram2r1w_behaviour);
            end for;
            for dut_i : ram2r1w
               use entity ihp.ram2r1w(ram2r1w_behaviour);
               for ram2r1w_behaviour
                  for ram2_i : DPRAM_BE
                     use entity ihp.DPRAM_BE(ihp)
                        generic map (numwords_a => numwords_a, numwords_b => numwords_b,
                                     widthad_a => widthad_a, widthad_b => widthad_b,
                                     width_a => width_a, width_b => width_b,
                                     two_port => true);
                  end for;
               end for;
            end for;
         end for;
      end for;
   end for;
end configuration;
