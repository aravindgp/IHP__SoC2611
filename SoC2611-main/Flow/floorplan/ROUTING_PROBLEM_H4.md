# DSOC2610 / SoC2611 - detailed-routing closure problem (7 Nov 2026)

## Chip
- IHP SG13CMOS5L (130 nm, 5 metal: Metal1-4 + TopMetal1; M2/M4/TM1 vertical, M3 horizontal), die 6600 x 6600 um,
  core 340..6260 um, QFN64, 64 IO cells. OpenROAD dcf36133 (Feb 2026) flow (DGSE), KLayout signoff.
- 298 RM_IHPSG13 SRAM macros (12.9 mm2, all signal pins on the SOUTH edge of the macro in R0, Metal2; macro OBS
  Metal1-4), 334,600 standard cells (7.0 mm2, 49 % core density). Four PCORE compute blocks with register-file
  SRAMs, a datapath block (dp_1_i/dp0_i: dp_gen_core, dp_fetch, dp_sink/source FIFOs), AXI merge/split block,
  VexRiscv CPU with caches/TCM, camera FIFOs, ztachip instruction/data memories.
- Hand floorplan "H4" (data/H4_axi3.pl: macro name, lower-left x y in um, orientation; data/macros_name_w_h_um.txt:
  sizes): macro rows grouped by owner block, pin rows facing a standard-cell strip (60-120 um) across which the
  pins are accessed, 180 um "highway" columns between macro columns, every macro >= 100 um from the pad ring.
  Pictures: data/H2_plan.png (floorplan), data/H4_drt_pass6_map.png, data/H4b_drt_pass21_map.png (violation maps).

## Flow to the detailed route
global placement (RePlAce, density 0.6) -> repair -> detailed placement (1-site padding) -> CTS -> global route
(15 congestion iterations; total overflow H4 = 9,520 core / 10,166 chip) -> pads + pad-to-core power straps added,
IO-band obstructions, guides clamped -> TritonRoute detailed route, 64-pass schedule (data/drt_steps.tcl lists the
schedule: pass 10 doubles the DRC cost, 17/25/33/41/49/57 are full rip-up passes, 18+ / 26+ / 34+ ... raise the
costs and maze iterations). Snapshots drt_iter<N>.odb are written after each pass. 32 cores, 128 GB.

## The problem
The detailed route converges everywhere except one place. Pass histories (data/drt_pass_histories.txt):

| run | floorplan | pass 3 | pass 9 | pass 15 | pass 21 | note |
|---|---|---|---|---|---|---|
| drtH4b | H4 | 40,601 | 15,830 | 8,728 | 4,924 | 61 % of the residue is ONE 600 um window |
| drtH10 | H4 + 2 placement blockages | 34,522 | 10,916 | 4,173 | - | residue scattered, no wall |

drtH4b's residue at pass 21 (data/H4b_grid21_600um.log = markers per 600 um window; data/H4b_zoom21_150um.log =
150 um windows around the hot spot): 5,088 markers, 3,091 of them in the window x 2740-3340 / y 1540-2140, and
inside it three 150 um cells x 3040-3340 / y 1840-2140 hold 1,201 / 1,156 / 723. The rest of the chip: 2,000
markers spread over windows of at most 358. The wall decays only ~8 % per pass (9,364 at pass 3, 6,746 at pass 9,
4,979 at pass 15, 3,091 at pass 21) while everything else decays 10-60 % per pass.

