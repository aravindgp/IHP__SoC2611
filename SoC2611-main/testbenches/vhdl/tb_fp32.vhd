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

---
-- Self-checking testbench for the ASIC platform FP32_MUL / FP32_ADDSUB.
--
-- Vectors are generated offline by HW/asic/tb/gen_fp32_vectors.py (exact
-- integer reference, see that file for the semantics) and read from
-- VECTORS (one "<op> <x1> <x2> <y>" hex line per vector, op M/A/S).
--
-- Each DUT is instantiated at every latency in LATENCIES (2 = minimum,
-- 4 = MUL_LATENCY/ADD_LATENCY/SUM_LATENCY used by falu/falu2, 6 = larger).
-- Vectors are streamed back-to-back, one per clock, and every output is
-- checked for an exact 32-bit match exactly LATENCY clocks later (NaN
-- results only require "is NaN").  The testbench ends with
--     FP32 TB: <pass>/<total> passed
-- and raises severity failure if anything mismatched.
---

library std;
use std.standard.all;
use std.textio.all;
use std.env.all;
LIBRARY ieee;
USE ieee.std_logic_1164.all;
use IEEE.numeric_std.all;
use work.ztachip_pkg.all;

entity tb_fp32 is
   generic
   (
      VECTORS      : string := "HW/asic/tb/vectors/fp32_vectors.txt";
      MAX_VECTORS  : natural := 65536;
      MAX_REPORTED : natural := 20
   );
end tb_fp32;

architecture sim of tb_fp32 is

constant LATENCIES : integer_vector := (2, 4, 6);
constant NUM_LAT   : integer := LATENCIES'length;
constant PERIOD    : time := 10 ns;

type vec_array_t is array(natural range <>) of fp32_t;
type op_array_t is array(natural range <>) of std_logic;

type vecset_t is record
   n   : natural;
   x1  : vec_array_t(0 to MAX_VECTORS-1);
   x2  : vec_array_t(0 to MAX_VECTORS-1);
   y   : vec_array_t(0 to MAX_VECTORS-1);
   sub : op_array_t(0 to MAX_VECTORS-1);
end record;

type vecset_ptr_t is access vecset_t;

signal clock   : std_logic := '0';
signal reset   : std_logic := '0';
signal running : boolean := true;

-- Stimulus shared by all DUT instances
signal mul_x1   : fp32_t := (others=>'0');
signal mul_x2   : fp32_t := (others=>'0');
signal mul_exp  : fp32_t := (others=>'0');
signal mul_vld  : std_logic := '0';
signal add_x1   : fp32_t := (others=>'0');
signal add_x2   : fp32_t := (others=>'0');
signal add_sub  : std_logic := '0';
signal add_exp  : fp32_t := (others=>'0');
signal add_vld  : std_logic := '0';
signal stim_idx : integer := 0;

type y_array_t is array(0 to NUM_LAT-1) of fp32_t;
signal mul_y : y_array_t;
signal add_y : y_array_t;

type count_array_t is array(0 to 2*NUM_LAT-1) of natural;
signal pass_cnt : count_array_t := (others=>0);
signal fail_cnt : count_array_t := (others=>0);
signal done_cnt : natural := 0;

function is_nan(v : fp32_t) return boolean is
begin
   return v(30 downto 23) = "11111111" and unsigned(v(22 downto 0)) /= 0;
end function;

function to_hstr(v : fp32_t) return string is
   constant hex : string := "0123456789ABCDEF";
   variable s : string(1 to 8);
begin
   for i in 0 to 7 loop
      s(8-i) := hex(to_integer(unsigned(v(4*i+3 downto 4*i)))+1);
   end loop;
   return s;
end function;

begin

-- Clock
clock <= not clock after PERIOD/2 when running else '0';

------
-- DUTs at each latency
------
lat_g: for g in 0 to NUM_LAT-1 generate

mul_i: FP32_MUL
   generic map(
      LATENCY=>LATENCIES(g)
   )
   port map(
      reset_in=>reset,
      clock_in=>clock,
      x1_in=>mul_x1,
      x2_in=>mul_x2,
      y_out=>mul_y(g)
   );

addsub_i: FP32_ADDSUB
   generic map(
      LATENCY=>LATENCIES(g)
   )
   port map(
      reset_in=>reset,
      clock_in=>clock,
      add_sub_in=>add_sub,
      x1_in=>add_x1,
      x2_in=>add_x2,
      y_out=>add_y(g)
   );

