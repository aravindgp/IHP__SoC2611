------------------------------------------------------------------------------
-- Prints the IHP macro tiling that ihp_sram_pkg.tile_plan picks for the
-- SoC2611 memory inventory (HW/asic/dgse/inventory_8pcore_camera.md,
-- natural geometries) together with the macro area, as a markdown table.
-- Elaboration-only: no clocks, no simulation time.
--
--   ghdl -a --std=08 HW/platform/ihp/ihp_sram_pkg.vhd HW/asic/tb/tb_ihp_plan.vhd
--   ghdl -e --std=08 tb_ihp_plan && ghdl -r --std=08 tb_ihp_plan
------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use work.ihp_sram_pkg.all;

entity tb_ihp_plan is
end entity;

architecture sim of tb_ihp_plan is

   type row_t is record
      prim    : string(1 to 8);
      width   : natural;
      depth   : natural;
      inst    : natural;
      ports   : natural;
      with_bm : boolean;
   end record;
   type rows_t is array (natural range <>) of row_t;
   constant rows_c : rows_t := (
      ("DPRAM_BE", 272,  256,  8, 1, true ),   -- ramw 136x512 natural geometry (xregister_file)
      ("DPRAM_BE", 128,  256, 16, 2, true ),   -- ram2r1w, two_port (register_file)
      ("SPRAM   ",  24,  512, 16, 1, false),
      ("SPRAM_BE", 128, 1024,  1, 1, true ),
      ("DPRAM_BE",  64, 1024,  2, 1, true ),
      ("DPRAM   ", 133,  256,  3, 1, false),
      ("DPRAM   ", 380,  256,  1, 1, false),
      ("DPRAM   ",  64,  256,  5, 1, false),
      ("DPRAM_BE",  72,   64,  8, 1, true ),   -- ramw 72x64 as instantiated (natural 144x32 -> flops)
      ("DPRAM   ", 132,  256,  1, 1, false),
      ("DPRAM_BE",  32, 1024,  1, 2, true ),   -- ram2r1w, two_port (tcm)
      ("DPRAM   ",  73,  256,  1, 1, false),
      ("DPRAM   ",  67,  256,  1, 1, false),
      ("DPRAM   ", 132,  128,  1, 1, false),
      ("DPRAM   ",  58,  256,  1, 1, false),
      ("DPRAM   ",  58,   64,  2, 1, false),
      ("DPRAM   ",  35,  128,  1, 1, false)
   );

   function slices_str(p : plan_t; ports : natural) return string is
      -- "4 x RM_..._256x64_c2_bm_bist + 1 x RM_..._256x16_c2_bm_bist"
      variable done : integer_vector(0 to max_slices_c-1) := (others => 0);
      variable cnt  : natural;
      variable s    : string(1 to 400) := (others => ' ');
      variable n    : natural := 0;
      procedure app(x : string) is
      begin
         s(n+1 to n+x'length) := x;
         n := n + x'length;
      end procedure;
   begin
      for i in 0 to p.nslices-1 loop
         if done(i) = 0 then
            cnt := 0;
            for j in i to p.nslices-1 loop
               if p.slice_w(j) = p.slice_w(i) then
                  cnt := cnt + 1;
                  done(j) := 1;
               end if;
            end loop;
            if n > 0 then app(" + "); end if;
            app(integer'image(cnt) & " x `" & macro_name(ports, p.class, p.slice_w(i)) & "`");
         end if;
      end loop;
      return s(1 to n);
   end function;

   function mm2(um2 : natural) return string is
      variable whole : natural := um2 / 1000000;
      variable frac  : natural := (um2 mod 1000000) / 1000;   -- 3 decimals
      variable f     : string(1 to 3);
   begin
      f := integer'image(frac + 1000)(2 to 4);
      return integer'image(whole) & "." & f;
   end function;

begin

   process
      variable p         : plan_t;
      variable tot_area  : natural := 0;
      variable tot_macro : natural := 0;
      variable nmac      : natural;
   begin
      report "IHP macro plan (ihp_sram_pkg.tile_plan)";
      report "| Primitive | W x D | Inst | Macros/inst | Area/inst (mm2) | Total (mm2) |";
      report "|---|---:|---:|---|---:|---:|";
      for i in rows_c'range loop
         p := tile_plan(rows_c(i).ports, rows_c(i).width, rows_c(i).depth, rows_c(i).with_bm);
         nmac := p.nbanks * p.nslices;
         tot_area  := tot_area + p.area * rows_c(i).inst;
         tot_macro := tot_macro + nmac * rows_c(i).inst;
         report "| `" & rows_c(i).prim & "` | " & integer'image(rows_c(i).width) & "x" & integer'image(rows_c(i).depth) &
                " | " & integer'image(rows_c(i).inst) & " | " & integer'image(p.nbanks) & " bank x (" &
                slices_str(p, rows_c(i).ports) & ") | " & mm2(p.area) & " | " & mm2(p.area * rows_c(i).inst) & " |";
      end loop;
      report "| **total** | | | **" & integer'image(tot_macro) & " macros** | | **" & mm2(tot_area) & " mm2** |";
      wait;
   end process;

end architecture;