What the wall is (data/H4b_wall_window_pass21_breakdown.txt, data/H4b_wall_top_nets_pass21.txt, first 400 lines of
the window's DRC report in data/H4b_wall_window_pass21_first400lines.rpt):
- Short 80 %, Metal Spacing 20 %; Metal2 ~58 %, Metal3 ~32 %, Metal4 ~10 %; ~900 distinct nets, the worst with
  40-100 shorts each; 73 % datapath nets (dp_gen_core / dp_fetch buffer-tree nets "netNNNN", high-fanout nets),
  the rest PCORE / clock / reset.
- Geometry: a 180 um wide standard-cell corridor (x 3120-3300) between the datapath 64x16 / 256x8 macro column
  (x 2883-3120, macro OBS M1-M4) and the instruction-memory macro column (x 3300-3716, y 1425-1955); above
  y 1955 the corridor's east side is an open slot (x 3300-3900, y 1955-2140) that the camera FIFO macros used to
  occupy before they were moved, and above y 2140 the AXI macro block starts.
- The global placer put a dp_gen_core logic cluster into the corridor + slot: 1,633 cells in the corridor
  (x 3120-3300, y 1850-2200), 2,386 cells in the slot (794 of them dp_gen_core/dp_fetch/dp_source). Their nets are
  mostly internal to the cluster (corridor cells: 5,397 pins inside, 851 west, 475 east; slot dp cells: 2,832 inside,
  575 to the corridor, 280 east, 253 west; data/H4_corridor_slot_connectivity.txt, data/H4_slot_cells.txt).
  Cell density there is ordinary (43-50 %; data/H4_density_corridor_100um.txt). The global router does not flag the
  area at all (overflow elsewhere). The wall is a detailed-routing phenomenon: too much Metal2/Metal3 wiring of
  one cluster inside a macro-bounded 180 um corridor.

## What was tried (all measured; details in data/NOTES_5-7Nov_excerpt.md)
1. Re-placements of the same floorplan (new global placement each time):
   - H5: cell blockage on the slot -> cluster pushed INTO the corridor; GRT 11.7k; not routed.
   - H6: camera macros put back into the slot -> GRT 15.4k; not routed.
   - H7: 2 sites of detailed-placement padding on every dp_gen_core cell -> GRT 9.2k; DRT wall 8,336 at pass 3
     (H4: 9,364) -> no real change.
   - H9: hard placement blockage on the corridor (x 3120-3300, y 1400-2300) -> DRT pass 3 = 35,722.
   - **H10: blockage on the corridor AND the slot (data/H10_place_blockages.txt)** -> DRT pass 3 = 34,522, the wall
     window is gone (< 1,400; all windows < 2,300 at pass 3, < 530 at pass 12), passes 9/15 = 10,916 / 4,173,
     converging ~8-9 % per pass on 16 threads. This is the current best candidate, but it restarted from pass 0 and
     is still 40+ passes from zero at the present rate.
2. Post-CTS local moves + full re-route (L1 corridor cleared by DPL, L3 corridor + slot cleared, L7 corridor + slot
   cells shifted 900 um east): every one made the global route 1.3x-5x worse (DPL legalizes to the nearest sites,
   so the cleared region becomes a dense ring; the shifted cluster overloads the band it lands in).
3. ECO on the routed snapshot (data/eco_plain.tcl, data/eco_move.tcl): deleting the routing of selected nets and
   running a plain detailed_route keeps the other wires and re-routes the deleted nets (10 nets: fine). Moving the
   1,666 corridor cells 700 um east and re-routing the 3,410 nets that touch displaced cells: 308k violations after
   the initial route, 286k after 3 passes - the restarted low-cost passes cannot clean an initial route made inside
   finished routing. A step-session resume (TritonRoute single-step API) does nothing on snapshot databases.
4. Plain resume of the router on a snapshot (schedule restarts at pass 0 on the routed wires): works but converges at
   only 2-3 % per pass because the early passes have low marker costs.

## Constraints
- Routing layers fixed (5 metals, TM1 used by the power straps, pitch 3.28 um of TM1 straps); SRAM pins are Metal2 on
  the south edge only; macro orientations R0/MX/MY/R180 only.
- No timing-driven requirement for this run beyond hold documentation; area and floorplan may change.
- Time: final GDS wanted within days (IHP MPW slot, 20 Nov ask). One machine: 32 cores, 128 GB.

## Questions
1. Fastest way to close drtH4b's wall (3 x 150 um cells, ~900 nets, M2/M3 shorts of one logic cluster in a
   macro-bounded corridor) WITHOUT restarting the whole route: a targeted ECO sequence (which nets to rip, which
   TritonRoute controls/costs for the re-route, region-limited re-routing, layer or track adjustments in the
   corridor only), or a local placement edit that the router can absorb?
2. For H10 (wall-free, scattered residue of ~4,000 falling 8-9 % per pass): TritonRoute settings or schedule changes
   (-droute_end_iter, costs, clip size, repair modes, via rules) that accelerate the tail from ~4k to 0?
3. Floorplan-level: a rule to avoid logic clusters in macro-bounded corridors for the next run (corridor width vs
   cluster size, placement blockages, cell padding on specific modules, macro halo), and whether the 180 um
   highways should carry cells at all.
4. Anything in the data that points to a different root cause (power straps, pin-access, guide clamping, via rules).