-- Checker: compare each output exactly LATENCY clocks after its stimulus.
-- Stimulus changes just after falling edge k and is sampled by the DUT at
-- rising edge k+1, so at falling edge k+LATENCY the DUT output corresponds
-- to the stimulus applied at falling edge k.  A queue of depth LATENCY
-- (entries 0..L-1, captured at each falling edge) holds the expectations;
-- entry L-1 is the one due at the current falling edge.
check_p: process
   constant L : integer := LATENCIES(g);
   variable mul_q_exp : vec_array_t(0 to L-1);
   variable mul_q_vld : std_logic_vector(0 to L-1);
   variable add_q_exp : vec_array_t(0 to L-1);
   variable add_q_vld : std_logic_vector(0 to L-1);
   variable ok : boolean;
   variable npass_m, nfail_m, npass_a, nfail_a : natural;
begin
   mul_q_vld := (others=>'0');
   add_q_vld := (others=>'0');
   npass_m := 0; nfail_m := 0; npass_a := 0; nfail_a := 0;
   wait until reset='1';
   while running loop
      wait until falling_edge(clock);
      -- Check what is due now (entry L-1 of the queue = stimulus from L falling edges ago)
      if mul_q_vld(L-1)='1' then
         if is_nan(mul_q_exp(L-1)) then
            ok := is_nan(mul_y(g));
         else
            ok := (mul_y(g) = mul_q_exp(L-1));
         end if;
         if ok then
            npass_m := npass_m+1;
         else
            nfail_m := nfail_m+1;
            if nfail_m+nfail_a <= MAX_REPORTED then
               report "FP32_MUL LATENCY=" & integer'image(L) &
                      " mismatch (MUL vector index " & integer'image(stim_idx+1-L) & ")" &
                      " got=" & to_hstr(mul_y(g)) & " expected=" & to_hstr(mul_q_exp(L-1))
                      severity error;
            end if;
         end if;
      end if;
      if add_q_vld(L-1)='1' then
         if is_nan(add_q_exp(L-1)) then
            ok := is_nan(add_y(g));
         else
            ok := (add_y(g) = add_q_exp(L-1));
         end if;
         if ok then
            npass_a := npass_a+1;
         else
            nfail_a := nfail_a+1;
            if nfail_m+nfail_a <= MAX_REPORTED then
               report "FP32_ADDSUB LATENCY=" & integer'image(L) &
                      " mismatch (ADDSUB vector index " & integer'image(stim_idx+1-L) & ")" &
                      " got=" & to_hstr(add_y(g)) & " expected=" & to_hstr(add_q_exp(L-1))
                      severity error;
            end if;
         end if;
      end if;
      -- Shift the expectation queues and capture the stimulus that the
      -- driver presents right after this falling edge (delta-cycle later),
      -- so sample on the next delta via a tiny wait.
      wait for 0 ns;
      wait for 0 ns;
      for i in L-1 downto 1 loop
         mul_q_exp(i) := mul_q_exp(i-1);
         mul_q_vld(i) := mul_q_vld(i-1);
         add_q_exp(i) := add_q_exp(i-1);
         add_q_vld(i) := add_q_vld(i-1);
      end loop;
      mul_q_exp(0) := mul_exp;
      mul_q_vld(0) := mul_vld;
      add_q_exp(0) := add_exp;
      add_q_vld(0) := add_vld;
      pass_cnt(2*g) <= npass_m;
      fail_cnt(2*g) <= nfail_m;
      pass_cnt(2*g+1) <= npass_a;
      fail_cnt(2*g+1) <= nfail_a;
   end loop;
   wait;
end process;

end generate lat_g;

------
-- Stimulus: load vectors, apply one per clock on the falling edge
------
stim_p: process
   variable mulv  : vecset_ptr_t;
   variable addv  : vecset_ptr_t;
   file     f     : text;
   variable l     : line;
   variable op    : character;
   variable sp    : character;
   variable x1v, x2v, yv : std_logic_vector(31 downto 0);
   variable good  : boolean;
   variable nline : natural := 0;
   variable total : natural;
   variable npass : natural;
   variable nfail : natural;
   variable i     : natural;
