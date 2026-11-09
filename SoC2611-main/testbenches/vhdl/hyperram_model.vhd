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
-- Behavioural HyperRAM model (HyperBus 1.0, S27KL0641-class, simulation only).
--
-- One device: MEM_BYTES of storage (default 8 MB = 64 Mbit), optionally
-- preloaded from an Intel HEX file (byte addresses relative to this
-- device, parser copied from HW/simulation/mem128.vhd).
--
-- Protocol (see hyperbus_core.vhd for the same formulas on the host side):
--  * CS# low with CK low starts a transaction. The 48-bit CA is captured on
--    the first 3 CK periods (CA[47:40] on the rising edge, CA[39:32] on the
--    falling edge, ...). While CS# is low and until the end of the CA the
--    model drives RWDS: high = 2x latency (always when FIXED_LATENCY, else
--    for every 4th transaction to emulate refresh collisions), low = 1x.
--  * Latency count = INITIAL_LATENCY CK periods (CR0[7:4] after a register
--    write) starting at the falling edge that captures CA[23:16]; the first
--    data byte is on CK rising edge index 2 + L*m (m = 1 or 2), index 0
--    being the edge that captured CA[47:40].
--  * Reads: after the latency the model drives DQ and RWDS edge aligned
--    (one byte per edge, RWDS high for the first byte of a 16-bit word),
--    TCKD_PS after every CK edge, until CS# rises. Linear burst, wraps at
--    MEM_BYTES.
--  * Writes: after the latency DQ and RWDS are sampled on every CK edge;
--    RWDS = '1' masks the byte.
--  * Register space (CA[46]=1): zero-latency write of CR0 (word address
--    0x1000: latency code CR0[7:4], fixed-latency CR0[3]) and reads of
--    ID0/CR0 with the normal latency. Other registers read as 0.
--  * Checks (error_out is sticky): CS# low longer than tCSM = 4 us
--    (TCSM_CHECK), a transaction before RESET# has been high for TVCS_NS ns
--    (or while RESET# is low), RESET# pulse shorter than tRP = 200 ns,
--    wrapped bursts (unsupported), CK not low at CS# fall.
--
-- Byte order: the first byte of a 16-bit word on the bus (RWDS high during
-- a read) is the byte at the even (lower) address.
----------

library std;
use std.standard.all;
use std.textio.all;
LIBRARY ieee;
USE ieee.std_logic_1164.all;
use IEEE.numeric_std.all;

entity hyperram_model is
   generic
   (
      MEM_BYTES       : natural := 8388608;
      INITIAL_LATENCY : natural := 6;
      FIXED_LATENCY   : boolean := true;
      HEX_FILE        : string  := "";
      TCSM_CHECK      : boolean := true;
      TVCS_NS         : natural := 150000;
      TCKD_PS         : natural := 2000;      -- CK edge to DQ/RWDS output delay
      NAME            : string  := "hyperram"
   );
   port
   (
      ck        : in  std_logic;
      ckn       : in  std_logic;   -- unused (CK# is the complement of CK)
      csn       : in  std_logic;
      resetn    : in  std_logic;
      rwds_i    : in  std_logic;
      rwds_o    : out std_logic;
      rwds_oe   : out std_logic;
      dq_i      : in  std_logic_vector(7 downto 0);
      dq_o      : out std_logic_vector(7 downto 0);
      dq_oe     : out std_logic;
      error_out : out std_logic    -- sticky: any protocol/timing violation
   );
end hyperram_model;

architecture sim of hyperram_model is

constant TCSM  : time := 4 us;
constant TRP   : time := 200 ns;
constant TVCS  : time := TVCS_NS * 1 ns;
constant TCKD  : time := TCKD_PS * 1 ps;

type mem_t is array(0 to MEM_BYTES-1) of std_logic_vector(7 downto 0);

-- the storage is a shared variable (static allocation): an 8 MB array must
-- not live on a process/function stack (GHDL segfaults on a 64 MB stack object)
shared variable mem_v : mem_t;

procedure InitRamFromFile (RamFileName : in string) is
file cmdfile: TEXT;
variable line_in:Line;
variable curraddr_v:integer;
variable baseaddr_v:integer;
variable SC_v:character;
variable LEN_v:std_logic_vector(7 downto 0);
variable ADDR_v:std_logic_vector(15 downto 0);
variable TYPE_v:std_logic_vector(7 downto 0);
variable DATA_v:std_logic_vector(7 downto 0);
variable CHECKSUM_v:std_logic_vector(7 downto 0);
variable baddr16_v:std_logic_vector(15 downto 0);
variable baddr32_v:std_logic_vector(31 downto 0);
begin
   baseaddr_v := 0;
   for i in 0 to MEM_BYTES-1 loop
      mem_v(i) := (others=>'0');
   end loop;
   if RamFileName'length = 0 then
      return;
   end if;
   FILE_OPEN(cmdfile,RamFileName,READ_MODE);
   loop
      if endfile(cmdfile) then
         return;
      end if;
      readline(cmdfile,line_in);
      read(line_in,SC_v);
      hread(line_in,LEN_v);
      hread(line_in,ADDR_v);
      hread(line_in,TYPE_v);
      case to_integer(unsigned(TYPE_v)) is
         when 0 => -- DATA
            curraddr_v := baseaddr_v+to_integer(unsigned(ADDR_v));
            for I in 0 to to_integer(unsigned(LEN_v))-1 loop
               hread(line_in,DATA_v);
               if curraddr_v < MEM_BYTES then
                  mem_v(curraddr_v) := DATA_v;
               end if;
               curraddr_v := curraddr_v+1;
            end loop;
            hread(line_in,CHECKSUM_v);
         when 1 => -- EOF
            return;
         when 2 => -- Extended Segment Address
            hread(line_in,baddr16_v);
            baseaddr_v := to_integer(unsigned(baddr16_v))*16;
         when 3 => -- Start Segment Address
         when 4 => -- Extended linear address
            hread(line_in,baddr16_v);
            baseaddr_v := to_integer(unsigned(baddr16_v))*65536;
         when 5 => -- Start linear address
            hread(line_in,baddr32_v);
            baseaddr_v := to_integer(unsigned(baddr32_v));
         when others =>
      end case;
   end loop;
end procedure;

signal err_main   : std_logic := '0';
signal err_tcsm   : std_logic := '0';
signal err_reset  : std_logic := '0';
signal t_reset_hi : time := 0 ns;      -- time RESET# last rose
signal reset_seen : boolean := false;  -- RESET# has risen at least once

begin

error_out <= err_main or err_tcsm or err_reset;

----
-- RESET# timing: tRP pulse width, remember the release time for tVCS
----
reset_mon : process
variable t_low : time;
begin
   wait until resetn'event;
   if resetn = '0' then
      t_low := now;
      wait until resetn'event;
      if resetn = '1' then
         if now - t_low < TRP and now > 0 ns and t_low > 0 ns then
            report NAME & ": RESET# pulse " & time'image(now - t_low) & " shorter than tRP (200 ns)" severity error;
            err_reset <= '1';
         end if;
         t_reset_hi <= now;
         reset_seen <= true;
      end if;
   end if;
end process;

----
-- tCSM: CS# must not stay low longer than 4 us
----
tcsm_mon : process
begin
   wait until csn = '0';
   wait until csn = '1' for TCSM;
   if csn /= '1' and TCSM_CHECK then
      report NAME & ": CS# low longer than tCSM (4 us)" severity error;
      err_tcsm <= '1';
      wait until csn = '1';
   end if;
end process;

----
-- transaction engine
----
main : process
variable loaded_v  : boolean := false;
variable cr0_v     : std_logic_vector(15 downto 0) := x"8F1F"; -- power-up: fixed 2x latency, 6 clocks
variable ca_v      : std_logic_vector(47 downto 0);
variable txn_cnt_v : natural := 0;
variable lat2x_v   : boolean;
variable lat_v     : natural;
variable is_read_v : boolean;
variable reg_v     : boolean;
variable waddr_v   : unsigned(31 downto 0);
variable baddr_v   : natural;
variable word_v    : std_logic_vector(15 downto 0);
variable nskip_v   : natural;
variable aborted_v : boolean;

-- latency code CR0[7:4] -> clocks (S27KL0641 table)
function lat_clocks(code : std_logic_vector(3 downto 0)) return natural is
begin
   case code is
      when "0000" => return 5;
      when "0001" => return 6;
      when "0010" => return 7;
      when "1110" => return 3;
      when "1111" => return 4;
      when others => return 6;
   end case;
end function;

-- wait for the next CK rising (rise=true) or falling edge; returns with
-- aborted=true if CS# rises first
procedure wait_edge(rise : in boolean; aborted : out boolean) is
begin
   aborted := false;
   loop
      wait until ck'event or csn'event;
      if csn = '1' then
         aborted := true;
         return;
      end if;
      if ck'event then
         if rise and To_X01(ck) = '1' then
            return;
         end if;
         if (not rise) and To_X01(ck) = '0' then
            return;
         end if;
      end if;
   end loop;
end procedure;

begin
   if not loaded_v then
      InitRamFromFile(HEX_FILE);
      loaded_v := true;
   end if;
   dq_oe <= '0';
   dq_o <= (others=>'0');
   rwds_oe <= '0';
   rwds_o <= '0';

   wait until csn = '0';

   -- start-up checks
   if resetn /= '1' then
      report NAME & ": transaction while RESET# is low" severity error;
      err_main <= '1';
   elsif (not reset_seen) or (now - t_reset_hi < TVCS) then
      report NAME & ": transaction before tVCS (" & integer'image(TVCS_NS) & " ns after RESET# high)" severity error;
      err_main <= '1';
   end if;
   if To_X01(ck) /= '0' then
      report NAME & ": CS# fell while CK was not low" severity error;
      err_main <= '1';
   end if;

   -- latency indication on RWDS during the CA
   txn_cnt_v := txn_cnt_v + 1;
   if FIXED_LATENCY or cr0_v(3) = '1' then
      lat2x_v := true;
   else
      lat2x_v := (txn_cnt_v mod 4) = 0;
   end if;
   if FIXED_LATENCY then
      lat_v := INITIAL_LATENCY;
   else
      lat_v := lat_clocks(cr0_v(7 downto 4));
   end if;
   rwds_oe <= '1' after TCKD;
   if lat2x_v then
      rwds_o <= '1' after TCKD;
   else
      rwds_o <= '0' after TCKD;
   end if;

   -- Command/Address: 6 bytes on 3 CK periods
   aborted_v := false;
   for i in 0 to 5 loop
      wait_edge((i mod 2) = 0, aborted_v);
      exit when aborted_v;
      ca_v(47-8*i downto 40-8*i) := To_X01(dq_i);
   end loop;

   if not aborted_v then
      is_read_v := ca_v(47) = '1';
      reg_v := ca_v(46) = '1';
      if ca_v(45) = '0' then
         report NAME & ": wrapped burst not supported by this model" severity error;
         err_main <= '1';
      end if;
      waddr_v := unsigned(ca_v(44 downto 16)) & unsigned(ca_v(2 downto 0));

      if is_read_v then
         rwds_o <= '0' after TCKD;                 -- keep driving RWDS (low) through the latency
      else
         rwds_oe <= '0' after TCKD;                -- release RWDS to the master
      end if;

      if reg_v and not is_read_v then
         -- zero-latency register write: one 16-bit word right after the CA
         wait_edge(true, aborted_v);
         if not aborted_v then
            word_v(15 downto 8) := To_X01(dq_i);
            wait_edge(false, aborted_v);
         end if;
         if not aborted_v then
            word_v(7 downto 0) := To_X01(dq_i);
            if waddr_v = x"00001000" then
               cr0_v := word_v;
               report NAME & ": CR0 <= 0x" & to_hstring(word_v) severity note;
            end if;
         end if;
      else
         -- initial latency: first data byte on CK rising edge index 2 + lat*m;
         -- rising edges 0..2 were consumed by the CA, skip the rest
         if lat2x_v then
            nskip_v := 2*lat_v - 1;
         else
            nskip_v := lat_v - 1;
         end if;
         for i in 1 to nskip_v loop
            wait_edge(true, aborted_v);
            exit when aborted_v;
         end loop;

         baddr_v := to_integer(waddr_v(30 downto 0) & '0') mod MEM_BYTES;
         while not aborted_v loop
            -- byte A (rising edge)
            wait_edge(true, aborted_v);
            exit when aborted_v;
            if is_read_v then
               if reg_v then
                  if waddr_v = x"00000000" then
                     word_v := x"0C81";                     -- ID0: S27KL0641-like
                  elsif waddr_v = x"00001000" then
                     word_v := cr0_v;
                  else
                     word_v := (others=>'0');
                  end if;
                  dq_o <= word_v(15 downto 8) after TCKD;
               else
                  dq_o <= mem_v(baddr_v) after TCKD;
               end if;
               dq_oe <= '1' after TCKD;
               rwds_o <= '1' after TCKD;
            else
               if To_X01(rwds_i) = '0' then
                  mem_v(baddr_v) := To_X01(dq_i);
               end if;
            end if;
            -- byte B (falling edge)
            wait_edge(false, aborted_v);
            exit when aborted_v;
            if is_read_v then
               if reg_v then
                  dq_o <= word_v(7 downto 0) after TCKD;
               else
                  dq_o <= mem_v((baddr_v+1) mod MEM_BYTES) after TCKD;
               end if;
               rwds_o <= '0' after TCKD;
            else
               if To_X01(rwds_i) = '0' then
                  mem_v((baddr_v+1) mod MEM_BYTES) := To_X01(dq_i);
               end if;
            end if;
            baddr_v := (baddr_v + 2) mod MEM_BYTES;
         end loop;
      end if;
   end if;

   -- CS# high: release the bus
   if csn /= '1' then
      wait until csn = '1';
   end if;
   dq_oe <= '0' after TCKD;
   rwds_oe <= '0' after TCKD;
   rwds_o <= '0' after TCKD;
end process;

end sim;
