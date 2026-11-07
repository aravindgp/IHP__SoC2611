# DSOC2610 / SoC2611 - H10 detailed route stuck at ~1,400 violations: Metal4 shorts inside SRAM macros (7 Nov 2026)

Same chip and flow as the first pack (IHP SG13CMOS5L, 5 metals M1-M4 + TopMetal1; M2/M4 vertical, M3/TM1 horizontal;
die 6.6 x 6.6 mm; 298 RM_IHPSG13 SRAM macros; 334,600 cells; OpenROAD dcf36133 / TritonRoute 64-pass schedule).

## Where H10 stands
H10 = floorplan H4 + two placement blockages (the dp corridor and the camera slot), which removed the earlier
routing wall. Detailed route history (data/drt_pass_histories.txt): 392k -> 34.5k (pass 3) -> 10.9k (9) -> 4.2k (15)
-> 1.9k (24) -> 1,702 (30) -> 1,608 / 1,550 / 2,008(ripup) / 1,811 / 1,716 / 1,541 / 1,417 (31-37). Flat since pass 30.

## What the residue is (pass 30 snapshot, data/H10_pass30_all_markers_breakdown.txt)
1,826 markers: Short 1,555 + Metal Spacing 271; layers Metal4 1,476, Metal2 203, TopMetal1 106, Metal3 41.
1,222 of the shorts involve VDD/VSS. data/H10_pass30_power_shorts_vs_macros.txt: 1,074 of the 1,166 Metal4 power
shorts lie >= 10 um INSIDE SRAM macro outlines (and all 51 TopMetal1 ones). They are not on the chip PDN straps
(data/H10_power_shorts_mod_strap_grid.txt: no periodicity with the 16 um TM1 strap grid or the 50 um M4 stubs).
430 distinct signal nets carry them (data/H10_nets_with_power_shorts_430.txt).

## Why wires are inside the macros
- The SRAM LEF (data/RM_IHPSG13_2P_1024x32_lef_excerpt.txt) has only a 17 um wide Metal4 OBS strip; the rest of the
  macro's Metal4 is VDD!/VSS!/VDDARRAY! pin stripes (225 rects in the 685 x 385 um macro) with routable gaps. M1-M3
  are obstructed (M2 only outside the south pin row).
- Global routing (FastRoute, `global_route -allow_congestion -congestion_iterations 15`, data/chip_grt.tcl) puts
  guide boxes on Metal4 deep inside macros: data/H10_guides_in_macros_margin-10.txt = 442 Metal4 boxes >= 10 um
  inside, on 498 nets; 186 (net, macro) pairs listed in data/H10_m4_pairs.txt.
- data/H10_net_macro_cross.txt: of the 186 pairs, the net connects to the crossed macro in only 12; 119 nets have
  pins both north and south of the macro -> pass-through nets of logic split by a macro. 265 of the 442 boxes are on
  the two east CPU cache macros (1024x32 at x 4888-5574, y 4359-4744 MX and y 4819-5205 R0, pins facing each
  other across a 75 um strip); the rest on AXI 64x32 FIFOs, PCORE0 register files, dp_sink 256x32.
- The CPU block (data/H10_cpu_block_density_100um.txt, data/H4b_vs_H10_floorplan.png): CPU logic lies north
  (y 5205-5450) and south (y 3900-4359) of the east cache pair; the column east of the pair (x 5634-6160) is closed
  by two 64x22 ibus-tag macros in both rows, so there is no vertical channel east of x 4888; the empty channel
  between the west and east caches (x 4343-4888) is 500+ um away for the east-side nets. FastRoute's 2D router
  overflows the vertical edges over the macros (vertical layers M2/M4 both blocked there; allow_congestion) and layer
  assignment drops those segments on Metal4 inside the macro; TritonRoute then shorts the power pins.

## What was tried on this specific problem (all measured)
1. Metal4 routing obstructions over every macro, then a re-route of the 430 nets on the pass-30 routing
   (data/eco_obs.tcl): 29,241 -> 7,949 -> 8,244 -> 6,221 -> 5,491 -> 5,173 after 5 passes; 3,844 of its shorts
   still >= 10 um inside macros (data/obsA_residue_vs_macros.txt). The detailed router cannot leave the guides.
2. Metal4 obstructions over the macros BEFORE the chip global route (data/macro_obs.tcl + chip_mobs_grt.sh):
   overflow identical to H10 (11,786, per layer identical; M4 resource 6,624,205 vs 6,624,207), guides identical
   (442 boxes): the global router already counted the macro M4 as blocked. data/H10m_grt_table.txt.
3. Metal4 + TopMetal1 obstructions over the macros before the global route: M4 boxes inside 442 -> 62, but
   Metal2 boxes inside 567 -> 1,021 (overflow moved to M2 inside the macros); total overflow 12,329.
   data/H10m3_grt_table.txt, data/H10m3_guides_in_macros.txt.
4. 40 congestion iterations instead of 15 (running at the time of writing; data/H10m2_* if present).
5. Floorplan H11 (running): H10 + the two 64x22 ibus-tag macros moved from x 5634-6160 to x 3360-3886
   (y 4360 MX / 4495 R0) to open a 586 um vertical channel east of the caches; data/H11_cputags.pl,
   data/H11_vs_H10_floorplan.png. Judged by the guides-inside-macros count on its chip guides (< 150) and DRT pass 3.

## Other facts that may matter
- PDN (data/pdn_c5l_sram_v2_header.txt): Metal1 follow-rails, Metal4 vertical straps 1 um at 50 um pitch, TopMetal1
  horizontal straps at 16 um pitch (so TM1 is usable horizontally between straps, never vertically over macros).
- chip_grt.tcl: set_global_routing_layer_adjustment Metal2-TopMetal1 0.05, signal layers Metal2-TopMetal1,
  non-default rules cleared, -allow_congestion, 15 iterations (50 took 3:51 h on an earlier chip).
- Chip-level GRT overflow ~11.8k with -allow_congestion; the macro channels are the saturated part.
- Macro orientations R0/MX only (pdngen cannot connect rotated macros); SRAM signal pins Metal2 on the south edge.

## Questions
1. Is there an OpenROAD global-routing control that forbids overflow INTO zero-capacity (macro) gcells while still
   allowing congestion elsewhere (region adjustments, `set_global_routing_region_adjustment`, capacity, hard
   obstruction semantics, `-critical_nets_percentage`, more iterations, CUGR), so that pass-through nets detour
   around macros?
2. Alternatively, a way to re-route only the ~500 offending nets at the global level (incremental GRT
   `-start_incremental/-end_incremental`, guide editing, or `detailed_route` options) with the macro cells
   forbidden, on top of the finished H10 routing?
3. Is the floorplan move (H11) the right lever, and what rule sizes vertical channels between big macros for
   pass-through demand (channel width vs number of nets straddling the macro)?
4. Anything in the LEF/PDN that we misread: are Metal4 wires between the macro power stripes legitimately
   routable, and if so why does TritonRoute end up on the stripes (pin access / track pitch vs stripe gap)?