begin
   mulv := new vecset_t;
   addv := new vecset_t;
   mulv.n := 0;
   addv.n := 0;
   file_open(f, VECTORS, read_mode);
   while not endfile(f) loop
      readline(f, l);
      nline := nline+1;
      if l'length = 0 or l(l'left) = '#' then
         next;
      end if;
      read(l, op, good);
      assert good report "vector file line " & integer'image(nline) & ": bad op" severity failure;
      read(l, sp, good);
      hread(l, x1v, good);
      assert good report "vector file line " & integer'image(nline) & ": bad x1" severity failure;
      hread(l, x2v, good);
      assert good report "vector file line " & integer'image(nline) & ": bad x2" severity failure;
      hread(l, yv, good);
      assert good report "vector file line " & integer'image(nline) & ": bad y" severity failure;
      if op = 'M' then
         assert mulv.n < MAX_VECTORS report "too many MUL vectors" severity failure;
         mulv.x1(mulv.n) := x1v;
         mulv.x2(mulv.n) := x2v;
         mulv.y(mulv.n) := yv;
         mulv.n := mulv.n+1;
      elsif op = 'A' or op = 'S' then
         assert addv.n < MAX_VECTORS report "too many ADDSUB vectors" severity failure;
         addv.x1(addv.n) := x1v;
         addv.x2(addv.n) := x2v;
         addv.y(addv.n) := yv;
         if op = 'S' then
            addv.sub(addv.n) := '1';
         else
            addv.sub(addv.n) := '0';
         end if;
         addv.n := addv.n+1;
      else
         report "vector file line " & integer'image(nline) & ": unknown op '" & op & "'" severity failure;
      end if;
   end loop;
   file_close(f);
   report "loaded " & integer'image(mulv.n) & " MUL and " & integer'image(addv.n) &
          " ADDSUB vectors from " & VECTORS;
   assert mulv.n > 0 and addv.n > 0 report "no vectors loaded" severity failure;

   -- Reset (asynchronous, active low)
   reset <= '0';
   wait for 3*PERIOD;
   wait until falling_edge(clock);
   reset <= '1';

   -- Stream vectors: one new operand pair per clock, both DUT kinds in parallel
   total := mulv.n;
   if addv.n > total then
      total := addv.n;
   end if;
   i := 0;
   while i < total + 8 loop       -- +8 idle cycles to flush the deepest pipeline
      wait until falling_edge(clock);
      stim_idx <= i;
      if i < mulv.n then
         mul_x1 <= mulv.x1(i);
         mul_x2 <= mulv.x2(i);
         mul_exp <= mulv.y(i);
         mul_vld <= '1';
      else
         -- Keep driving something non-trivial while idle
         mul_x1 <= x"7FC00000";
         mul_x2 <= x"00000000";
         mul_exp <= (others=>'0');
         mul_vld <= '0';
      end if;
      if i < addv.n then
         add_x1 <= addv.x1(i);
         add_x2 <= addv.x2(i);
         add_sub <= addv.sub(i);
         add_exp <= addv.y(i);
         add_vld <= '1';
      else
         add_x1 <= x"7F800000";
         add_x2 <= x"7F800000";
         add_sub <= '1';
         add_exp <= (others=>'0');
         add_vld <= '0';
      end if;
      i := i+1;
   end loop;
   -- Wait for the last checks to land, then stop the clock
   for k in 1 to 4 loop
      wait until falling_edge(clock);
   end loop;
   wait for 1 ns;

   npass := 0;
   nfail := 0;
   for k in 0 to NUM_LAT-1 loop
      report "FP32_MUL    LATENCY=" & integer'image(LATENCIES(k)) & ": " &
             integer'image(pass_cnt(2*k)) & " passed, " & integer'image(fail_cnt(2*k)) & " failed";
      report "FP32_ADDSUB LATENCY=" & integer'image(LATENCIES(k)) & ": " &
             integer'image(pass_cnt(2*k+1)) & " passed, " & integer'image(fail_cnt(2*k+1)) & " failed";
      npass := npass + pass_cnt(2*k) + pass_cnt(2*k+1);
      nfail := nfail + fail_cnt(2*k) + fail_cnt(2*k+1);
   end loop;
   -- Every vector must have been checked once per latency
   assert npass + nfail = NUM_LAT*(mulv.n + addv.n)
      report "FP32 TB: checked " & integer'image(npass+nfail) & " results but expected " &
             integer'image(NUM_LAT*(mulv.n+addv.n)) severity failure;
   report "FP32 TB: " & integer'image(npass) & "/" & integer'image(npass+nfail) & " passed";
   assert nfail = 0 report "FP32 TB: " & integer'image(nfail) & " MISMATCHES" severity failure;
   running <= false;
   wait for PERIOD;
   finish;
   wait;
end process;

end sim;
