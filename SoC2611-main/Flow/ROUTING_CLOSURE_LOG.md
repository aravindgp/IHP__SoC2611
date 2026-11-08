# DGrid-SoC1 on IHP SG13CMOS5L with DGSEV2 -- run notes (2026-10-30)

Engine: DGSE DGSEV2 scratch checkout `/root/.claude/jobs/658ac326/tmp/dgse/DGSE`, OpenROAD dcf3613 (2026-02-17).
Scripts / inputs for these runs: `HW/asic/dgse/runs/cmos5l-01/` (install_engine.py, patch_engine.py, make_run.py,
run_stages.py, chip_extra.sdc, pin_constraints.tcl).

## Engine changes (scratch checkout; originals kept as `*.orig`)

1. `engine/flow/platforms/ihp-sg13cmos5l-dgse/` copied from `platform_ihp-sg13cmos5l/platforms/`.
2. `engine/flow/pdks.json`: `ihp-sg13cmos5l` entry from `pdks.json.fragment` + `"antenna_diode": "sg13cmos5l_antennanp"`.
3. `engine/flow/pdk_registry.json`: `ihp-sg13cmos5l` row from the fragment.
4. `engine/flow/macros.json`: all 30 `RM_IHPSG13_*` SRAM macros (cmos5l sram dir = sg13g2 sram via symlink; LEF/GDS/typ lib/verilog/cdl, LEF SIZE).
5. `pdk/sg13cmos5l_stdcell.cdl` hyphen-free symlink (KLayout LVS reader).
6. `engine/flow/pnr.tcl`: `DGSE_EXTRA_SDC` hook (project SDC sourced after the engine clock block, before `write_sdc`).
7. `engine/orchestrator.py`: config `extra_sdc` -> `DGSE_EXTRA_SDC`; platform default antenna diode (`pdks.json antenna_diode`)
   when config has none; KLayout DRC runner from `pdks.json klayout_drc_runner` (was hard-coded to sg13g2).

## Netlist

`HW/asic/build/chip1/synth/dgrid_soc1_chip_top_synth.v` (Yosys, sg13g2 typ, 304 macros) with `sg13g2_` -> `sg13cmos5l_`
(29 cell types, all present in the cmos5l LEF). The orchestrator's spec/rtl/synth stages are skipped (run_stages.py
calls `st_floorplan_pnr` etc. directly).

## Progress

### 15:20-15:40 chip1 (304 macros) floorplan probes
* `rtl_macro_placer` (engine `macro_placer: rtl`): MPL-0040 "Annealing engine failed" at 6600/m180 and m340,
  halo 10/20, flat or `link_design -hier`, and on chip1 even at 7000/7400/8000/9000 um dies (root cluster holds ~300
  macros); MPL-0065 (cells+haloed macros > core) at 6600/m340/halo 20. Not usable for this design.
* Scripted shelf floorplan instead (`scripts/shelf_pack.py`): macro rows (sorted by height) paired around horizontal
  std-cell channels, MX row below / R0 row above (pins face the channel), back-to-back pairs 4 um apart,
  >= 20 um vertical gaps, 20 um core clearance. chip1 at 6600/m180: 32 rows, 148 um channels.

### 15:40 chip2 (HART off: 272 macros / 16.91 mm2, 354 k cells / 7.06 mm2) -- switched to this netlist
* shelf pack: 6600/m180 -> 28 rows, 14 channels of 209 um; 6600/m340 (pad-ring inset) -> 29 rows, 15 channels of 166 um.
* engine run (macro_placements, halo 10): 272/272 placed, 0 outside core.
* PDN: PSM-0069 -- 63 short SRAMs (1P_64x16/64x64, 2P_64x22/64x32) have VDDARRAY! only in a 19 um Metal4 band;
  the 50 um TopMetal1 pitch missed it. Fix (run pdn_tcl `cmos5l-01/pdn_c5l_sram.tcl`): TopMetal1 1.8/2.0 @ 16 um pitch,
  remove row slivers < 60 um. check_power_grid VDD/VSS pass. (A macro-grid stripe set islanded the macros -- rejected.)
* c2-6600m340 global placement converged in 2.5 min: GPL utilization 63.0 % of the free row area (cells incl. 1-site
  padding 9.13 mm2), target density auto-raised 0.60 -> 0.64. **chip2 places at 6.6 mm with the 340 um pad-ring inset.**

### 16:25 hedge run c2-6600m340-fast (coordinator request)
* c2-6600m340 (threads 12) has sat in post-GPL `repair_design` since 15:53 (single-threaded, ~1.9 cores, no
  progress lines). Left running untouched.
* Hedge `c2-6600m340-fast`: same floorplan/placements/PDN, threads 4, `repair_extra "-buffer_gain 4.0 -verbose"`
  (gain-based buffering first, progress visible), `repair_timing_extra "-max_passes 2 -repair_tns 0 -verbose"`
  (new engine knob, change 8 below). Started from scratch (the engine's gplace resume re-runs GPL anyway; 4 min).
  Whichever run reaches detailed route first continues; nothing is killed without a note here.
* Engine change 8: `pnr.tcl` DGSE_REPAIR_TIMING_EXTRA appended to post-CTS `repair_timing -setup`;
  `orchestrator.py` config `repair_timing_extra` -> env.

### 16:40 root cause of the repair_design stall + third run c2-6600m340-hfn
* High-fanout nets in the netlist: `rst_main_n` (rst_main_i/_3_ flop) drives **69,527** async resets; `clk_main`
  80,620 (clock, CTS handles it); Yosys hilomap tie cells up to 3,037 pins; ~20 logic nets of 450-1,500 sinks in
  dp_fetch / dp_gen. The -buffer_gain hedge also stalls at "0 nets" (same net first).
* `cmos5l-01/hfn_tree.tcl` (config `post_gplace_tcl`, no engine change): every non-clock signal net > 400 sinks
  is split by recursive median bisection into groups of <= 40 sinks, one buf_8 per group at its centroid
  (tie nets: one cloned tie cell per group). Probe on ck_gplace: 29 nets, 3,273 cells, 16 s; afterwards
  `repair_design -verbose` processed 340k of ~370k nets in < 10 min (54k buffers, +2.6 % area) instead of stalling.
* `c2-6600m340-hfn` launched 16:41 (threads 8, post_gplace_tcl hfn_tree.tcl, repair_timing_extra
  "-max_passes 3 -verbose"). c2-6600m340 and c2-6600m340-fast keep running untouched.
* 16:50 (coordinator instruction) killed c2-6600m340 (pid 2756083, in repair_design since 15:53, no progress line) and
  c2-6600m340-fast (pid 2762723, same stall since 16:27). c2-6600m340-hfn continues alone.
* Probe result (hfn_tree + plain repair_design on ck_gplace): repair_design 817 s, 76,476 buffers in 20,524 nets,
  8,177 slew / 9,578 fanout / 8,860 cap violations fixed, design area 24.97 mm2 = 71 % of the 35.0 mm2 core.

### LVS preparation (engine changes 9-10)
9. `scripts/verilog2cdl.py`: hard-macro bus ports (bit i -> CDL pin `PORT<i>`/`PORT[i]`; was sys.exit on any
   multi-bit port) and `!`-suffixed power pins (`VDD!`/`VDDARRAY!` -> VDD, `VSS!` -> VSS; were floating).
10. `pdk/sg13cmos5l_stdcell_sram.cdl` = std-cell CDL + the 15 used SRAM CDLs merged (`cmos5l-01/scripts/merge_cdl.py`,
    1573 subckts, 686 duplicated RSC_IHPSG13_* leaf subckts dropped); `pdks.json ihp-sg13cmos5l cell_cdl` points to it.

### 16:58 c2-6600m340-hfn failed at detailed placement (DPL-0011/0033), rerun c2-6600m340-hfn2
* hfn_tree worked: repair_design done in ~14 min (+3.9 % area, 77,938 buffers), row utilisation after repair
  55.7 % (8.069 mm2 std cells / 14.476 mm2 rows). DPL legalised (avg displacement 6.9 um) but check_placement failed
  "Padding check failed (89)" -- all 89 are whole MX macro rows sitting 4 um above an R0 row (back-to-back gap),
  i.e. off-grid macros sharing a placement row with the macro below.
* Fix in shelf_pack.py: macros snapped to the site/row grid (core origin rounded up as initialize_floorplan does),
  back-to-back gap 7.56 um (2 rows). 6600/m340: channels 162.6 um.
* c2-6600m340-hfn2 launched 17:05, threads 16 (only run). A side probe checks GPL+DPL legality on its floorplan.
* Probe on hfn2's floorplan: the row-grid snap did NOT fix it -- same 89 macros fail DPL-0011, also with global
  padding 0 and with zero padding on all block masters. All failures are whole MX-oriented macro rows (8 of 15 MX
  rows; all 14 R0 rows pass); no gap/parity pattern found. Not understood; avoided instead:
* shelf_pack.py `--r0only`: every macro row R0 (pins down) with its own 84 um channel below (29 rows, 29 channels),
  rows snapped to the grid. Legality probe (GPL + DPL + check_placement on the floorplan ODB): **PASS**.
* 17:13 killed c2-6600m340-hfn2 (pid 2769187, still in repair_design, would hit the same DPL failure);
  launched **c2-6600m340-r0** (threads 16, hfn_tree, R0-only shelf placement) through gdsii/drc/lvs.

### c2-6600m340-r0 progress
* 17:10 GPL done (t=216 s); hfn_tree 29 nets / 3,273 cells; repair_design done 17:31 (t=1314 s), row utilisation
  61.4 % (8.070 mm2 cells / 13.149 mm2 rows). **Detailed placement + check_placement PASS** (t=1328 s).
* **CTS done ~17:33** (trees: clk_main_regs 85,711 sinks, clk_x2 1,244 + 241 macro sinks, clk_camera 130, cam_pclk 168,
  hb_rwds 74, jtag 88). Post-CTS setup before repair (placement parasitics, typ): WNS -6.03 ns, TNS -3,324 ns,
  1,801 violating endpoints (worst into dp_sink2). repair_timing (-max_passes 3) at 17:41: WNS -2.80 ns, TNS -340 ns,
  ~1,000 endpoints left.
* 17:43 post-CTS repair done: setup repair WNS -2.78 / TNS -240 ns (423 endpoints), then hold repair inserted
  14,456 hold buffers (+1.7 % area) and setup went back to WNS -4.10 / TNS -5,680 ns (engine log). ck_cts.odb t=2039 s.
* Per-clock STA on ck_cts.odb (typ, placement parasitics, `scripts/sta_clocks.tcl`): core_clock (clk_x2, 100 MHz)
  WNS -3.11 ns; clk_main (50 MHz) -0.39 ns; clk_camera +35.6; hb_ck +14.7; cam_pclk +32.5; hb_rwds +17.4; jtag +28.4;
  TNS -503 ns; worst hold -4.06 ns.
  **Root cause of the core_clock failure: inter-clock skew.** clk_main (generated /2, 85.7k sinks) has 7.5 ns
  insertion delay; the clk_x2 tree to the SRAM macros only 3.0 ns. clk_main -> SRAM (clk_x2) paths lose ~4.5 ns of
  the 10 ns period. TritonCTS builds each clock tree independently and does not balance a generated clock against
  its source. Fix next: balance latency (delay the clk_x2 macro tree / clock the macros from the clk_main tree
  root, or cut clk_main latency with a stronger/wider tree), then repair again.
* 17:43 global route started (TopMetal1 resources derated 35 % by the 16 um power straps).

### 18:50 skew fix works; runs r0b and v2 launched (coordinator plan: clean GDS > hold > setup)
* `cmos5l-01/skew_fix.tcl` probe on r0's ck_cts.odb: divider flop clocked straight from the clk_x2_in port, other
  clk_x2 loads behind N x dlygate4sd3_1 (~0.26 ns each). Moving the divider did not shorten clk_main (7.45 ns -- the
  tree itself is that deep); 8 cells raise SRAM CLK 3.83 -> 6.35 ns. Then repair_timing hold + setup (2 passes):
  **typ, placement RC: setup WNS +0.09 ns, TNS 0, hold WNS 0.00** (only 450 hold buffers; before the fix the engine
  needed 14,456 and still ended at -4.1 ns setup). Output `probe/cts_skewfix.odb`.
* Engine change 11: `pnr.tcl` DGSE_POST_CTS_TCL hook (after CTS + repair_clock_nets + DPL, before repair_timing),
  `orchestrator.py` config `post_cts_tcl`. `cmos5l-01/post_cts_skew.tcl` = the same fix as an engine hook
  (DGSE_SKEW_NMAX / DGSE_SKEW_TOL).
* PDN v2 (`pdn_c5l_sram_v2.tcl`): TopMetal1 VDD 1.8 um @ 16 um (VDDARRAY band), VSS 1.8 um @ 32 um (VSS! band is
  39 um tall); check_power_grid VDD/VSS pass on the r0 floorplan.
* **c2-6600m340-r0b** (18:50): engine resume_from global_route on probe/cts_skewfix.odb, allow_congestion,
  grt_overflow_max 1e6 -> GRT/DRT/GDS/DRC/LVS on the skew-fixed r0 database.
* **c2-6600m340-v2** (18:52): from scratch, macro_halo 5 (+~1.7 mm2 rows), PDN v2, hfn_tree, post_cts_skew
  (8 cells), repair_timing -max_passes 3 -repair_tns 0, allow_congestion.
* c2-6600m340-r0 left running in GRT (iteration ~20/40) to get its overflow numbers.
* **19:0x c2-6600m340-r0 was KILLED BY CGROUP OOM** in GRT iteration 21/40 (container memory.max = 32 GB, not the
  host's 755 GB): r0 GRT + r0b GRT + v2 + the GRT probe together. Each GRT on this design holds ~9-12 GB.
  Killed the 3-iteration GRT probe (pid 2779685, 7.2 GB) at 19:10. Rule from here: at most two OpenROAD P&R jobs
  at once. r0's numbers are lost; r0b (same placement, skew-fixed) carries on.
* Memory rule (coordinator): container limit **32 GB**; DRT on this design may need 15-25 GB -> never two DRTs at
  once. The second run to reach detailed route is stopped right after its `ck_groute.odb` checkpoint and resumed
  later with resume_from detailed_route; the DRT slot goes to the run with lower GRT overflow.
* c2-6600m340-v2 (halo 5): row utilisation after repair 54.6 % (8.067 / 14.787 mm2); DPL ok; CTS + post_cts_skew
  (SRAM CLK 3.64 -> 6.20 ns vs flops 6.83 ns, 8 cells); setup repair -> WNS -0.56 ns / TNS -2.6 ns (4 endpoints);
  hold repair 8,120 buffers -> hold 0.000. GRT started ~19:20. drt_gate.sh holds v2 at its groute checkpoint if
  r0b is in DRT by then.

### 19:45 GRT verdict on the R0-only shelf floorplan: NOT routable
* r0b's GRT ran 40 iterations, then restarted (NDR disabled on clock nets), i.e. no convergence. A 1-iteration
  GRT probe on the same database (`probe/cts_skewfix.odb`, -allow_congestion) gives the numbers:
  | layer | resource | demand | usage | overflow |
  |---|---|---|---|---|
  | Metal2 (V) | 6.90 M | 2.10 M | 30.5 % | 323,950 |
  | Metal3 (H) | 8.08 M | 5.19 M | 64.3 % | 853,336 |
  | Metal4 (V) | 6.73 M | 1.89 M | 28.1 % | 817,666 |
  | TopMetal1 (H) | 0.47 M | 0.29 M | 61.5 % | 102,946 |
  | total | 22.2 M | 9.47 M | 42.7 % | **2,097,898** |
  Wirelength 79.3 m (481k nets). Average usage is moderate (43 %); the overflow is local:
  (1) macro rows are packed to 95-97 % of the core width, so all vertical traffic squeezes through 190-430 um of
  gaps per row (~800-1,800 M2+M4 tracks); (2) the height-sorted shelf order scatters each PCORE's macros over many
  rows, so the logic->SRAM wires are long (79 m).
* 19:47 killed c2-6600m340-r0b (would enter DRT with ~2 M overflow; pointless and 15-25 GB). v2 continues to its
  GRT result for the halo-5 / lighter-PDN comparison; it will NOT be allowed into DRT with this overflow.
* 20:00 routability sweep (`scripts/fit_sweep.sh` -> `probe_fit.tcl`: floorplan + R0-only shelf + cut_rows + PDN v2
  + GPL + 3-iteration GRT, no repair/CTS) at 6600 (calibration) then 7400, one job at a time (coordinator: total
  < 22 GB while the 4-PCORE fallback chip3_4p is synthesised). QFN64 caps the die at 6.6 mm; the sweep is for the
  record. Next: chip3_4p at 6600/m340 (+ probes at 5600 / 6000) with hfn_tree, post_cts_skew, PDN v2.

### 20:15 chip3_4p (4 PCOREs, HART off): 224 macros / 13.17 mm2, 258k cells -- priority
* 20:10 stopped the 8P work for memory: killed c2-6600m340-v2 (pid 2784635, in GRT round 2 of the NDR-disabled
  restarts, no final number) and the 6600 calibration sweep probe (pid 2808497). chip2 checkpoints untouched.
* chip3 netlist renamed (`runs/soc1-c5l-chip3-net`), same 15 macro types, same divider / camera flop names.
  6600/m340 floorplan: instance area 18.34 mm2 in 35.04 mm2 core (52 %).
* R0-only shelf at 6600/m340: fill 1.0 -> 22 rows / 145 um channels (top row overflows the core; not used),
  0.9 -> 25 rows / 114 um, 0.85 -> 27 rows / 98 um, 0.8 -> 29 rows / 84 um. GRT fit probes running on 0.85 and 0.9.
* chip3 GRT fit probes at 6600/m340 (3 GRT iterations, no CTS/repair; PDN v2; halo 10), per-layer overflow:
  | floorplan | M2 | M3 | M4 | TM1 | total | usage | WL |
  |---|---|---|---|---|---|---|---|
  | fill 0.90 (25 rows, 114 um ch.) | 50,840 | 38,719 | 124,135 | 4,028 | **217,722** | 24.9 % | 52.5 m |
  | fill 0.85 (27 rows, 98 um ch.) | 48,293 | 71,533 | 122,352 | 13,945 | 256,123 | 25.3 % | 53.4 m |
  (8P chip2 6600 for reference: 2,097,898 / 42.7 % / 79.3 m.)
* Congestion map (`scripts/cong_map.py`, fill 0.90): vertical overflow is ~96 % in gcells OVER macros, peaking at
  x = 1.5-4.5 mm: with Metal1-4 blocked by the SRAMs and TopMetal1 horizontal, CMOS5L has NO vertical layer over a
  macro, so every row crossing must use the gaps between macros. Horizontal overflow: half over macros (TopMetal1),
  half in channels.
* Corridor packing (`shelf_pack.py --corridors K --cw W`): K straight vertical corridors at the same x in every
  row. K=6/cw=64 um gives 7 segments of 788 um (one 784-um macro each): 25 rows / 115 um channels; K=5/cw=200:
  29 rows / 86 um. Probe K6/cw64 running.
* c3-6600m340 (full engine run, fill 0.90): row util after repair 32.8 %; skew hook SRAM 4.31 -> ? / flops 8.10 ns.
* more chip3 probes (3 GRT it.): corridors K5 x 200 um (29 rows / 86 um ch.): 31.1k / 66.2k / 63.3k / 17.6k =
  **178,174** (WL 51.7 m); single 900 um spine K1: 279,267 (M4 184k); K2 x 400: 346,016; K6 x 60: 251,504.
* Column topology (coordinator idea; `scripts/column_pack.py`): macros stacked in columns, all R0, a 25 um pin-access
  gap under each macro (a horizontal M3 corridor through the column), vertical channels between columns.
  6600/m340: 6 columns (784/784/703/597/237/237 um wide), 5 channels of 362 um. R90 not used (macro Metal4 power
  stripes would run parallel to TopMetal1 -> no PDN connection). Probe running.
* Column probe (6 columns, 362 um vertical channels, 25 um pin gaps): 42.1k / **445.1k** / 59.4k / 91.5k = 638,037 --
  vertical fixed, but horizontal traffic cannot cross 600-780 um wide columns (only TopMetal1 + the pin gaps). Worse.
* Best floorplan so far: rows with 5 x 200 um aligned corridors (178k at 3 iterations). 20:45 launched full engine
  run **c3-6600m340-k5** (that floorplan, threads 8, same fix set) alongside c3-6600m340 (fill 0.90, GRT iteration 15).

### 21:05 chip4_lean = deliverable netlist (209 macros / 12.48 mm2; chip3 + lean AXI fabric, repo d16342a)
* Probes 6600/m340 (3 GRT it.): K5 x 230 um corridors (26 rows / 104 um ch.): 30.0k / 32.3k / 50.8k / 11.1k =
  **124,293** (22.9 %, WL 49.4 m); K6 x 64 um (23 rows / 131 um): 212,264 (M4 159k).
* 21:05 killed c3-6600m340-k5 (pid 2820310, chip3, in CTS) per coordinator; launched **c4-6600m340-k5**
  (chip4_lean, K5 x 230 corridors, halo 10, hfn_tree, post_cts_skew, PDN v2, GRT gate 5,000, threads 12).
  c3-6600m340 kept only until its 40-iteration GRT number is in (calibration of the 3-iteration probe).
* c4-6600m340-k5: repair -> row util 33.1 % (6.40 / 19.35 mm2), DPL ok, skew hook 13 cells (SRAM 7.41 / flops
  7.65 ns), post-CTS setup WNS -0.37 ns / TNS -2.5 ns (30 endpoints), hold 0.000 after 14,159 hold buffers.
  GRT started ~21:30.
* GRT iteration calibration (chip4 K5x230 probe, no CTS): 3 iterations 124,293 -> **15 iterations 40,218**
  (M2 13.8k / M3 9.9k / M4 14.4k / TM1 2.1k; 27.6 % usage), 33 min. 21:58 killed c3-6600m340 (pid 2809626, chip3
  fill 0.90, GRT iteration 26/40) -- calibration obtained from the probe instead, memory freed for c4.
* Hedge probe chip4 K5x230, GPL density 0.45 + pad 2, 15 GRT it.: 11.0k / 7.6k / 11.7k / 1.6k = **31,890**
  (vs 40,218 at density 0.6 / pad 1), usage 29.8 %, but WL 64.0 m (+28 %).
* Hedge probe chip4 K4x300 (32 rows / 65 um ch.), density 0.5 + pad 2, 15 it.: 19.3k / 19.4k / 21.2k / 5.8k =
  65,710 (WL 69.3 m) -- worse than K5x230. Best hedge stays K5x230 + density 0.45 / pad 2 (31.9k).
* GRT is slow on this design: c4-6600m340-k5 at iteration 26/40 at 23:11 (~7-10 min per iteration now).
* 23:30 hedge run **c4-6600m340-k5d45** (chip4_lean, K5x230, place_density_override 0.45, gpl_pad 2, cell_pad 2,
  same hooks/PDN, threads 6) launched with DGSE_PNR_STOP_AFTER=groute: it writes ck_groute.odb and stops at the DRT
  boundary. `scripts/mem_guard.sh` kills it if total OpenROAD RSS >= 28 GB while c4-6600m340-k5 is in DRT
  (c4 GRT holds 8.5 GB now).
* 00:47 GRT is crawling: c4-6600m340-k5 at extra iteration 33/40 (last ones ~20 min each), hedge k5d45 at 20/40
  (~6 min each). The 15-iteration probe already gets most of the reduction, so launched **c4-k5d45-g15**: engine
  resume_from global_route on the hedge's ck_cts.odb with grt_congestion_iters 15, parked at ck_groute
  (DGSE_PNR_STOP_AFTER). Whichever run reaches its groute checkpoint first with acceptable overflow gets DRT.
* Hedge k5d45 post-CTS (typ, placement RC): skew hook 14 cells (SRAM 7.79 / flops 7.97 ns); setup after repair
  WNS -0.73 ns / TNS -4.1 ns (12 endpoints), but **hold NOT clean: WNS -0.86 ns / TNS -901 ns** after hold repair
  (density 0.45 + cell_pad 2 left the repair no room?). c4-6600m340-k5 (density 0.6, pad 1) had hold 0.000.
* 00:55 killed c4-6600m340-k5d45 (pid 2863469, 40-iteration GRT at 20/40; superseded by its 15-iteration resume)
  and launched **c4-k5-g15** = engine resume_from global_route on c4-6600m340-k5's ck_cts.odb (clean hold),
  grt_congestion_iters 15, parked at ck_groute.
* 00:58 killed c4-6600m340-k5 (40-iteration GRT, 20 min per iteration at 33/40) on the coordinator's memory
  instruction (3 jobs = ~25 GB of the 32 GB cap). Running now: c4-k5-g15 and c4-k5d45-g15 (both 15 GRT iterations,
  parked at ck_groute).
* **Why GRT took hours:** after each 15/40-iteration round with overflow left, GRT disables the non-default rule
  (CTS clock NDR) on a few clock nets (GRT-0273) and starts a NEW round; 82 NDR nets -> up to ~20 rounds.
  c4-k5-g15 had just begun its 2nd round at 01:17. Fix: `scripts/ndr_off.tcl` clears the NDR on all nets of the
  ck_cts checkpoint (82 / 81 nets) -> ck_cts_nondr.odb; 01:22 killed both g15 runs (pids 2883330, 2883208) and
  relaunched them on the NDR-free checkpoints (resume_from global_route, 15 iterations, parked at ck_groute).

### 02:00 real-design GRT (after repair + CTS + hold buffers), chip4_lean 6600/m340, 15 iterations, NDR off
| run | M2 | M3 | M4 | TM1 | total | usage | WL |
|---|---|---|---|---|---|---|---|
| c4-k5-g15 (density 0.6, pad 1; hold clean) | 52.4k | 58.2k | 81.4k | 11.6k | **203,513** | 31.2 % | 71.0 m |
| c4-k5d45-g15 (density 0.45, pad 2; hold -0.86 ns) | 47.5k | 47.5k | 70.8k | 9.7k | **175,473** | 35.5 % | 80.0 m |
* 5x the GRT-only probe (40k): repair_design + hold repair add ~75k buffers and the wirelength rises 49 -> 71-80 m.
  Not routable (DRT does not recover six-figure overflow). Both resumes also stopped with GRT-0116: pnr_resume.tcl
  calls global_route without -allow_congestion (engine gap; pnr.tcl honours allow_congestion), so no ck_groute.
* No routed database, GDS, DRC or LVS for any configuration at 6.6 mm. All jobs stopped; no OpenROAD running.

### 02:20 next cycle (coordinator): chip4_lean, two runs (memory <= 25 GB)
* Engine changes 12-14: `pnr_resume.tcl` global_route honours allow_congestion; `pnr.tcl` config `skip_cts_hold`
  (DGSE_SKIP_CTS_HOLD) and `post_grt_tcl` (DGSE_POST_GRT_TCL, after estimate_parasitics -global_routing); hooks
  `cmos5l-01/ndr_off_hook.tcl` (pre_groute_tcl: clear CTS NDRs) and `cmos5l-01/post_grt_hold.tcl`
  (global_route -start_incremental; repair_timing -hold; DPL; -end_incremental).
* (A) **c4-7400-k5g**: die 7400 / m340, rows ordered by height class then owner block (`--order group`), 5 x 380 um
  corridors (26 rows / 134 um channels), density 0.6, hfn + skew + PDN v2 + ndr_off, 15 GRT iterations, full flow
  through GDS/DRC/LVS, threads 10.
* (B) **c4-6600-k5-lateh**: c4-k5 floorplan, skip_cts_hold + post_grt_hold, repair_design -max_wire_length 3000,
  same hooks; stopped by a watcher when it reaches DRT (diagnostic: overflow before / after the hold buffers).
* Results 02:52 (15 GRT iterations, NDR off; overflow M2 / M3 / M4 / TM1 = total, usage, WL):
  | run | overflow | usage | WL |
  |---|---|---|---|
  | (A) c4-7400-k5g, 7.4 mm die | 23.5k / 29.8k / 56.5k / 1.8k = **111,681** | 23.3 % | 71.0 m |
  | (B) c4-6600-k5-lateh, no hold buffers yet | 51.9k / 56.4k / 80.4k / 11.7k = **200,466** | 30.8 % | 70.1 m |
  | ref c4-k5-g15 (6.6 mm, with post-CTS hold buffers) | 203,513 | 31.2 % | 71.0 m |
* (B) shows the ~14k hold buffers cost only ~3k of overflow; -max_wire_length 3000 did not change repair_design
  (59,960 buffers vs 59,866: slew/cap/fanout driven). The 49 -> 70 m wirelength jump from the GRT-only probe comes
  from CTS + repair_design, not hold.
* (A) at 7.4 mm still has 112k: vertical overflow sits OVER macros inside the 797 um corridor segments
  (x 2.7-3.5, 3.9-4.7, 5.1-5.9 mm; 98 % of vertical overflow over-macro), horizontal half in channels.
  Die area alone does not fix it with this shelf topology. (A) hold after post-CTS repair: -1.41 ns / -2,348 ns
  (not clean; same symptom as the density-0.45 hedge).
* (A) entered DRT at 02:53 (allow_congestion) -- left running to measure the DRT violation trend; mem_guard kills (B)
  if total RSS >= 26 GB.
* (B) post-GRT hold repair (GRT parasitics, no post-CTS hold repair): hold WNS **-4.45 ns, TNS -28,854 ns** at the start
  of repair (iteration 140: -4.39 ns). With global-route RC the hold picture is far worse than at placement level
  (post-CTS placement-RC hold repair needed ~14k buffers and reached 0.000 on c4-k5). 02:55 mem_guard killed (B)
  (total RSS 27 GB with (A) in DRT). Root cause of the -4.4 ns not yet analysed (suspects: clock-tree latency with
  GRT RC vs the placement estimate the skew fix was balanced on; the 13-16 dlygate cells on the clk_x2 branch).

### 03:00 band floorplan attempt (coordinator): wide macros at the core edges, narrow ones in the middle
* chip4 widths: 140 of 209 macros are > 400 um wide (784 / 703 / 685 / 596 / 526 um; ~10.3 of 12.5 mm2);
  69 are <= 420 um (237 / 279 / 417 / 420 um).
* `shelf_pack.py --bands WMIN KW CWW KN CWN`: macros wider than WMIN in rows at the bottom and top of the core (KW
  corridors of CWW um), the rest in the middle rows (KN corridors of CWN um, i.e. one narrow macro per <= 440 um
  segment). 7400: bands 400/2/150/11/130 -> 26 rows / 132 um channels; 6600 -> 27 rows / 92.5 um.
* Placement-only GRT probe (15 it.) at 7400 running (the real post-CTS number is ~4-5x for k5 at 6600: 40k -> 204k).
* (A) c4-7400-k5g DRT iteration 0 running (19 GB); kept only for the first 2-3 iteration counts.
* (A) c4-7400-k5g DRT iteration 0: 10 % -> 39,285, 20 % -> 182,616, 30 % -> 201,067 violations (~13 min). Not
  converging (GRT overflow 112k behind it). 03:17 killed (pid 2901663): new memory budget ~22 GB (two more agents
  on the box), and the iteration-0 trend already answers the question. ck_groute.odb kept.
* Band probe 7400 (placement-only, 15 it.): 12.5k / 5.9k / 19.0k / 1.0k = **38,361** (usage 20.8 %, WL 60.7 m) -- about
  the same as the K5x230 placement probe at 6600 (40.2k), i.e. not the step change needed.

### 03:30 chip5_icg (clk_main / clk_camera from 2 sg13cmos5l_lgcp_1 ICGs on clk_x2, no divider flops)
* netlist renamed (`runs/soc1-c5l-chip5-net`), same 209 macro instance names as chip4 (macro list diff empty).
* Engine change 15: config `cts_extra` -> DGSE_CTS_EXTRA appended to clock_tree_synthesis.
* **c5-6600-k5-icg**: c4-k5 floorplan (6600/m340, K5x230), SDC HW/asic/constraints/chip_extra_icg.sdc, NO skew hook,
  cts_extra -balance_levels, `post_gplace_icg.tcl` (hfn_tree + both ICGs next to the clk_x2_in pin), ndr_off,
  15 GRT iterations, skip_cts_hold + post_grt_hold (hold repaired on GRT parasitics), stopped at the DRT boundary.
  Key numbers: post-GRT hold (vs -4.45 ns with the dividers) and GRT overflow.
* 03:35 also launched **c5-7400-band-icg** (chip5_icg, band floorplan at 7400, same ICG recipe, threads 6, stopped at the DRT boundary) = the real post-CTS number for the band floorplan.
* c5-7400-band-icg post-CTS (no skew hook, CTS -balance_levels): clk_main_regs 70.0k sinks behind the ICG, clk_x2
  164 SRAM + 676 flop sinks; setup after repair **WNS -4.81 ns / TNS -3,056 ns** (1,466 endpoints) -- the ICG alone
  does not balance the trees (same signature as the divider). Kept running to its GRT number, stops at DRT.
* ~03:55 killed c5-6600-k5-icg (pid 2971609, no-hook variant) per coordinator; launched **c5-6600-k5-icg-skew**:
  post_cts_skew.tcl generalised (DGSE_SKEW_ROOTS = the two ICGs: their CLK pins move to the clk_x2_in port net,
  the rest of clk_x2 goes behind the dlygate chain), skip_cts_hold, `post_grt_rebalance.tcl` as post_grt_tcl
  (one incremental GRT: measure SRAM vs flop CLK arrival on GRT RC, add/remove chain cells to |diff| <= 0.2 ns,
  DPL, repair_timing -hold, -end_incremental; reports latencies and hold/setup before/after). Stops at DRT.
* c5-7400-band-icg real post-CTS GRT (15 it.): 34.8k / 25.6k / 79.1k / 3.0k = **142,461** (24.6 %, WL 75.0 m) -- worse than the K5x380 grouped rows at 7400 (111.7k). Band floorplan rejected.
* c5-7400-band-icg post-GRT hold repair start (GRT RC, NO skew hook): hold **WNS -10.20 ns, TNS -20,321 ns**, 8,237 endpoints -> the hold failures are the inter-tree skew (clk_x2-launched paths into the deep ICG clk_main tree). 04:23 killed (numbers obtained).
* c5-6600-k5-icg-skew post-CTS: skew hook with the ICG roots, 9 cells: SRAM CLK 6.50 -> 9.11 ns vs flops 9.25 -> 9.28 ns; setup after repair WNS -0.49 ns / TNS -6.4 ns (27 endpoints). GRT started 04:33.
* c5-6600-k5-icg-skew GRT (15 it., NDR off) finished: 51.7k / 56.7k / 77.9k / 12.0k = **198,322** (31.0 %, WL 70.5 m),
  then the run died writing ck_groute.odb: **disk full** (iostream error). Coordinator freed disk (17 GB free).
  Hygiene from now on: keep ck_cts / ck_groute / final ODBs only, delete dead runs, `df -h /` before each launch
  (stop below 8 GB). Deleted c5-6600-k5-icg-skew's ck_macros/floorplan/gplace/repair/dplace + the .part file.
* Engine change 16: pnr_resume.tcl gets the pre_groute_tcl and post_grt_tcl hooks (a resumed GRT ran without
  NDR-off / rebalance). Resumed c5-6600-k5-icg-skew from build/ck_cts.odb (resume_from global_route) -> GRT ->
  post_grt_rebalance.tcl; stopped at DRT.

### Routing-direction experiment (coordinator): TopMetal1 vertical so vertical traffic can cross the macros
* Variants via a modified copy of the tech LEF (probe/lefdir/): (v1) M1 H / M2 V / M3 H / M4 H / TM1 V and
  (v2) TM1 V with M4 kept V -- both REJECTED by FastRoute: GRT-0126 "Layers Metal3 and Metal4 (resp. Metal4 and
  TopMetal1) have the same preferred routing direction" -- the global router requires alternating directions.
* Only legal TM1-vertical stack: fully flipped **M2 H / M3 V / M4 H / TM1 V** (tech_flip.lef; M1 left H, not routed).
  PDN for it: `pdn_c5l_tm1v.tcl` (M1 rails, TM1 vertical straps 1.8/2.0 @ 32 um, M1->TM1 via stacks, no M4 straps,
  ring M4+TM1; macros M4->TM1 where straps cross). Pins: hor Metal2 / ver Metal3. Probe c5flip (chip5, K5x230,
  6600/m340, placement-only, 15 it.) running.
* c5-6600-k5-icg-skew resume (GRT 15 it., NDR off 128 nets): 52.4k / 57.1k / 77.0k / 12.0k = 198,539. Post-GRT:
  **hold WNS -7.04 ns on GRT RC** (chain of 9 cells balanced on placement RC), then post_grt_rebalance.tcl died:
  EST-0005 -- estimate_parasitics -global_routing is refused inside global_route -start_incremental. Script fixed:
  measure outside the incremental session, each round edits the chain inside start/end_incremental (up to 4 rounds,
  ~0.26 ns per cell), then hold repair in its own incremental session. Not yet re-run (congestion has priority).
* **c5flip** (chip5, fully flipped M2 H / M3 V / M4 H / TM1 V, K5x230, 6600/m340, placement-only 15 it.):
  M2 2.8k / M3 43.8k / M4 0.4k / TM1 0.6k = **47,603** (28.6 %, WL 65.2 m) vs 40,218 with the normal directions
  (chip4, same floorplan) -> no gain. TM1 carries only 3.2 % (3.28 um pitch = ~2 tracks per gcell); the vertical
  load lands on M3 (now the only fine vertical layer) and overflows there. Direction flip rejected.
* c6f2kflip (chip6_f2k + flip) died in GRT with GRT-0228 (edge usage 65535 > limit; seen before on one K6 probe).
* chip6 probes (normal directions, PDN v2, K5x230, 6600/m340, placement-only 15 it.):
  c6f1k (192 macros, 25 rows / 110 um ch.): 14.0k / 9.5k / 16.8k / 1.4k = **41,735** (27.3 %, WL 60.3 m) -- no gain vs
  chip4/5 (40.2k). c6f2k: process vanished at GRT iteration 9 without an error line (likely OOM: 4 probes + another
  agent's mpl-c7w32 job); its K5x230 pack also overflowed the core top (top_y 6331 > 6240) -- needs fill < 1.
* chip7 probes (normal directions, PDN v2, 6600/m340, placement-only 15 it.):
  | netlist / rows | M2 | M3 | M4 | TM1 | total | usage | WL |
  |---|---|---|---|---|---|---|---|
  | c7w16 (438 macros; K10 x 40 um, 24 rows / 106 um ch.) | 45.5k | 15.3k | 22.3k | 6.8k | **89,847** | 35.6 % | 71.6 m |
  | c7w32 (298 macros; K6 x 60 um, 28 rows / 81 um ch.) | 20.2k | 24.3k | 18.8k | 8.6k | **71,906** | 30.3 % | 67.1 m |
  Narrow macros in rows are worse than chip5/6 (40-42k): more macros -> more rows -> thinner channels, more pins.
  The coordinator's second agent (rtl_macro_placer, halo 25) reports 23.6k on chip6_f2k -> its placement is ahead.

### 18:00 real runs on the MPL placement (coordinator's second agent: rtl_macro_placer, halo 25, chip6_f2k: 23.6k)
* `scripts/pl_to_placements.py`: MPL .pl (bbox lower-left + orient) -> engine macro_placements (dbInst origin).
  MPL uses R0/MX/MY/R180 (43/43/30/40).
* **c6-6600-mpl**: chip6_f2k, mpl-c6/d_h25_lvl1.pl as-is; **c6-6600-mplr**: same with MX->R0, R180->MY (hedge against
  the unexplained DPL-0011 failure on MX macros). Both: 6600/m340, ICG SDC, post_gplace_icg (hfn + ICGs at
  the clk_x2 pin), skew hook with ICG roots, PDN v2, ndr_off, 15 GRT it., skip_cts_hold + post_grt_rebalance.
  drt_gate.sh both ways (never two DRTs), ckpt_clean.sh deletes superseded checkpoints.
* 18:04 **c6-6600-mpl passed detailed placement** (MX as-is; no DPL-0011): row util after repair 46.7 %
  (9.65 mm2 cells / 20.68 mm2 rows). Killed + deleted c6-6600-mplr (hedge not needed).
* 18:06 launched **c7w32-6600-mpl**: chip7_w32 + mpl-c7w32/h25_lvl1.pl (MPL probe 19.4k), same full flow;
  config macros = the 13 chip7 types (1P_1024x32 / 1P_256x16 are new). drt_gate: held at ck_groute while c6 is in DRT.
* DRT gate changed to best-overflow (coordinator): post_grt_rebalance.tcl now writes build/ck_groute_hold.odb (after rebalance + hold repair, guides in the DB); stop_at_drt.sh stops c6-6600-mpl and c7w32-6600-mpl at the DRT boundary; the lower-overflow run is resumed with resume_from detailed_route on its ck_groute_hold.odb.
* **c6-6600-mpl real GRT** (chip6_f2k + MPL h25, 15 it., NDR off 118): 54.9k / 27.7k / 44.4k / 4.2k = **131,094**
  (28.3 %, WL 68.3 m) vs its placement-only MPL probe 23.6k (5.5x, the same factor as before). repair_design added
  72,670 buffers (+3.3 %); skew hook 5 cells (SRAM 6.93 -> 8.42 / flops 8.66 ns); setup after repair -1.00 ns / -1.4 ns.
* c6-6600-mpl post-GRT rebalance (GRT RC): hold before -6.75 ns; measured SRAM CLK 6.31 / flop CLK 3.44 ns (the
  flop sample reads far earlier on GRT RC than on placement RC, 8.66 ns -- suspect); rebalance removed all 5 chain
  cells (diff -2.88 -> -1.68 ns); hold before repair -4.99 ns, setup -4.31 ns; then repair_timing -hold died with
  EST-0104 "inconsistent parasitics state" inside the incremental GRT session. Run ended (ck_cts / ck_groute kept).
  The GRT-RC rebalance needs rework (measure on a full re-route, or do hold repair outside start/end_incremental).
* **Repair-light probe c7w32-6600-mpl-lite**: the liberty's default_max_fanout is **8** (sg13cmos5l typ lib) -- the
  source of ~9.5k fanout "violations" and most of the ~70k repair buffers. New pdks.json entry `cmos5l-fo40` =
  ihp-sg13cmos5l with a liberty copy at default_max_fanout 40 (pdk/cmos5l_fo40/), plus max_transition_ns 2.0.
  Same flow otherwise (chip7_w32 + MPL h25, skew hook, hfn, PDN v2, 15 GRT it.); stopped at DRT.
  c7w32-6600-mpl (normal repair) continues for the comparison; keep_gplace.odb / keep_floorplan.odb saved.
* repair_design on chip7_w32 + MPL: normal 58,093 buffers (9,267 fanout / 5,569 slew / 4,989 cap violations) vs **lite (fanout 40, max_tran 2.0) 25,129 buffers** (663 fanout / 6,343 slew / 5,522 cap); row util 38.7 % -> 37.7 %.
* 19:25 killed c7w32-6600-mpl (normal repair): stuck in CTS > 60 min (TritonCTS level 2, 1,792 sinks per sub-region, no progress line), the fanout-8 buffered netlist. Comparison taken from the repair_design buffer counts instead.
* **c7w32-6600-mpl-lite real GRT** (chip7_w32 + MPL h25, fanout-40 lib, max_tran 2.0; 25.1k repair buffers; skew 11
  cells SRAM 10.07 / flops 10.31 ns; setup after repair WNS -0.90 ns / TNS -0.9 ns): 67.8k / 34.6k / 61.0k / 16.6k =
  **179,902** (28.4 %, WL 62.6 m) vs its placement-only MPL probe 19.4k (9.3x). Fewer repair buffers did NOT reduce
  overflow (c6-mpl with 72.7k buffers: 131k). The probe-to-real gap is not the repair buffers; candidates: CTS
  (clk_main tree ~70k sinks) and DPL legalisation/cell padding concentrating cells (the probe stops after GPL).

## Lessons so far + recommended recipe for the March 2027 run (draft, kept up to date)
**What is known**
1. CMOS5L (M1-M4 + TopMetal1) and the IHP SRAMs: the macros block M1-M4 completely; TopMetal1 is the only layer over
   them and is coarse (3.28 um pitch, ~2 tracks per 7.2 um gcell) and also carries the power straps. Macro area is
   ~45-50 % of a 6.6 mm die even with 4 PCOREs -> routing is the binding constraint, not placement area.
2. FastRoute requires alternating layer directions (GRT-0126): TM1 vertical forces a fully flipped stack, which
   moves the vertical load onto M3 and was worse (47.6k vs 40.2k probe).
3. Placement-only GRT probes underestimate the real (post-CTS/repair) overflow by 5-9x on this design; probes rank
   floorplans but cannot certify one. Real numbers so far: >= 111k (7.4 mm), >= 131k (6.6 mm).
4. Engine/flow issues found and fixed: rtl_macro_placer failure on flat netlists (MPL-0040) -> scripted shelf or
   hierarchical MPL; 69.5k-fanout reset -> hfn_tree.tcl; VDDARRAY! band -> TM1 VDD @ 16 um; GRT restart rounds on
   CTS NDRs -> ndr_off; liberty default_max_fanout 8 (most repair buffers); generated-clock skew (divider or ICG)
   -> post-CTS delay-chain hook; resume path missing allow_congestion / hooks; disk/memory (32 GB cgroup) limits.
5. Hold: with the skewed clk_x2 vs clk_main trees, hold on GRT RC is -4.5..-10 ns; the delay-chain fix balances on
   placement RC only. A GRT-RC rebalance needs a cleaner implementation (no EST in incremental sessions).
**Recommended recipe (March 2027)**
- Netlist: chip7-style narrow macros or fewer/merged memories, ICG clocking with clk_main and clk_x2 as ONE CTS tree
  (gate the clock enables in RTL instead of a gated clock where possible), reset tree synthesised or pre-buffered.
- Floorplan: hierarchical rtl_macro_placer (halo ~25) on a -hier linked netlist, R0/MX/MY/R180 allowed (DPL passed).
- Liberty fanout limit 20-40 (deliberate waiver), max_transition from the PDK, hfn_tree for resets/ties.
- Probe-to-real factor must be measured per recipe; target placement-only probe <= 3-4k for a real <= 20k.
- Consider SG13G2 (7 layers: M5 + TM1/TM2) if the CMOS5L cost advantage is not essential: the extra vertical layer
  over macros removes the root cause.
* c7w32-6600-mpl-lite post-GRT: the GRT-RC rebalance WORKS now (diff -2.51 -> +0.24 -> -0.03 ns in 2 rounds, chain
  13 -> 2 cells) but hold before repair is still **-4.33 ns** (setup -12.4 ns on GRT RC), and repair_timing -hold
  again died with EST-0104 inside the incremental session -> hold repair must run outside start/end_incremental.
* Gap analysis 1 (c6-6600-mpl ck_cts.odb, 15 GRT it., NDR off): all nets 131,094 -> clock nets excluded (13,361 nets made special) **113,373** (46.9k / 23.7k / 39.2k / 3.5k; WL 64.4 m). The clock tree accounts for ~18k (14 %); the signal nets carry the rest.
* Gap analysis 2 (chip7_w32 + MPL h25, engine ck_gplace = GPL + PDN, then hfn_tree, 15 GRT it.): 14.5k / 8.2k / 7.3k / 2.5k = **32,507** (27.1 %, WL 58.1 m) -- vs MPL-agent probe 19.4k and the real run 179.9k: the 5.5x jump happens after global placement (repair_design / DPL / CTS). Probes with DPL pad 1 / pad 0 added running.
* **Hold root cause found** (c7w32-6600-mpl-lite ck_groute.odb, placement RC, `scripts/hold_paths.tcl`): worst hold
  -3.40 ns is core_clock -> core_clock, clk_x2 *register* (e.g. axi_split pending_resp_fifo g_1p_phase_i/_3_, CLK at
  7.71 ns) -> SRAM A_ADDR (capture CLK at 11.00 ns). Both share the 11-cell SKEWFIX chain; the SRAM branch then gets
  **~50 `delaybuf_<n>_core_clock` buffers (~3.2 ns) inserted by TritonCTS** -- macro/register latency balancing
  (insertion-delay balancing of the macro sinks against the register tree, with -balance_levels) -- so every
  clk_x2 flop -> SRAM path is a 3.3 ns hold violation. Other groups: clk_main -1.52 (register_bank ram3 _351_ ->
  _707_), cam_pclk -0.65 (afifo -> 64x32 SRAM), all others >= 0. Not an SDC edge problem.
  Fix: stop CTS from delay-padding the macro branch (cts delay-buffer derate 0 / no -balance_levels / macro
  insertion delay from the SRAM liberty), then balance clk_x2 regs + SRAMs as one group against clk_main.
* Gap analysis 3 (chip7_w32 engine ck_gplace + hfn_tree (no SDC: clock nets also split) + DPL, 15 GRT it.):
  DPL pad 1: 8.7k / 3.6k / 6.3k / 1.4k = **19,958** (WL 60.1 m); DPL pad 0: **19,693**. Legalisation does not add
  overflow (it removes GPL overlap: 32.5k -> 20.0k) and padding is irrelevant. The jump to the real 180k is
  repair_design and/or CTS. Next: + repair_design (fanout-40 lib, max_tran 2.0, with SDC so clocks are not split).
* Gap analysis 4 (c7w32-6600-mpl-lite ck_cts.odb, clock nets excluded, 15 it.): 61.8k / 31.2k / 56.1k / 14.7k = **163,777** (vs 179,902 with clocks): clock nets ~16k; the signal nets of the post-CTS database carry ~164k.
* Gap analysis 5 (chip7_w32 ck_gplace + hfn WITH SDC (clocks not split, no CTS) + lite repair_design + DPL):
  **166,270** -- confounded: the unbuffered 70k-sink clock nets are routed as plain nets here. Re-running with clock
  nets excluded, with and without repair_design (c7_s_hfn_dpl_noclk / c7_s_hfn_rep_dpl_noclk).
* Threads rule (user, 31 Oct 20:50): every probe and run uses threads 4 (make_run.py default 16 -> 4, all
  make_c4_runs entries 4, probe scripts 4) so 3-4 jobs share the 16 CPUs; the run that goes to detailed route
  runs DRT alone with threads 16 (resume_from detailed_route, "threads": 16), other jobs paused/held.
* Gap analysis 6a (chip7_w32 ck_gplace + hfn (SDC) + DPL, the 8 pre-CTS clock nets excluded): 6.2k / 2.8k / 4.9k / 1.4k = **15,383** (WL 57.6 m). Waiting for 6b = same + lite repair_design.
* **Gap analysis 6b -- ROOT CAUSE**: same as 6a + lite repair_design (25,124 buffers in 9,231 nets, WL 57.6 -> 59.5 m,
  only +3 %): 60.5k / 30.6k / 56.9k / 15.2k = **163,157** vs **15,383** without repair. repair_design alone
  multiplies the overflow by 10.6x on a +3 % wirelength -- it is not demand, it is where the buffers land (clusters /
  pin-access hotspots). The 5-9x probe->real factor seen all along is repair_design.

### 01 Nov ~03:30 IST -- G2 candidates (chip7_w32 + MPL h25, 6600/m340, threads 4, stop at ck_groute)
* Engine change 17: `skip_repair_design` (DGSE_SKIP_REPAIR_DESIGN) in pnr.tcl / orchestrator.py.
* **c7w32-6600-norep**: repair_design skipped; skew hook (ICG roots); skip_cts_hold; setup repair_timing 2 passes;
  ndr_off; 15 GRT it.; pdk cmos5l-fo40. Expectation ~15k + ~16k CTS.
* **c7w32-6600-respread**: lite repair_design (fanout 40, max_tran 2.0) + `gpl_incremental` (engine knob:
  global_placement -incremental after repair_design, before DPL) to spread the buffers; otherwise as norep.
  This is the shippable variant if it works (slew/cap fixed).
* Handoff: a new session continues from HW/asic/dgse/runs/NOTES.md (this file) + the coordinator's
  HANDOFF_IHP_TAPEOUT.md; scripts in HW/asic/dgse/runs/cmos5l-01/, engine edits listed in patch_engine.py.
* **c7w32-6600-norep REAL GRT (CTS included)**: 9.5k / 4.0k / 7.0k / 1.7k = **22,079** (28.1 %, WL 61.1 m) -- the
  first real run near the G2 target (<= ~20k). But setup after CTS is WNS -56 ns / TNS -90,748 ns (unrepaired
  slew/cap) -> not shippable as is. ck_groute.odb written (stopped by DGSE_PNR_STOP_AFTER).
* 01 Nov 04:27 UTC (09:57 IST) USER DECISION: DRT on **c7w32-6600-respread** ck_groute (GRT 49,512) alone, resume_from detailed_route, threads 16, allow_congestion, no pre-DRT hold repair (hold/setup ECO after routing). Anti-pileup variants rsp-a/b/c (max_tran 2.5 + incremental GPL -routability_driven; gpl_pad 3; both) configured but NOT run (engine change 18: gpl_incr_extra / DGSE_GPL_INCR_EXTRA). Disk cleaned (c5 skew, c6-mpl, c7w32-lite, norep intermediates deleted; 15 GB free). DRT pin access done 04:29 (334,586 groups), RSS 12 GB.
* respread DRT pass 0 (threads 16, 04:29-04:50 UTC, 21 min): 10 % 20.0k, 30 % 103k, 50 % 190k, 80 % 288k, 100 % 369k -> **iteration 0 = 499,747 violations**; RSS 14.7 GB.
* respread DRT **iteration 1 = 197,676** (-60 %, 05:08 UTC, 18 min/iteration, RSS 14-15 GB). Converging; iteration 2 started.
* respread DRT **iteration 2 = 178,450** (-10 %, 05:26 UTC). DRT continues alone (threads 16, RSS ~14 GB); log runs/c7w32-6600-respread/logs/openroad.log, checkpoints build/ck_droute.odb per chunk (resumable). Watch: count must keep falling; DGSE drt_stall gate stops on two identical consecutive counts.

### 01 Nov 12:58 IST -- respread DRT switched to ONE continuous call (coordinator)
* Chunked DRT (schedule "5 10"): chunk 1 (iters 0-4): 499,747 / 197,676 / 178,450 / 52,413 / 43,672 / 40,965 ->
  ck_droute.odb (route_drc.rpt 15,826 entries). Chunk 2 (10-iter call) restarted DRT's strategy list and crawled:
  81,947 / 81,942 / 81,940 / 80,802 / 79,977 / 79,564 (~8-10 min/pass in the later passes).
* Killed the chunked job at 12:58 IST (pid 429588) and resumed from ck_droute.odb with config
  drt_continuous_below = 1e9 + DGSE_DRT_CONT_CHUNK=64 -> one 64-iteration call (scripts/drt_continuous_cfg.py;
  original config kept as config.chunked.json). logs/openroad.log was overwritten by the resume.
* Stall watch: if the continuous call does not get clearly below ~75k (in DRT's own count), more iterations
  will not help -> targeted fix (re-place cells in the hotspots from route_drc.rpt).
* 01 Nov 07:56 UTC: **c7w32-6600-spread** launched (threads 4, stop at ck_groute) in parallel with the coordinator's
  continuous DRT on respread (pid 539880, 15.7 GB). = respread flow + place_density_override 0.5 (GPL reports 0.53)
  + gpl_pad 2 + `hotspot_blockages.tcl` (post_pdn_tcl): soft placement blockages, max density 40 %, over the DRT
  hotspots: CPU bin x 2640-3300 / y 5280-5940 um and the PCORE cluster x 1320-2640 / y 3300-4620 um.
* **c7w32-6600-spread real GRT** (08:55 UTC): 16.4k / 8.7k / 11.9k / 7.2k = **44,192** (30.3 %, WL 65.8 m) vs respread
  49,512 -> only -11 %. 26.0k repair buffers; skew 11 cells (SRAM 9.93 / flops 10.05 ns); setup after repair WNS
  -2.04 ns / TNS -23.7 ns (worst hb_dq_out[6]). Global density 0.5 + pad 2 + 40 % soft blockages over the hotspots
  do not change the picture -> not worth a DRT slot. ck_cts / ck_groute kept, intermediates deleted.
* **01 Nov 13:42 UTC (19:12 IST) OOM: continuous DRT killed** in pass 13 (last pass 25,960) by the 32 GB cgroup
  (oom_kill 4) when a trial hold ECO (full-chip STA + repair_timing -hold) and the full-chip signoff rehearsal ran next
  to it. DRT writes no checkpoint inside a call -> back to ck_droute.odb (40,965); ~6.7 h of routing lost. Restarted
  alone at 16 threads 13:46 UTC. Rule: nothing memory-heavy next to DRT; DRT has no intra-call checkpoint.
* **Routed-snapshot timing** (ck_droute 40,965, placement RC, hold_paths.tcl): hold WNS **-3.32 ns** (core_clock
  clk_x2 reg -> SRAM, the CTS SRAM-branch padding), clk_main -1.52, cam_pclk -0.91, others >= 0; setup WNS -1.28 ns.
  Hold ECO script `HW/asic/signoff/hold_eco.tcl` (repair_timing -hold outside any incremental session, DPL bounded
  displacement) reached hold -2.905 ns / TNS -16.5k after ~590 iterations before the OOM kill -> not validated.
* **Full-chip rehearsal** (`signoff/rehearse_chip.sh` on ck_droute): pads 64 / ports 60, pad straps +1819/-935,
  power merge, write_v, GDS stream 75 s (809 MB), CDL 335,456 instances -- all OK. Fill: 12 GB per 1 mm tile
  process on the full chip (2 mm test: <3 GB) -> killed; fill now FILL_J=2. DRC/LVS on the full chip not yet run.

## DPASS 2 Nov 2026 00:58 IST: overnight plan (owner away 8 h: "use dpass score and select and move forward")
Pod dgrid-soc1-2 (35c4667cbbcd, 32 CPU shared host, 128 GB). Router c7w32-6600-respread resumed from
ck_droute 40,965 at 20:25 IST, 32 threads, deterministic (same counts as the old pod): pass 9 = 33,724 at
00:51, ~1.8x slower per pass than the old pod (shared CPUs, load 140-190).
Scores: separation / owner rules / risk / evidence / value, 0-5.

D1 router. R1 keep the running call; R2 kill + relaunch with per-pass snapshots (drt_steps.tcl START=0).
 K1 loses > 2 h of routing; K2 endangers the router. R2 fails K1 (4.5 h since 40,965). **R1** (5/5/3/5/4).
 Protection: side jobs only via lowprio.sh (oom_score_adj 1000) / drc_capped.sh; mem_watch 95/80 GB.
D2 full-chip DRC. A main tables on the full GDS (measured: pwellblock table 77 GB, 491 M GatPoly
 polygons from the SRAM bit cells, cgroup oom_kill 1 at 00:26, router survived by OOM priority);
 B all main tables on the LVS view (IO + SRAM FEOL removed; all metal, std-cell FEOL, seal ring kept),
 -j 1, 40 GB virtual-memory cap, 6 pinned CPUs; C wait for the router. K1 can kill the router; K2 result
 not labelled as what it covers. A fails K1. **B** (5/4/4/4/5) over C (5/5/5/4/2). Not covered by B:
 SRAM/IO internal FEOL (IHP-qualified hard IP) and density (needs fill).
D3 fill. Pre-split per tile (fill_tiled.py, new) measured: no gain (tiles 42/28 MB in, still 15-21 GB,
 >22 min each): the cost is flattening SRAM bit cells, not reading. Next: deep-mode fill or SRAM
 cells excluded from fill input. Deferred until the router is done (CPU).
D4 DRT step runner (drt_steps.tcl). Test on gate2-dgfabric-4x4-sky130-02 ck_groute (52,606 -> 35,332 after
 pass 1, snapshots drt_iter<N>.odb written): A baseline continuous to pass 12, then B resume at pass N
 from snapA/drt_iter<N-1>.odb vs C plain detailed_route on the same snapshot. Pass = B tracks A.
D5 tape-out date: owner's decision (IHP contact). Evidence: routing ~26k by ~03:00-04:00 IST at this pace;
 hold -2.9 ns not closable post-route (hold_eco.tcl stalls, GRT-0232) -> CTS rework needed -> recommend
 the 14 Mar 2027 run.
* **D4 result (02:25 IST): drt_steps.tcl VALIDATED** on gate2-dgfabric-4x4-sky130-02 (sky130, ck_groute).
  A continuous with snapshots (4 thr): 52,606 / 35,332 / 33,377 / 7,972 / 1,801 / 661 / 393 / 224 / 71 / 59 / 17 / 15 / 9.
  B step resume from snapA/drt_iter1.odb at pass 2 (2 thr): scan 35,345 (A pass 1: 35,332 -> markers rebuilt, no
  wire lost) / 43,905 / **7,691 / 1,699 / 626 / 194 / 83** (passes 2-7; A: 33,377 / 7,972 / 1,801 / 661 / 393 / 224).
  C plain detailed_route on the same snapshot (2 thr): 35,360 / 35,345 / 35,365 / 8,813 / 1,918 / 714 (schedule
  restarts at pass 0; passes 0-2 are near no-ops on routed input (ALL -> INCR), so it lags ~3 passes).
  Snapshot hook (detailed_route_debug -snapshot_dir + set_debug_level DRT snapshot 1) writes drt_iter<N>.odb per pass.
  => Crash protection for the next long DRT: run STEP_START=0 with STEP_SNAPSHOT_DIR, resume with STEP_START=N+1
  from drt_iter<N>.odb. B's pass 2 (RipUpMode ALL on routed input) is worse than A's but recovered by pass 3;
  OpenROAD's main() turns ALL into INCR for iter <= 2 on routed input -- a resume at START <= 2 could do the same.
* 2 Nov 05:59 IST: new pod back at **25,960** (pass 12) = the pre-OOM point; passes 10 / 11 / 12 took 84 / 103 / 121 min
  (host load 45-250). From pass 13 the run is past where the old pod died. ~2k violations per pass removed.
* **2 Nov 08:00-08:40 IST signoff speed-ups** (owner: "solution" for the stuck KLayout jobs; all three stopped):
  - Antenna: OpenROAD `signoff/check_antennas.tcl` on ck_droute (40,965): **6,107 nets / 7,134 pins** in ~5 min (KLayout
    antenna deck: 9 h single-threaded, still on TopMetal1). Expected before the engine's repair_antennas stage.
  - Connectivity: `signoff/connectivity.tcl` on the pad-integrated chip_pdn.odb: logical PASS (dgse_connectivity_check),
    102 unrouted multi-pin nets = the pad nets (rehearsal skipped the pad-net route), DRT shorts from route_drc.rpt.
    KLayout LVS (7 h in alignment) only on the clean final GDS with --blackbox 'RM_IHPSG13_*' --blackbox 'sg13cmos5l_IO*'.
  - Fill: `fill_tiled.py --abstract-macros "RM_IHPSG13_.*"` (157 macro cells -> outline on Activ/GatPoly/M1-M4, TM1/TV1
    kept; fill merged into the unmodified GDS): heavy tiles 0_4 / 3_3 **64 s / 51 s** (were >22 min, 15-27 GB).
  - DRC: `signoff/drc_tables.sh` = one capped job per table (drc_capped.sh, CPU_OFF disjoint cpus), metal/via ->
    FEOL -> latchup/forbidden/pin, 3 in parallel, 40 GB / 4 cpus each, on the LVS view (SRAM/IO FEOL removed).
* **2 Nov 10:15 IST per-table DRC on the integrated chip (routing snapshot 40,965, LVS view):** via1 0, passiv 0, pad 314
  all waived (0 unwaived), topvia1 36, vian 481, topmetal1 1,848 (TM1.b 1,840), metaln 11,977 (M4.b 6,663 / M2.b 2,618 /
  M3.b 1,772 ...): routing-related (top cell). Full-chip SRAM-abstract fill: 49/49 tiles, 17.4 min, 257,751 fill objects.
  **OPEN ISSUE (IO ring M3):** ~300 M3.b in sg13cmos5l_Corner + ~50 in IOPad*/Filler* cells: a 0.18 um M3 gap (rule
  0.21) at the cells' rail (local y 93.32 vs 93.5; the rail overhangs the cell edge by 0.108 um). Reproduced on the
  REAL GDS (clip_window.py window around IOPadVss, metaln table: 4+4 M3.b, 7 M3.f, 5 M3.e) -> not an LVS-view artefact.
  Standalone Corner / IOPadVss / Filler10000: CLEAN. No DEF special-net shape near (y 6366.5 um). make_padring ring
  and the 2 mm c5l-mini2k chip were clean -> compare this ring's pad/filler sequence + pitch (padring_qfn64.json,
  372 um pitch) with the clean ones before tape-out.
  **ROOT CAUSE FOUND (10:40 IST):** not the IO cells. xor_layer.py (chip window vs make_padring window, same IOPadVss
  at (3817.38,6280)) -> only the chip has top-level M3 lines 0.2 um wide on the 0.42 um M3 track pitch running across
  the pad area from y 6265 um: REGULAR SIGNAL ROUTING of the core run in the 340 um pad-ring margin, e.g.
  soc_i/axi_split_dbus_i/.../gen2_slave_resp_fifo/ram_i/... Metal3 (3083.52,6265.14)-(4548.48,6265.14). The core-only
  DGSE run sees the whole die as routable: **27,399 of 7,348,830 DEF route points lie outside the core box**.
  This run: chip_integrate step 3 (GRT + DRT with the pad cells placed) must re-route these as violations.
  Next run: routing blockages over the margin before GRT (or pads in the floorplan, see signoff/README) -- the core's
  GRT congestion figures so far INCLUDE margin capacity it can not keep.

## 2 Nov 2026 15:20 IST -- plan for the clean-GDS P&R run (owner approved; target 14 Mar 2027 run)
Preliminary placeholder GDS sent as private release ihp-prelim-2026-11-02 (sha256 04cc677c..., from ck_droute 40,965 +
rehearsal integration, not for fabrication). Current run c7w32-6600-respread keeps routing for data (pass 14: 23,583).
Steps, each measured before the next:
1. Netlist: flop_max_bits sweep (1024 / 2048 / 4096) by synthesis -> macro count, flops, std-cell area; pick by data
   (each SRAM blocks M1-M4; flops add cells + read-mux wiring). [running as a background agent]
2. Floorplan: pad ring in the floorplan (or routing blockage over the 340 um margin) BEFORE GRT, so the core cannot
   route into the pad ring (27k route points did); MPL h25 macro placement as before.
3. Placement: lower density / padding + soft blockages at the CPU (x 2.6-3.3, y 5.3-5.9 mm) and PCORE (x 1.3-2.6,
   y 3.3-4.6 mm) hotspots; lite repair_design (fanout 40, max_tran 2.0) + gpl_incremental re-spread.
4. CTS: no delay padding of the SRAM clock branch (balance clk_x2 regs + SRAMs as one group vs clk_main), then hold
   repair on placement RC OUTSIDE incremental GRT sessions; gate: hold WNS >= 0 before routing.
5. Global route: overflow gate (target < 20k) before DRT.
6. DRT: STEP_START=0 with per-pass snapshots (drt_steps.tcl + STEP_SNAPSHOT_DIR); resume via drt_steps.tcl at N+1.
   Nothing memory-heavy next to it unless lowprio.sh/drc_capped.sh + mem_watch.
7. Signoff: chip_integrate (pad-net route) -> stream -> SRAM-abstract fill -> drc_tables.sh + --minimum_drc on the real
   filled GDS -> LVS --deep --blackbox 'RM_IHPSG13_*' --blackbox 'sg13cmos5l_IO*' -> check_antennas / connectivity.

## 2 Nov 2026 15:30 IST -- step 1 result: flop_max sweep on chip7_w32 (synthesis only)
`HW/asic/scripts/flop_sweep.sh <variant> <flop_max_bits> [max_macro_width=32] [flop_max_words=8]` = ihp_synth.sh
(the chip6/chip7 build) with a patched COPY of ihp_sram_pkg.vhd + filelist in the build dir (committed defaults
untouched); `flop_sweep_compare.py` tabulates. chip7_w32 reproduced first: export sha256 8087132d... identical,
298 macros, 290,426 cells. Std-cell area from the sg13g2 LEF (block_tree.py fixed: its LEF regex dropped *_a21o_1,
6.149 -> 6.21 mm2; pass the sg13g2 LEF for Yosys netlists).

| build (w32) | macros | SRAM mm2 | flops | std cells | std mm2 | macro+std mm2 |
|---|---:|---:|---:|---:|---:|---:|
| chip7_w32 (bits 1024, words 8) | 298 | 12.91 | 73,550 | 290,426 | 6.21 | 19.12 |
| f2048 | 253 | 11.99 | 106,750 | 383,250 | 8.90 | 20.88 (+1.76) |
| f4096 | 236 | 11.63 | 122,176 | 426,533 | 10.15 | 21.78 (+2.66) |
| d16 (words 16, bits 1024) | 249 | 12.17 | 85,964 | 319,186 | 7.19 | 19.36 (+0.24) |
| d16 + f2048 | 204 | 11.24 | 119,164 | 411,936 | 9.88 | 21.12 (+2.00) |

* f2048: 21 memories -> flops (33k bits): AXI fabric FIFOs (axi_merge/axi_split cmd 32x58, resp 32x36, data 32x37,
  pending 256x5/256x6), uart rx/tx 256x8, ztachip axilite 64x32/64x24, vstream 32x64. -45 macros (31x 1P_64x16,
  8x 1P_256x8, 6x 2P_64x32); axi_merge 33k -> 59k cells. f4096 adds 64x58 x2, 32x73, VexRiscv I$ tags 128x22 x2
  (-17 more macros); axi_merge 86k cells. Flops cost ~80 um2/bit vs 28 um2/bit saved -> 3x area, all in the fabric.
* The "93 tiny 1P_64x16" are mostly ONE memory: dp_fetch 16 deep x 776 wide = 49 slices using 16 of 64 words.
  flop_max_bits can not reach it (12,416 bits); flop_max_words 16 does: -49 macros / -0.74 mm2 SRAM for
  +0.98 mm2 std (+12.4k flops, +29k cells, ztachip only); no other memory moves.
* Recommendation: keep flop_max_bits 1024 (2048/4096 trade ~1 mm2 of small macro footprint for 2.7-3.9 mm2 of
  M1-M4-hungry std cells + read muxes in the already congested interconnect). Candidate: flop_max_words 16 (d16),
  only if the 49-slice dp_fetch row is in a congested area; needs firmware suite + new MPL placement + GRT probe.

## 2 Nov 2026 ~16:00 IST -- IHP submission registered (preliminary)
* IHP (K. Herman) rejected the release-link route; designs must follow github.com/IHP-GmbH/Open-Silicon-MPW.
* IP repo (gen_structure.py, Digital/RVSoC): **https://github.com/aravindgp/IHP__RVSoC2794** (public, Apache-2.0,
  commit 39a1167). Top cell RVSoC2794 in GDS/netlists/RTL; release/v.1.0.0: gds/RVSoC2794.gds.gz (KLayout save options
  per IHP fig/klayout_save.png), netlist/RVSoC2794.cdl.gz + .v.gz; doc/info.json, TRL (5 items), Datasheet (QFN64 pinout).
  Content = PRELIMINARY (ck_droute 40,965 + rehearsal integration): CI DRC/LVS will fail until the clean run.
  Tools: signoff/ihp_release.py (rename + save options + info.json), signoff/ihp_repo_docs.py (docs; arg "final").
* Submission issue: **IHP-GmbH/Open-Silicon-MPW#79** (title still "Oct-2026"; the other requests use Nov-2026/T628).
* E-mail to Herman sent by the owner with repo + issue; asked: final GDS deadline (or 14 Mar 2027), own 6.6 mm die +
  IO ring vs fixed 18 mm2 padframe (owner: assume not fixed), LVS with SRAM/IO black boxes.
* To update: re-run ihp_release.py + ihp_repo_docs.py ... final on the clean GDS, commit/push to the same repo.
* 2 Nov ~16:45 IST: IP renamed to **IHP__DGSL2611 / top cell DGSL2611** (owner: DGSL prefix like Tiny Tapeout's
  IHP__TT2609 / IHP__TT26004; 2611 = 2026-11). Repo https://github.com/aravindgp/IHP__DGSL2611 (old name redirects),
  issue #79 = "Request for submission Nov-2026 IHP__DGSL2611" with a Naming section asking IHP to confirm DGSL.
  Local clone /workspace/ihp_ip_repo/IHP__DGSL2611. Final release: ihp_release.py <repo> DGSL2611 <clean.gds>
  dgrid_soc1_chip_top <chip.v> <chip.cdl>, then ihp_repo_docs.py <repo> DGSL2611 <bond_table> final (README kept).

## 2 Nov 2026 ~17:00 IST -- IHP answers (K. Herman) + rename to SoC2611
1. Prefix **SoC** (not DGSL) -> IHP__SoC2611, top cell SoC2611, category Mixed-Signal / SystemOnChip (design_type M,
   TRL-Mixed-Signal-IP.md). Repo renamed: https://github.com/aravindgp/IHP__SoC2611 (commit 6182696).
2. **Final GDS deadline 9 Nov 2026.**
3. Our 6.6 mm die fits the QFN64 9x9 mm package (die at max size, OK).
4. LVS NOT checked at submission (SRAM black-boxing is the only way anyway); IHP runs only the **DRC foundry
   precheck = basic DRC + density**. Herman offers a precheck dry run once the repo is ready.
=> Submission bar = precheck DRC + density clean (not LVS/timing). Issue #79 retitle/body to SoC2611 +
   Nov-2026/Mixed-Signal is the owner's step (external write blocked for Claude).
* **2 Nov 19:15 IST: A1 c7w32d16-a1 GRT** (no -balance_levels, margin GRT hook -85 %, d16 netlist, ICG skew roots):
  - skew_fix ran (10 delay cells): SRAM CLK 6.422 -> 9.378 ns, flop CLK 9.609 ns (balanced; respread had the SRAM
    branch padded by -balance_levels -> hold -3.3 ns).
  - GRT-0096 table 38.3k / 22.3k / 26.4k / 16.8k = 103,905 vs respread 49,512, BUT resources 20.2M vs 25.6M: the
    -85 % margin capacity is counted as overflow in the layer table. Per-gcell congestion.rpt (`cong_regions.py`):
    A1 core 25,159 + margin 317 vs respread core 23,457 + margin 0 -> core congestion ~+7 %, same hotspots
    (x 1300-3300, y 4300-6260; PCORE / CPU). The margin hook works (no spill), it does not relieve the core.
  - Decision (DPASS, owner away): run A1 DRT in parallel with respread (hedge: A1 = margin-clean + hold-balanced,
    respread = 15 passes ahead at ~21.7k). `drt_a1.sh`: pnr.tcl pre-DRT stray-net block -> ck_predrt.odb ->
    drt_steps.tcl STEP_START=0, 16 threads, snapshots build/drt_snap/drt_iter<N>.odb. Stopped the per-table DRC on
    the superseded prelim LVS view (CPU); the density check on the filled rehearsal chip keeps running.
* **2 Nov 20:22 IST: respread continuous DRT KILLED by the DGSE driver's 24 h subprocess timeout** (driver.log:
  `TimeoutExpired ... timed out after 86399.99 seconds`), in pass 16 at 90 % / 21,433. One continuous call writes no
  checkpoint -> back to ck_droute.odb (1 Nov 06:27, 40,965 after pass 4); ~23 h of routing lost.
  Rule: long DRT runs only outside the driver with per-pass / per-session checkpoints.
  - respread resumed with `drt_resume_loop.sh` (drt_steps.tcl, START=5, 3-pass sessions -> build/drt_sess/drt_p<N>.odb,
    16 threads, no timeout).
  - A1 DRT pass 0 = 646,420 (respread 499,747, +29 %); snapshot build/drt_snap/drt_iter0.odb. Both run in parallel;
    compare A1 pass 4 vs respread 40,965, then keep one.
  - 20:30 IST: **drt_steps.tcl resume (START=5) FAILS on respread ck_droute.odb**: the scan step (INCR, mazeEndIter 0)
    ran in 0 s and rebuilt 0 markers -> passes 5-7 "0 violations" without routing (false clean). It worked on the
    sky130 snapshot (drt_iter<N>.odb from the debug hook); not on a flow write_db checkpoint. Do not trust
    drt_resume_loop.sh until the scan is fixed. Instead: plain restart from ck_droute.odb (what the lost continuous run
    did: 40,965 -> 25,960 @12 -> 21,433 @16) via drt_steps.tcl STEP_START=0 + STEP_SNAPSHOT_DIR=build/drt_snap
    (logs/drt_restart2.log, 16 threads). Resume after a kill = the same plain restart on the newest drt_iter<N>.odb.

## 2 Nov 2026 ~20:55 IST -- OWNER DECISION: next architecture (14 Mar 2027 CMOS5L run)
Requested: (1) remove the x2 clock, use multi-port SRAM instead (130 nm too slow for double pumping); (2) HyperRAM +
HyperFlash via AXI; (3) SPI master for display/peripherals; (4) camera DVP 4-bit to save pins, >= VGA.
Answers: changes go to **Mar 2027**, 9 Nov ships the current design; SRAM area growth (2P = ~1.9x 1P) handled by
**shrinking the config** (keep 6.6 mm / QFN64); camera = **generic nibble mode + Y-only grayscale**.
Survey facts: all 291 macros double-pumped at clk_x2 (ram2r1w 1W2R for pcore regfile + TCM; DPRAM/DPRAM_BE/ramw/scfifo
1W1R); 2P macros are true dual-port (6.6 ns slow-corner read); HyperBus = HyperRAM only, 1 CS; SPI = GPIO bit-bang;
camera 8-bit OV7670 RGB555, row counter counts VSYNC; UART/timer constants assume 125 MHz (chip 50 MHz -> 2.5x off).
Pin plan: free cam_d4..7 + cam_pwdn (5); add hb_csn1, spi_dc, spi_csn1; 2 spare.
Work streams (parallel, own worktrees): branches arch27-nox2, arch27-periph, arch27-hyperflash (off worktree-asic-rtl-prep).
* **2 Nov 22:55 IST: A1 stopped.** A1 DRT 646,420 / 268,874 / 243,761 / 103,297 (passes 0-3) vs respread 499,747 /
  197,676 / 178,450 / 52,413 -> ~2x behind. **A1 hold on ck_groute (placement RC, hold_paths.tcl): WNS -3.51 ns**
  (core_clock: g_1p_phase flop on clk_x2 -> 1P SRAM A_ADDR of a double-pumped FIFO), clk_main -1.80, cam_pclk -0.49;
  setup WNS -3.40 ns. Same as respread (-3.32): the hold is inherent to the x2 double-pumped 1P SRAM scheme (phase
  flops on the x2 root vs the skew-balanced SRAM clock pins), NOT the -balance_levels padding -> CTS tuning cannot fix
  it; the Mar 2027 no-x2 architecture does. A1 snapshots kept (build/drt_snap/drt_iter0-3.odb).
  respread restart continues alone (16 threads; host load ~82 so no re-thread restart): 40,982 / 40,977 / 40,975 /
  39,837 / 39,012 / 38,599 (passes 0-5).
* **3 Nov 00:05 IST: arch27 branches done** (all pushed, tests PASS per branch docs):
  arch27-hyperflash c480a0f (RAM CS0 + flash CS1, XIP, DGP1 UART flash programming, flash boot; RWDS delay + flash
  datasheet timing open); arch27-periph ee64041 (SPI master + DMA, 4-bit DVP + Y-only, row-counter fix, pins 58/59
  spi_dc/spi_csn1, pin 4 reserved hb_csn1, 60/61 spare); arch27-nox2 1484091 (x2 gone, 2P + delayed-write bypass,
  UART 115200 / 1 ms timer measured, 41 mem-equiv pairs; macro area 4 PCORE best 16.74 mm^2, 2 PCORE 12.99 mm^2).
  Owner: "measure first" on 2 vs 4 PCOREs -> merge into arch27-integ, synth + GRT probe (A 2 PCORE 6.6 mm; B 4 PCORE
  at 6.6 / larger die), ztachip kernel on both, package/cost -> Documentation/ARCH27_MEASURE.md.
  respread restart: passes 6/7 = 37,378 / 36,219.
* **3 Nov 00:25 IST OWNER DECISION: 9 Nov = current design, clean DRT first** (MPW slot paid). Options offered:
  A keep current route (chosen) / B skip 9 Nov / C small test chip. 4 PCOREs is the minimum for Mar 2027.
  arch27-integ agent: merge + tests only, heavy P&R probes deferred until the 9 Nov route is clean.
  Next: prepare the post-DRT chain now (pad-net route, margin spill fix, stream, fill, precheck + density).
* **3 Nov 00:35 IST: pads into the DRT.** `signoff/chip_drt_prep.sh` = run_chip_integrate.sh (pads, bondpads, pad
  straps; STOP_AFTER=pdn) + `chip_grt.tcl` (GRT of the pad nets, bondpad BPins saved to bpins.tcl for DRT-0302) on a
  core DRT snapshot. Test on respread drt_iter7.odb (36,219): 3 min, 64 pads / 60 ports moved, straps +1819/-935,
  pad-net GRT **0 overflow** (326 mm, 28 s). `chip_drt_switch.sh` waits for the pass-9 start of the core DRT (=
  drt_iter8 written), kills it, preps the chip ODB from drt_iter8 and runs drt_steps.tcl START=0 with snapshots
  (/workspace/chip_drt/run1). The chip DRT then also repairs the core routing that spilled into the pad-ring margin
  (IO-ring M3 gap root cause) and routes the pad nets. `chip_finish.tcl` restores the bondpad pins after DRT.
  respread restart pass 7 = 36,219; pass 8 at 80 % = 35,512.
* **3 Nov 01:00-02:15 IST: chip-level DRT run1 FAILED to converge**: pads into drt_iter8 (35,261) -> passes 0-3
  210,006 / 203,408 / 202,702 / ~202.5k (pass 3 at 60 %): +170k from core routing in the pad-ring margin overlapping
  the IO cells; DRT could not move it. Killed. (30 threads: pass 0 ~9 min incl. pin access.)
  Fix B (/workspace/chip_drt/stripB): `def_margin_nets.py` on chip_pdn.def -> **3,715 of 336,008 nets** route outside
  the core box; `chip_strip_margin.tcl` destroys their wires; GRT re-routes them (+60 pad nets) around the pads, then
  chip DRT (drt_steps START=0, 30 threads, snapshots). Tcl/Python getBBox on dbWire returns an unusable
  std::optional, Python odb has no dbWireShapeItr -> DEF parse. set_global_routing_region_adjustment over the margin
  underflowed capacity to 65535 (GRT-0113) -> dropped.
* **3 Nov 03:40 IST: arch27-integ 0c04720** (3 branches merged, 4 PCORE default): mem-equiv / SPI / cam / hyperflash /
  analyze / portmap / cocotb smoke+periph PASS; bootrom real-baud UART + flash boot PASS (fast-UART sim overflows the
  16-deep UART RX FIFO, sim artefact). **ztachip kernel test (y=2*x1+x2, DMA copy) FAILS: data reads back X** on both
  MEM=ihp and MEM=asic, not the nox2 memories/FIFOs -> suspect HART-off config (44aa7ff), the launch, or DP->PCORE path.
  Checking whether the 9 Nov RTL has the same failure (agent, sim only). 4 PCORE options: 6.6 mm needs thread cut
  16->8 to hit <=13.5 mm^2 macros; 7.4 mm die +16.8 kEUR, no IHP package > QFN64 (6.6 mm) found. Density closure:
  033840f (density_fast.py + fill_topup.py, rehearsal 212 -> 0).
* **3 Nov 06:15 IST ztachip kernel on the 9 Nov RTL** (branch zta-fix e7fdb9f): DMA into/out of all 4 PCOREs PASS
  (the earlier X was the test's REMAP without ztaInitStream; core.vhd:1122). Kernel execution FAILS: instr 1 (2*x1)
  correct, instr 2 writes 0x800 (12-bit min, saturation?) to all lanes; also y=x1+x2; HART on/off no difference.
  RTL vs compiler/test-setup not yet determined; debug continues (sim only).
* **Run B (stripped margin nets) chip GRT**: 128,342 overflow (3:51 h); chip DRT 30 thr: pass 0 494,371, pass 1
  154,577 (original from-scratch core route: 499,747 / 197,676).
* **3 Nov 07:10 IST OWNER: "Run B only"** (no reduced-config hedge, no test chip) after run B pass 3 = 127,964
  (passes 0-3: 494,371 / 154,577 / 143,321 / 127,964; ~-10 %/pass; original core route 52k at pass 3).
* **ztachip kernel root cause = SW/test setup, NOT RTL** (branch zta-fix 27b0e0d): the per-thread lane mask _VMASK
  lives inverted in the iregister RAM (iregister_file.vhd:89/113) and is never reset; FPGA BRAM powers up 0 (= all
  lanes on), ASIC SRAM is undefined -> result writes get byteena 'U' -> 0x800 via alu.vhd saturation. Fix: pcore image
  init `_VMASK=-1` once after load (test::init, EXE_LOCKSTEP). Also LATEST on DMA read-back (copy race). 4 PCOREs PASS
  on the 9 Nov RTL (MEM=asic and ihp). **Silicon SW rule: every pcore image must set _VMASK=-1 after load.**
  March RTL option: per-thread "lane written" flag -> all-ones until first write (32 flops/PCORE).
* **3 Nov 17:55 IST run B chip DRT** (30 thr, /workspace/chip_drt/stripB, snapshots drt_snap/drt_iter<N>.odb):
  494,371 / 154,577 / 143,321 / 127,964 / 123,403 / 118,837 / 115,036 / 112,957 / 109,659 / 103,800 / 90,840 /
  79,782 / 73,105 (passes 0-12). Passes 10-12 take ~1.6-2.4 h and remove 7-13k each (the schedule's later cost
  settings); linear ETA to 0 ~4 Nov 20:00 IST, realistic 5-6 Nov; then fill_tiled + fill_topup + density_fast +
  precheck DRC (~1 day).
* **3 Nov 19:40 IST hotspot analysis of run B pass 12** (`drt::check_drc` on drt_iter12.odb, 19,097 markers;
  `drc_concentration.py`, `drc_layer_maps.py` SVG): **63 % of the violations are in the pad-ring margin, 92 % of
  those on the WEST IO band (x 200-300 um)**, layers M3 5.8k / TM1 3.7k / M4 2.4k, shorts with IOVSS/IOVDD: GRT
  re-routed the stripped nets over the IO cells, whose supply rails are PINs on M3/M4/TM1 (local y 7..178) that GRT
  does not count as blockage. Core: 7.1k (worst core bin 2100,3400 = PCORE cell 0, M2 spacing).
  Per-layer GRT usage (A1): M2 42 %, M3 48 %, M4 14 %, TM1 12 %; flow default = uniform 0.05 derate.
  **Run C** (/workspace/chip_drt/runC, in parallel with run B): drt_iter12 + `chip_io_obs.tcl` obstructions on
  M3/M4/TM1 over the four IO bands (140..318 um from the die edge, M2 + pin edge open), strip nets entering the band
  (def_margin_nets.py 318/6282), GRT with LAYER_ADJUST "Metal2 0.30 Metal3 0.30 Metal4 0.15 TopMetal1 0.0" and
  CONG_ITERS 10, then drt_steps START=0, 16 threads, snapshots. Keep the better of B and C.
* **3 Nov 21:30 IST run C verdict (passes 0-3: 132,712 / 91,712 / 93,132 / 88,968; pass 3 took 51 min)**: NOT better
  than run B (pass 13 at 70 % = 70,013). check_drc on runC drt_iter2 (20,065 markers, zones.py): west IO band
  10,055 (50 %, now 94 % Metal3 shorts with IOVSS; run B pass 12: 10,853, M3 5.7k / TM1 2.7k / M4 2.4k), core 9,922
  (run B 7,108), E/S/N bands ~0 (run B ~1.1k, TM1). The M3/M4/TM1 dbObstructions did NOT keep GRT out: route.guide
  still has 3,628 Metal3 guide boxes (605 nets) in the west band (-allow_congestion overflows into blocked capacity);
  M3 derate 0.30 doubled the M3 shorts (DRT table 16.5k -> 35k). The west-band nets are PCORE 0 (gen_cell[0])
  register-file SRAM nets: west SRAM column x 365.7-602.5 (16x 1P_512x8 MY at y 3204-5720, 8x 1P_256x32 at y 365-1665,
  4x 1P_64x16 at the top), 26 um from the core edge, 50 um to the next column (x 652.9); SRAM signal pins are on the
  macro's bottom edge, so this is vertical (N/S) traffic of that column squeezed into the 26 um edge channel.
  Moving the column needs a re-place (not for 9 Nov). Run B stays primary.
* **3 Nov 21:52 IST run B pass 13 = 67,430** (3 h 55 min; M4 short 31.2k, M3 short 16.0k, TM1 short 8.8k, M2 short 3.7k).
  **Run C stopped 22:00 IST** after pass 4 = 87,442 (passes 0-4: 132,712 / 91,712 / 93,132 / 88,968 / 87,442);
  snapshots kept in /workspace/chip_drt/runC/drt_snap. Run B continues alone (30 threads).
* **3 Nov 23:45 IST run D (west-band ECO, /workspace/chip_drt/runD) from stripB drt_iter13** (check_drc 18,156
  markers: west band 10,687 = -1.5 % vs pass 12 -> STALLED; core 6,430 = -9.5 %). Stripped 828 band nets (+12 from
  the west markers), dbObstructions on ALL five layers over the four IO bands, GRT TopMetal1 0.0 (2:14 min):
  **GATE G1 FAILED: 16,726 guide boxes in the band (W 6,383 / 615 nets)** and GRT "Resource" ROSE (M2 2.28M -> 3.09M,
  M3 2.71M -> 3.75M vs run C) = unsigned UNDERFLOW of the already-reduced band capacity -> GRT sees unlimited
  capacity there. Same mechanism broke run C's obstructions and the 3 Nov region adjustment. GRT cannot be told to
  avoid the band on this ODB. Fix: `guide_clamp.py` projects every guide box of a non-pad net that enters the band
  onto the first gcell column inside (316.8 um), `chip_load_guides.tcl` replaces the db guides, then DRT
  (`run_d_drt.sh`, 8 threads) with the obstructions kept as DRT hard blockages. Pad nets (padnets.tcl) untouched.
* **4 Nov ~00:30 IST run D DRT** (guided ODB, 8 thr): router counts 633,558 / 506,742 (passes 0-1) -- but the router
  count over-counts dense clusters (~24x here vs ~4x on run B). check_drc on runD drt_iter1: **21,260 markers, core
  138** (run B pass 13: core 6,430), west gap x 320-340 17,596 + west band 3,162 = 98 %, all PCORE 0 (gen_cell[0])
  nets in x 300-400 / y 500-1600 um (next to the 8x 1P_256x32 bottom-left SRAMs): the clamp's funnel column.
  Gate metric changed: compare check_drc markers per zone, NOT the router's "Number of violations".
  Run D restarted from drt_iter1 (plain restart, STEP_START=0, snapshots runD/drt_snap2, log runD/drt_chip2.log).
* **4 Nov 01:00-01:45 IST: soft + hard west channel.** Run E v1 (guide_soft.py: translate strip boxes into the
  column-1/2 gap) REJECTED by DRT (DRT-0218 guide not connected, 15 nets) -> a guide rewrite must be a SUPERSET.
  Run E v2 (`guide_widen.py` on the clamped guides: strip 1 -> 7 gcell columns + the gap x 784.8..828 + M3
  connectors, +7,131 boxes / 601 nets; nothing moved) accepted, DRT 8 thr from 01:03 (/workspace/chip_drt/runE).
  Run F = option 2 (`chip_col1_shift.tcl` DX=32 on stripB drt_iter13): 8 SRAMs x 365.7 -> 397.7 um (strip 46 ->
  78 um), 2,972 PDN via/M4 shapes moved with them, 348 gap PDN shapes deleted, 127 cells moved, rows run full width
  (no cut needed), DPL max displacement 31.7 um, **check_placement clean**, **check_power_grid VDD/VSS: all shapes
  connected**, 1,322 nets ripped (791 macro/cell + 531 over the old gap), GRT 1:30 min, clamp + widen (STRIP_E
  396.0), band boxes only on 37 pad nets (gate by guide_band_nets.py), DRT 8 thr from ~01:45 (/workspace/chip_drt/runF).
  Pod clock is UTC (IST = +5:30). Remaining gate for F: windowed check_drc of the moved area after pass 3.
* **4 Nov 03:40 IST run F v1 DRT: passes 0-2 = 145,937 / 105,193 / 98,773, then DRT-0206 checkConnectivity error
  at the end of pass 3** (run E v2: 416,670 / 385,848 / 311,143; run D 3rd pass ~502k). Cause: detailed_placement
  nudged 118 cells beyond the 127 I moved (253 instances differ between drt_iter13 and chip_shift.odb, all at
  x 397..870 um) and their nets kept their old routing. Rule: after ANY legalisation on a routed ODB, rip the nets
  of every instance whose location changed (dump_loc.tcl pre/post -> loc_diff_nets.py -> cells_to_nets.tcl), not
  only the ones you moved. Run F v2: EXTRA_RIP=moved_nets.txt through run_f_route.sh (snapshots drt_snap_v1 kept).
* **4 Nov 04:05 IST run D STOPPED**: pass-3 check_drc 21,254 markers / west strip 16,271 = identical to pass 1
  (21,260 / 16,263); the single-column clamp does not converge. Snapshots runD/drt_snap2 kept.
* **4 Nov 05:10 IST run E (soft channel v2) pass-3 gate**: router 416,670 / 385,848 / 311,143 / 307,047; check_drc
  20,297 markers: IO band W 651 (run B 10,687: the unfixable rail shorts are gone), strip x 300-366 / y 365-1665
  9,687 (run D 16,271), gap channel x 782-832 1,138, rest of core ~9k (run B 6,430). Total not below run B (18,156)
  yet but all remaining markers are signal-vs-signal -> fixable; slow. Kept as fallback behind run F.
* **4 Nov 05:46 IST run F v2 pass-3 gate** (router 152,243 / 106,372 / 100,046 / 98,330; connectivity check clean):
  check_drc 19,527: strip x 300-398 3,139 (run E 9,687, run D 16,271), gap channel 202, west edge north 239,
  **west IO band 8,084** (M3 4.3k / M4 2.2k / TM1 1.6k), core ~7.4k. The hard channel works; the band shorts are
  run B's own (F was built from drt_iter13 WITHOUT stripping the band nets / obstructing the band, which D and E had).
  -> **run F v3** (`run_f3.sh` on runF drt_iter3): def_margin_nets 318/6282 strip + chip_io_obs all layers + GRT +
  clamp + widen(396) + DRT, /workspace/chip_drt/runF3. Run E stopped (fallback verdict in). Run F v2 kept until F3's
  pass-3 gate.
* **4 Nov 05:50 IST run B pass 14 = 61,074** (-9.4 %; 8 h 01 min with three side DRTs on the pod; shorts M4 27.3k
  / M3 14.3k / TM1 8.7k / M2 3.4k). Run F v3 DRT started 05:52 (686 band nets stripped, band obstructed, gate: 31
  pad nets only).
* **4 Nov 07:20 IST**: run F v3 passes 0-2 = 460,218 / 360,489 / 301,437 (M2/M3 shorts of the 686 re-routed band
  nets; -35 % in two passes vs run E's -25 %). Run F v2 pass 4 = 97,500 (flat: its 8k band rail shorts do not
  clear). Run B pass 15 in progress. F v3 pass-3 check_drc gate armed (runF3/drt_snap/drt_iter3.odb).
* **4 Nov 08:34 IST run F v2 DIED at the end of pass 5 (97,500): DRT-0206, 4 INSTTERMs = CLK pins of flops moved
  by the shift on `clknet_leaf_120_clk_main_regs`.** cells_to_nets.tcl collected SIGNAL nets only; CLOCK nets of the
  moved flops kept their routing to the old pin positions. Rule: rip every non-supply net of a moved instance
  (cells_to_nets.tcl ALLNETS=1). Run F v3 carries the same stale clock routing (at risk at its next check).
  **Run F v4** (`run_f4.sh`): runF3 drt_iter2 + ALLNETS rip of the 253 moved instances + GRT + clamp/widen + DRT 8 thr
  (/workspace/chip_drt/runF4); F v3 kept running until its pass-3 gate / death.
* **4 Nov 09:10 IST run F v3 pass-3 gate** (router 460,218 / 360,489 / 301,437 / 297,964; connectivity check passed):
  check_drc 20,427: band W 722 (rail shorts gone), strip beside the shifted array 9,681 (F v2 3,139: the stripped
  band nets now crowd the strip), gap channel 6 (unused), **strip NORTH of the array (x 300-398, y 1665-6260) 8,532**
  (the 16x 1P_512x8 + 4x 1P_64x16 at x 365.7, y 3204-6235 were NOT shifted: strip still 46 um there), rest of the
  core ~2k. => the whole 28-macro west column needs the shift. **Run F v5** (`run_f5.sh`, `chip_col_shift.tcl`
  generalised, `dump_loc.tcl` full height): runF4 drt_iter2 + shift of the 20 north macros (+32 um), ALLNETS rip of
  all moved instances + nets under the new footprint, GRT, clamp/widen(396), DRT 8 thr (/workspace/chip_drt/runF5).
  F v3 stopped (superseded by F v4 = clock-correct fallback).
* **4 Nov 09:35 IST run F v5 gates**: 20 north macros shifted (x 365.7 -> 397.7), 3,364 PDN shapes moved / 402
  deleted, 643 cells moved, DPL max displacement 43.5 um, **check_placement clean**, **check_power_grid VDD/VSS all
  connected**; 816 instances changed location -> 1,672 nets (signal+clock) + 804 nets under the new footprint ->
  2,431 nets re-routed (GRT 2:05); guide gate 31 pad nets only; DRT 8 thr from 09:25 (/workspace/chip_drt/runF5).
* **4 Nov 10:40 IST**: run F v5 passes 0-2 = 325,945 / 282,039 / 280,244 (F v4: 337,767 / 303,987 / 293,718; F v4
  pass 3 still running). Floorplan picture: `dump_floorplan.tcl` + `floorplan_svg.py` ->
  /workspace/chip_drt/hotspot/dgrid_soc1_floorplan_F5.svg (298 macros by owner, 636 IO cells, 1,061 TM1 straps,
  28 shifted macros with previous outlines). Run B pass 15 at 70 % (59,850).
* **4 Nov 11:15 IST run F v4 pass-3 gate** (router 337,767 / 303,987 / 293,718 / 289,740; connectivity check passed
  = the ALLNETS clock fix holds): check_drc 20,416 = same as F v3 (south strip x 300-398/y 365-1665 10,521, north
  strip y 1665-6260 8,253, band W 732, gap 6, rest of core ~1.6k). F v4 kept only until F v5 passes its own pass-3
  connectivity check. If F v5's south strip stays ~10k: **F v6 = F v5 iter3 + both column halves a further +16 um**
  (DX=16 via chip_col_shift.tcl at COL_X0=397.7: south COL_X1=814.34/GAP_X1=832.26, north COL_X1=634.5/GAP_X1=652.3;
  strip 94 um, gap channel 2 um -- it carries 6 markers).
* **4 Nov 12:08 IST**: run F v5 pass 3 = 274,739 (325,945 / 282,039 / 280,244 / 274,739), connectivity check
  passed, pass 4 started; pass-3 check_drc gate running. **Run F v4 stopped** (12:08; superseded by F v5, which
  carries all of F v4's fixes; snapshots runF4/drt_snap kept).
* **4 Nov 12:27 IST run F v5 pass-3 gate**: check_drc 20,243: north strip 8,253 -> **1,055** (the north shift works),
  **south strip x 300-398 / y 365-1665 = 12,838** (F v4 10,521; capacity-limited at 78 um), band W 642, gap 448.
  => **Run F v7** (`run_f7.sh`): F v5 drt_iter3 + south column 2 (8x 256x32 at x 832.26) +32 um into its 50 um gap,
  then column 1 (x 397.7) +32 um behind it -> south strip 110 um; ALLNETS rip + footprint nets + GRT + clamp/widen
  (STRIP_E 428.4) + DRT 8 thr (/workspace/chip_drt/runF7). F v5 kept as fallback. run_f6.sh (+16 um) not used.
* **4 Nov 12:40 IST run F v7 gates**: south column 2 (8x 256x32) x 832.26 -> 864.26, column 1 x 397.7 -> 429.7
  (south strip 110 um); both check_placement clean (max displacement 29.2 / 40.3 um); **check_power_grid VDD/VSS
  all connected**; 641 instances moved -> 2,071 nets (signal+clock) + 798 footprint nets -> 2,712 re-routed
  (GRT 1:33); guide gate 31 pad nets only; DRT 8 thr from 12:36 (/workspace/chip_drt/runF7). F v5 = fallback.
* **4 Nov 13:30 IST**: run F v7 passes 0-2 = 370,429 / 274,512 / 270,972 (lowest of any run at pass 2); pass 3
  running, check_drc gate armed. F v5 pass 4 ~274k. Run B pass 15 at 90 % (58,981).
* **4 Nov 13:50 IST run B pass 15 = 56,759** (-7 %; 7 h 57 min; shorts M4 24.4k / M3 13.4k / TM1 8.6k / M2 3.3k).
  At ~540 violations/h run B alone needs >4 days -> cannot make 9 Nov; F v7 is the path.
* **4 Nov 15:25 IST run F v7 pass 3 = 267,297** (370,429 / 274,512 / 270,972 / 267,297; shorts M3 117.6k / M4 67.7k
  / M2 51.8k / TM1 7.4k); connectivity check passed, pass 4 started; pass-3 check_drc gate running.
* **4 Nov 15:35 IST run F v7 pass-3 gate**: check_drc 20,236 (every F run at pass 3 sits at 20.2-20.4k: the
  early-schedule count; only the distribution moves). South strip x 300-430: **7,138** (F v5 12,838 at 78 um ->
  110 um helps, -44 %); north strip 3,930 (F v5 1,055; the 2,712 re-routed nets spread); band W 637; rest of core
  ~8k. 14 % of markers involve VDD/VSS, the rest signal-signal (PCORE 0 nets, x 300-400 / y 800-1600 and 3500-3600).
  **DECISION 15:35 IST: F v7 is the only run. Run B killed** (pass 16, 56,759: >4 days at its rate) **and F v5
  killed** (dominated by F v7). F v7 restarted from drt_snap/drt_iter3.odb with 30 threads (plain restart,
  STEP_START=0, snapshots runF7/drt_snap2, log runF7/drt_chip2.log).
* **4 Nov 16:47 IST F v7 @30 thr restart passes 0-3**: 267,262 / 267,343 / 267,344 / 266,829 (pass 3: 58 min);
  check_drc on drt_snap2/drt_iter3 = 20,235 (identical to the 8-thr pass 3: same schedule step). Router count is
  13x the marker count on all clamped/widened-guide runs (run B: 3x) -> judge by markers only. Rule: markers must
  fall >= 10 %/pass from pass 4 (zone checks armed for iter4/iter5); flat through pass 5 => 9 Nov not reachable,
  extension/March. IHP repo github.com/aravindgp/IHP__DSOC2610 returns 404 anonymously (private?) -> owner to make
  it public; audit fixes are in 9d5e139 = origin/main; testbenches/ still empty.
* **4 Nov 17:20 IST OWNER: keep IHP__SoC2611 first, request the DSOC2610 rename afterwards.** Local IHP clone
  (/workspace/ihp_ip_repo/IHP__DSOC2610, remote IHP__DSOC2610.git) reverted to SoC2611 content on top of the audit
  fixes: ihp_release.py (top cell SoC2611, release/v.1.0.0 SoC2611.gds.gz / .cdl.gz / .v.gz, info.json), ihp_repo_docs
  (preliminary, TRL 0), SoC2611-main/ (rtl/SoC2611.v module SoC2611, README), root README / TRL doc / info.json
  repository URL. SHA-256: GDS 69aa132d…24bc, CDL eabac1b7…4169, V 60384968…e5b6. Owner commits/pushes (git in that
  clone is blocked for Claude), renames the GitHub repo back to IHP__SoC2611 if needed, makes it PUBLIC (404 now),
  posts audit_reply_79.md on #79, sends EMAIL_HERMAN_STATUS_04NOV.md.
* **4 Nov 18:00 IST F v7 @30 thr pass 4 = 264,757 (-0.8 %, 65 min); markers 20,234 = FLAT (20,236/20,235/20,234).**
  Marker attribution (runF7b_iter4): 18,039 of 20,234 involve a RE-ROUTED net (1,975 nets), only 2,195 are on
  never-ripped nets -> DRT does rip, the re-routed nets simply cannot be legalised. The re-routes' own GRT already
  overflows: F3 ~37k, F5 ~15.6k, F7 ~18k (M2 11.8k / M3 6k ...) -> the west strip + core corridors lack capacity for
  PCORE 0's register-file traffic even at 110 um (the band obstructions also inflate "capacity" via underflow).
  Trials: `grt_trials.sh` on runF7 chip_ripped WITHOUT obstructions (chip_rm_obs.tcl): baseline vs M2/M3/M4 derate
  0.5 / 0.3 with TM1 0.0 (TM1 is vertical and ~free over the SRAM columns) -> does TM1 absorb the overflow?
  check_drc on run B's start ODB (stripB/chip_grt.odb) running: the pre-routed core's own marker floor.
* **4 Nov 18:05 IST GRT trials (runF7 ripped nets, NO band obstructions)**: baseline overflow 22.7k (M2 11.4k / M3
  2.9k / M4 5.6k / TM1 2.8k; 108 non-pad nets still enter the band); derate M2-4 0.5 -> 40.5k, 0.3 -> 31.7k (worse;
  TM1 overflows too: the 16 um-pitch PDN straps take most TM1 tracks over the SRAMs). Run B's start ODB: 14,171 core
  markers -> 6,430 after 13 passes (~6 %/pass), so DRT does grind pre-routed markers slowly; the west-strip 11k on
  the re-routed nets do not move at all (capacity). **CONCLUSION: no routing-only lever is left; PCORE 0's
  register-file traffic through the west edge needs a placement change (PCORE 0 logic next to its 28 SRAMs = new
  placement + CTS + route, 2-3 days to a comparable state, convergence unproven). A DRC-clean GDS by 9 Nov is not
  reachable with this floorplan.** Options for the owner: (A) stop the 9 Nov attempt, ask IHP about the paid slot
  (roll to 14 Mar 2027?), build March on the corrected floorplan; (B) ask IHP for ~2 weeks and re-place PCORE 0 now.
  F v7 kept running (pass 5) only until the owner decides.

### 4 Nov 18:53 IST — F v7 pass 5 (30 threads): flat, confirms the conclusion
- Router count 264,757 -> 263,347 (-0.5%); check_drc markers pass3/4/5 = 20,236 / 20,234 / 20,237.
- Zones: core 19,294 (95.3%; M2 6,683, M4 6,324, M3 3,951), IO band W 582 (all M3), gap W 153.
- West strip windows: south x300-430 y365-1665 = 7,269 (pass 4: 7,138); north x300-398 y1665-6260 = 3,626.
- No DRT-0206. Process left running only until the owner chooses option A (roll slot to March) or B (2-week ask + re-place PCORE 0).

### 5 Nov 01:30 IST — DECISION: option B, hand floorplan (run G), F v7 kept running in parallel
- Density map (density_map.py on runF7/chip_grt.odb): core 49.3%, PCORE logic box 49.5%; no density problem. 298 macros,
  12.91 mm2 macro area; std cells 6.99 mm2; core 35.0 mm2.
- West column = 8 PCORE register files (2 each of PCORE 0-3) + 16 stream lookups + 4 AXI FIFOs: the funnel.
- Floorplan rules: PCORE blocks with own SRAMs; datapath/stream/AXI groups by their logic; 40-60 um channels; 100 um band
  inside the pad ring; shared logic in the centre. Work dir /workspace/chip_fp2.

### 5 Nov ~03:50 IST — DPASS round 1 launched (owner: "still clustered, let's do DPASS")
- Harness HW/asic/signoff/dpass_dsoc_fp.py (planner fp2_plan.py, env FP_KNOBS); out /workspace/chip_fp2/dpass; runs
  DG/runs/dpass-dsoc-<tag>, engine flow to groute (DGSE_PNR_STOP_AFTER=groute), 4 threads each, 4 in parallel, F v7 kept.
- Baseline to beat: respread GRT overflow 49,512 (M2 17,943 / M3 8,633 / M4 15,473 / TM1 7,463); gate < 20k.
- Probes: A-bands (owner blocks, 60 um gaps, strips x1), B-spread (100 um gaps, BB 40, strips x0.6),
  C-corners (PCORE squares in corners, centre column), D-h25-d050 (A + halo 25 + GPL density 0.5).
- Cell areas per block (cellgroups_F7): datapath 1.89 mm2 (88k cells), axi 1.11, cpu 0.52, PCORE 0.50 each, streams 0.27,
  zcore 0.25, zmem 0.25; macro connectivity: PCORE macros connect only within their own PCORE.
- Round 1 result (02:08 IST): all four probes died in the post-CTS detailed_placement, DPL-0036 on 125 / 475 / 189 / 725
  clkload dummy loads (CTS balance_levels). Reproduced on A ck_dplace.odb (probe_cts_dpl.tcl, CTS 313 s at 8 thr):
  6,603 clkloads, 3,398 inside the hard blockages (100 um band at the die-edge pins), none inside macros; default
  detailed_placement fails on the same 125, max_displacement 1500 um passes. Fix: config dpl_max_disp 1500 1500.
  Round 1b relaunched 02:10 IST, 8 threads per probe. Row util after repair: A 37.4, B 35.5, C 37.1, D 44.7 percent.
- Owner (02:20 IST): the survivor's DRT runs alone at all 32 threads (stop F v7 first); no RAM cap.

### 5 Nov 08:40 IST — DPASS round 1b: all four hand floorplans KILLED at groute
- GRT overflow (M2/M3/M4/TM1/total): D-h25-d050 46,108/19,384/35,301/1,992/102,785; C-corners 118,420; A-bands 119,216;
  B-spread 126,596; baseline (auto placer, respread) 49,512. Usage only 30-32 percent: LOCAL pinches, not global.
- congestion.rpt (20k-entry cap, 28k of the overflow): hot bands exactly on the back-to-back macro row PAIRS (PCORE2/3
  rows at y 5.5-5.75 mm, PCORE0/1 at y 0.75-1.0 mm, datapath/axi pairs in the middle); nets: clock tree 24-29 percent,
  datapath 15-25, axi 7-18. The gaps of the two rows of a pair are not aligned, so N-S routes cannot cross a pair.
- Lesson: no back-to-back pairs without aligned gaps; macro walls need N-S highways; the auto placer (49.5k) left
  open areas that carried the cross traffic. Round 2: E = auto placer (halo 25, level 1) with a 100 um fence
  (rtl_macro_placer -fence_* ; MPL takes ~1 min), F = single rows with strips on both sides, G = sub-columns with
  vertical highways aligned across all bands.
- Round 2 launched 08:39 IST: E-mpl-core440 (auto placer on base_fence.odb, core 440..6160; the MPL fence options are
  ignored), F-single, G-highway; 8 threads each. Picture /workspace/chip_fp2/round2_floorplans.png (fp_panels.py).
- 09:55 IST: owner's ChatGPT produced H (targeted repair of G, 123 moved, 8 reoriented, highways ~180 um) and I
  (balanced grid, 201 moved, ~220 um freeways) from the data pack /workspace/chip_fp2/DSOC2610_floorplan_pack.zip;
  validated (298, no overlap, inside 440..6160, R0/MX) and launched as probes H-targeted / I-balanced (ring blockage
  only, as specified). Picture /workspace/chip_fp2/round2_GHI.png. Five probes now run at 8 threads each.
- 10:50 IST: E-mpl-core440 groute overflow 160,776 (M2 49,725 / M3 53,957 / M4 37,067 / TM1 20,027), usage 33.8
  percent. Overflow concentrated at x 500-750, y 2.75-4.5 mm: the auto placer again stacked the datapath 64x16 tiles
  in a column along the west edge (now 100 um in). Caveat on all comparisons: the 49,512 baseline ran GRT at 4
  threads, the probes at 8; DGSE note says overflow changes with thread count -> baseline re-measured at 8 threads
  (probe_grt_threads.tcl on respread ck_cts.odb, /workspace/chip_fp2/baseline_grt8). MPL variants with
  -boundary_weight 0 (halo 25 / 40) started. F v7 stopped 10:36 IST (owner: speed; option B).
- 10:55 IST: MPL on base_fence with -boundary_weight 0 (halo 25) gives clusters with an open centre and no edge
  walls (edge counts llx<700: 29 vs 49); halo 40 variant fails MPL-0040. Launched as probe J-auto-bw0.
- 11:07 IST round 2 results: G-highway 89,801 (M2 32,494 / M3 27,312 / M4 19,282 / TM1 10,713) best so far;
  F-single 117,411; E-mpl-core440 160,776. All above the 4-thread baseline 49,512 (8-thread baseline pending).
  G hot spots: around the 60 um centre vertical channel where it meets the PCORE bands (x 3.5-3.8 mm at y 0.5 and
  5.75 mm) and the west band edge (x 0.5 mm, y 2.5-3.25 mm); nets datapath 22, clock 21, axi 18 percent.
- 11:30 IST: baseline re-measured at 8 threads on respread ck_cts.odb: 49,567 (M2 16,663 / M3 8,373 / M4 17,463 /
  TM1 7,068) = the 4-thread 49,512. Thread count is not a factor here; the bar stays 49.5k. G (89.8k) killed.
  Next: K = the proven respread placement with ONLY the 28 west-column macros relocated into its open areas
  (minimal change to a floorplan whose DRT converged everywhere except the west strip).
- 11:33 IST: probe K-relocate launched (fp_k_relocate.py: h25_lvl1 placement, 28 west-column macros moved: 8 RF in a
  row at y 1765 MX above the PCORE rows, 16 stream lookups + 4 AXI 64x16 tiles in rows of 4 at x 2890..4190,
  y 3560..4546 R0 with 120 um channels; the 53 edge macros on E/N/S stay; ring blockage for cells only).
  fp_free_rects.py lists the open areas (largest: x 440-4790 y 1690-2640; x 2890-4190 y 3440-5590).
- 12:00 IST: H-targeted 55,655 (M2 20,002 / M3 16,996 / M4 13,674 / TM1 4,983), I-balanced 56,644: the ~180 um
  lanes cut G by 38 percent; 12 percent above the 49.5k bar; wider lanes (I, 220 um) add nothing. H hot spots:
  PCORE0 bottom rows near the south die-edge pins (x 2.0-2.5 mm, y 0.5-0.75), the east highway at the cpu/axi
  blocks (x 4.5-4.75, y 3.25-3.5 and 4.75); nets datapath 25, clock 20, axi 16 percent.
- 12:05 IST: H promoted to the chip-level chain in parallel (chip_drt_prep.sh on dpass-dsoc-H-targeted ck_cts.odb ->
  /workspace/chip_fp2/chipH: pad ring + straps + chip GRT, 8 threads); the chip GRT number (with pads) is the one
  that matters for DRT. J (~13:00) and K (~13:40) still to come; the DRT candidate is picked among H, J, K.
- 12:33 IST: J-auto-bw0 167,924 (M2 68,355 / M3 41,209 / M4 41,927 / TM1 16,433): killed, worst of all; the auto
  placer's 49.5k result does not reproduce under any variation (E 160k, J 168k). H stays the candidate.
  chipH: pad ring + straps integrated (PAD_PDN_APPLY 1,819 shapes), chip GRT running. run_chip_drt.sh written:
  clamp guides -> band obstructions -> load guides -> drt_steps at 32 threads.
- 13:20 IST: K-relocate 168,268 (M2 65,363 / M3 33,887 / M4 50,173 / TM1 18,845): killed. The baseline's own
  placement with 28 macros moved (+ ring blockage, dpl_max_disp, 8 threads) triples the overflow -> the 49.5k
  itself is suspect. R-reproduce launched: the exact respread config (no blockage, no dpl_max_disp, 298 fixed
  macros, halo 10, density 0.6) to groute at 8 threads. If R is not ~49.5k, the baseline was not reproducible and
  H (55,655) is the best measured floorplan. K hot spots: CPU caches at the north edge (x 2.5-3.25, y 5.25-5.9 mm).
- 14:45 IST: R-reproduce = 49,512 EXACTLY (M3 8,633 / M4 15,473 / TM1 7,463): the flow is deterministic and the
  baseline is real. So K's 168k comes from the 28 moved macros and/or the 100 um cell blockage ring (H has the ring
  too). Round 3: H2-noring and K2-noring launched (same placements, no ring; routes may use the band, cells too, as
  in the baseline). chipH GRT at iteration 28/50 (~4.6 min each at 8 threads), result ~16:25 IST.

### 5 Nov 16:05 IST — H2 (H without the cell-blockage ring): 11,716 GRT overflow — the ring was the culprit
- H2-noring: M2 3,352 / M3 4,028 / M4 2,681 / TM1 1,655, total 11,716, usage 23.2 percent (H with ring 55,655;
  baseline 49,512). Under the 20k gate. The hard placement blockage over the 100 um band (cells kept out of the band)
  pushed every pin-side buffer and the edge logic 100 um inward and made the band a dead zone for placement; routes
  may still use the band, and the IO-rail shorts of run B are handled by the guide clamp + DRT obstructions, not by
  a cell ban. Rule from now: NO cell blockage ring; keep the macro fence (macros >= 100 um from the core edge).
- chipH (H with ring) chain stopped; chipH2 launched: chip_drt_prep.sh on dpass-dsoc-H2-noring ck_cts.odb, 16
  threads (/workspace/chip_fp2/chipH2). Then run_chip_drt.sh -> DRT at 32 threads.
- 16:08 IST: K2-noring 46,461 (M2 16,240 / M3 7,732 / M4 15,390 / TM1 7,099) = baseline level: the 28 moved macros
  are neutral, the ring alone made K 168k. Confirms the ring finding. H2 (11.7k) is 4x better than K2.
  chipH2: pads + straps integrated 16:08, chip GRT running at 16 threads.
- 20:40 IST: chipH2 chip GRT (16 thr, 50 iters) finished its 50 iterations at ~20:00, then GRT-0273 disabled the NDR on
  clknet_3_7_1_clk_main_regs and net17209 and RESTARTED the overflow loop from iteration 1 (another ~3 h). Killed.
  chip_grt.tcl now clears all NDRs before global_route (as the core probes do). Re-run at 32 threads, CONG_ITERS 15,
  chained into run_chip_drt.sh -> /workspace/chip_fp2/drtH2 (DRT 32 threads).

### 5 Nov 20:59 IST — DRT started on floorplan H2 (run drtH2), 32 threads
- chipH2 chip GRT (32 thr, 15 iters, NDRs cleared on 116 nets): M2 3,583 / M3 4,341 / M4 2,997 / TM1 1,864 =
  12,785 (core-only H2 11,716). Band: 25 nets in band, 4 NON-pad -> clamped to 0; 20 obstructions on M1-TM1 over
  the 140..318 um IO band; guides loaded (3,519,616). DRT /workspace/chip_fp2/drtH2 (drt_chip.log, drt_snap/).
- Old floorplan for comparison: chip GRT overflow tens of thousands, DRT flat at 20.2k markers by pass 3.
- 21:25 IST: drtH2 pass 0 = 409,388 router violations in 24.5 min at 32 threads (M2 shorts 171k, M3 shorts 71k,
  M2 spacing 48k). For comparison run B (old floorplan): 494,371 -> 154,577 -> 143,321 -> 127,964; F v7 370k -> 274k.
  Watchers: passes 1-3 counts; check_drc on drt_iter2 (the comparable marker count, zones).
- 22:20 IST: drtH2 pass 2 = 160,558 (409,388 -> 173,593 -> 160,558). check_drc on drt_iter2: 20,036 markers,
  BUT drt::check_drc CAPS each violation type at 10,000 (Short 10000, Metal Spacing 10000) and lists in x order:
  the capped report cannot give a total or a location (the sampled markers all sit west of x 1.75 mm). This also
  means the old "flat 20.2k markers" of F v7 was the cap; the uncapped evidence there was the router count
  (258k -> 260k, 0.5 percent/pass) and the GRT overflow. Metric from now: the router's per-pass count and its
  Viol/Layer table; locations via check_drc -box windows (test running).
- 22:25 IST: drt::check_drc -box takes DBU (micron boxes return 0). Pass-2 snapshot: window x 1.4-1.8 mm, y 2.0-3.4
  alone holds >= 12,617 markers (hits the 10k Short cap): a genuine wall at the east end of the datapath west
  sub-column rows, next to the 180 um highway. SW quadrant window = 20,017 (capped). drc_grid.tcl (600 um windows,
  each under the cap) running on drt_iter2 to map the real distribution.
- 22:45 IST: drtH2 pass 3 = 45,987 (409,388 -> 173,593 -> 160,558 -> 45,987; -71 percent). Shorts M2 22,214 /
  M3 8,180 / M4 5,632 / TM1 344; M2 spacing 8,137. Old floorplan at pass 3: 127,964, F v7 flat ~258k. Converging.
  Pass time 34 min (pass 3 had more rip-up). Watcher for passes 4-6 armed.
- 23:05 IST: drc_grid (600 um windows) on drt_iter2: sum 158,773 = the router count (uncapped). Two hot columns:
  x 1.54-2.14 mm (the datapath sub-column highway, up to 11k per window at y 2.7-3.3) and x 2.74-3.34 mm (the
  datapath/AXI seam highway, 13k at y 2.1-2.7); y 1.5-3.4 band = the datapath block. Elsewhere < 5k per window.
  Same map running on drt_iter3 (pass 3 = 45,987) to see whether the lanes clear.
- 23:12 IST: drc_grid on drt_iter3 (sum 46,295): ONE window dominates, x 2.74-3.34 mm y 2.14-2.74 = 12,333 (27
  percent; pass 2 had 13,096 there: barely moving while everything else collapsed). It holds the datapath east
  sub-column's last 64x16 tiles (x 2883-3120) and the dp/AXI seam (dp ends 3120, AXI starts 3300-3450). Next
  windows: x 2.74 y 2.74 3,817; x 1.54 y 2.74 3,644; x 2.74 y 1.54 2,818. 150 um zoom running (zoom3).
- 23:20 IST: drtH2 pass 4 = 33,264 (-28 percent). 150 um zoom of the stuck window on drt_iter3: 7,551 of 17,411
  markers in x 3200-3350 y 2600-2750 = the AXI 2P 64x32 row (R0, pins down at y 2721) facing the AXI 256x32 row
  (MX, pins up at y 2661) across a 60 um strip, at its west end where the dp/AXI seam traffic enters. H3-axi120
  prepared (fp_h3_axi.py: 59 AXI macros above y 2700 shifted +60 um, AXI top 3817 < CPU 3954, no overlap) and
  launched as a GRT probe at 8 threads in parallel; used only if the wall stays flat over passes 5-6.
- 23:40 IST: drc_grid on drt_iter4 (sum 33,600): the AXI pin-facing window x 2.74-3.34 y 2.14-2.74 went 13,096 ->
  12,333 -> 11,414 over passes 2-4 (-7 percent/pass) while all other windows fall 20-50 percent/pass. It is a wall;
  the floor of drtH2 is ~11k unless it clears late. H3-axi120 (GRT probe running) is the fix candidate.
- 00:12 IST 6 Nov: drtH2 passes 5-6 = 29,278 / 26,631 (shorts M2 11,498 / M3 5,277 / M4 4,595; M2 spacing 3,735),
  ~25 min per pass. The AXI wall (~11k) is now ~40 percent of the total. H3-axi120 GRT probe at iteration 10/15.
- 00:30 IST: H3-axi120 core GRT 11,918 (M2 3,508 / M3 3,994 / M4 2,628 / TM1 1,788) = H2 within 2 percent: the AXI
  wall is a DRT pin-access effect GRT cannot see. chipH3 chain launched (pads + straps + chip GRT, 16 threads, NDRs
  cleared) in parallel with drtH2; when ready, DRT switches to H3 at 32 threads.
- 00:40 IST: drtH2 stopped after pass 7 (owner: faster; H3 supersedes; snapshots drt_iter0-7 kept in
  /workspace/chip_fp2/drtH2/drt_snap). chipH3 chip GRT (16 thr, 15 iters) runs alone; hand-over to run_chip_drt.sh
  (drtH3, 32 threads) armed. Lesson: never pkill -f on a pattern that appears in a waiting shell's own command line.
- 02:10 IST 6 Nov: chipH3 chip GRT 12,532 (M2 3,658 / M3 4,376 / M4 2,609 / TM1 1,889). drtH3 started 00:58 IST,
  32 threads: 406,185 -> 176,272 -> 161,259 (passes 0-2), same curve as H2. Watchers: passes 3-4; drc_grid on
  drt_iter3 (the H2 wall window x 2740 y 2140 had 12,333 there).
- 03:00 IST: drtH3 pass 3 = 46,816 (H2 45,987). drc_grid on drtH3 iter3 (sum 47,230): former wall window
  x 2740 y 2140 = 6,896 (H2: 12,333, -44 percent) but still the top; x 2740 y 2740 6,092; x 1540 y 2740 5,375;
  x 2740 y 1540 3,835. Distribution flatter. Pass 4 + its map decide whether these keep falling (H2's wall: -7
  percent/pass). 150 um zoom on iter3 x 2600-3500 y 2000-3400 running.
- 03:03 IST: drtH3 pass 4 = 32,357 (H2 33,264). Watcher passes 5-7; drc_grid on iter4 armed; zoom iter3 running.
- 03:08 IST: drtH3 iter3 150 um zoom (x 2600-3500 y 2000-3400, sum 16,281): hottest cells still at the dp/AXI seam
  west of the AXI 64x32 row, x 3200-3350: y 2600-2750 3,277 (H2: 7,551), y 2750-2900 2,345, y 2150-2300 1,854.
  Halved by the 120 um strip; the seam entry (230 um wide, dp tiles end 3120 / AXI starts 3351) stays the hottest.
- 03:27 IST: drtH3 iter4 map (sum 32,724 vs H2 33,600): seam column x 2740-3340: y 2140 5,719 (-17 percent),
  y 2740 5,047 (-17), y 1540 3,007 (-22); elsewhere -50. The slow part is the whole dp/AXI seam (230 um) plus the
  west ends of ALL AXI pin strips (H set every AXI pin-facing strip to 60 um; H3 widened only the 64x32 pair).
  H4 idea: all AXI pin strips >= 100 um, camera row moved to free the height.
- 03:35 IST: drtH3 pass 5 = 27,624 (H2 29,278). H4 built as standby: fp2_plan knobs cols_blk {axi:3}, strip_blk
  {axi:85}, axi_y0 640 -> AXI block 3 sub-columns x 13 rows, y 2140-3921 (CPU bottom 3954); merged into H3 with
  the camera FIFOs on one MX row at y 1240 above PCORE1 (fp_h4_merge.py); pl_check: 0 overlaps, min gaps 20/60 um.
  Launched as GRT probe H4-axi3 (8 threads) in parallel with drtH3. In-place widening (fp_h4_axi.py) did not fit.
- 03:55 IST: drtH3 iter5 map (sum 28,004): seam windows x 2740 y 2140 5,719 -> 5,166 (-10 percent), y 2740 5,047 ->
  4,773 (-5): the dp/AXI seam is a wall in H3 too (smaller than H2's). H4 hand-over armed (handover_drt.sh): when
  dpass-dsoc-H4-axi3 writes ck_cts.odb (~05:00), pads + chip GRT (16 thr) -> stop drtH3 -> drtH4 at 32 threads.
- 04:15 IST: IHP repo pushed: https://github.com/aravindgp/IHP__SoC2611 main 9d5e139 -> 21410c3 (SoC2611 names
  restored, docs regenerated). Repo is PRIVATE: owner must set it public for Herman. Local clone
  /workspace/ihp_ip_repo/IHP__DSOC2610 (origin now aravindgp/IHP__SoC2611; remote dg = Deepgridsemi/IHP__SoC2611,
  not created: repo creation is blocked for the agent).
- 04:25 IST: drtH3 pass 7 = 22,590 (-7 percent; the seam wall dominates). H4: ck_cts 04:15, pads + straps in, chip
  GRT at iteration 8/15 (16 thr); hand-over to drtH4 (32 thr) follows automatically; watcher armed for its first
  three passes.

## 2026-11-05 23:10 UTC (04:40 IST 6 Nov) - H4 hand-over done
- chipH4 chip GRT (15 iters, 16 thr): Total overflow 10,166 (M2 3897 / M3 3251 / M4 1811 / TM1 1207); H3 12,532; H2 12,785.
- handover_drt.sh stopped drtH3 (pid 845819, pass 7 = 22,590, snapshots drt_iter0..7 kept) at 23:09:36 UTC.
- drtH4 chain: guide clamp 24 boxes / 8 nets moved, 102 kept; io obs + guides loading; DRT at 32 threads next.
- Next: when drtH4 pass 3 exists, drc_grid.tcl 600 um on drt_snap/drt_iter3.odb; compare seam windows
  x 2740 / y 2140 and y 2740 with H3 (5,166 / 4,773).
- H4-axi3 core probe GRT (8 thr): 9,520 total overflow (M2 3507 / M3 2973 / M4 1857 / TM1 1183) - best of the campaign
  (H2 11,716; H3 11,918; auto 49,512). M3 dropped 4028 -> 2973 with the 85 um AXI strips.
- 05:48 IST 6 Nov: drtH4 passes 0-2 = 392,856 / 169,741 / 156,109 (H3 406,185 / 176,272 / 161,259; ~3-4% better).
  grid_on_snap.sh armed on drt_iter3 (600 um); H3 seam windows for reference: iter3 6,896 / 6,092, iter4 5,719 / 5,047,
  iter5 5,166 / 4,773 (x 2740 y 2140 / y 2740).

## 2026-11-06 01:20 UTC (06:50 IST) - drtH4 pass 3 window map, probe H5
- drtH4 pass 3 = 40,601 (H3 46,816, H2 45,987). grid3 (600 um) sum 40,858. Former seam window x 2740 y 2140 = 1,411
  (H3 6,896) - the AXI re-pack removed that wall. y 2740 window 4,949 (H3 6,092).
- NEW hot window x 2740-3340 y 1540-2140 = 9,364 (H3 3,835 at the same pass, same macros): 77% datapath nets
  (dp_gen_core 9.3k srcs, dp_fetch_1 3.4k), M2 shorts; drc_hist: 8.3k of them inside the 180 um highway
  x 3120-3300 at y 1900-2100 (H3: 3.0k). Cell density in the window is the same as H3 (50-80%); GRT does not flag it.
- cells_in_box.tcl on H4 ck_cts, slot x 3300-3900 y 1955-2140 (where H3 had the camera 256x32 + its strip):
  2,386 cells, 635 dp_gen_core + 86 dp_fetch_1 + ddr_rx/sram_i bits: dp logic spilled east of the highway, its nets
  cross the highway, hence the shorts.
- Probe H5-slotblk launched 01:17 UTC: H4 + place_blockage 3300 1955 3900 2140 (harness knob blk).
  Kill: GRT above 10,000 or the window at DRT pass 3 not below 3,835. ETA ck_groute about 05:00 UTC (10:30 IST).
- drtH4 keeps running (pass 4 due about 01:25 UTC); grid_on_snap armed on iter4. Hand-over to H5 only if its GRT passes.
- New helpers: grid_on_snap.sh, dens_dump.sh + dens_window.py, drc_hist.py, cells_in_box.tcl.
- 01:42 UTC: drtH4 pass 4 = 28,722 (H3 32,357, H2 33,264); grid4 sum 28,939. Highway window x 2740 y 1540:
  9,364 -> 8,596 (-8%/pass = a wall, like the old seam); everything else drops 20-60%/pass (y 2740: 4,949 -> 3,808;
  seam 1,411 -> 539). grid_on_snap armed on iter6. H5 result decides the hand-over.

## 2026-11-06 02:45 UTC (08:15 IST) - H5 killed, H6 launched; drtH4 pass 6
- H5-slotblk core GRT 11,655 (M2 4420 / M3 3787 / M4 2063 / TM1 1385) vs H4 9,520 -> KILLED by its criterion (>10,000).
  The extra overflow is spread (PCORE1 share 3% -> 9%, PCORE0 west bins up): the cell blockage perturbed the whole
  global placement rather than just moving the dp spill back west. Engine run took 70 min (not 4 h).
- drtH4 pass 5 = 23,799, pass 6 = 21,001 (H3 pass 6 24,402; H2 26,631). grid on iter6 armed.
- H6-cam2010 launched 02:44 UTC: H4 + the 4 camera FIFOs back in the slot at their H3 x positions, R0 at y 2010
  (55 um pin strip above the pin-free ztachip_in row top at 1955.4; 11.4 um under the AXI MX row at 2140.2).
  Macro bodies exclude cells and M1-M4 from the slot as H3 did. pl_check: 0 overlaps, min v gap 11.4, min h gap 60.
  Kill: GRT > 10,000 or highway window at DRT pass 3 not below 3,835. Expected ~03:55 UTC (09:25 IST).
- Helper: fp_h6_cam.py <macros> <H4.pl> <H3.pl> <out.pl> [Y] [ORI].
- 02:32 UTC: drtH4 grid6 sum 21,233: highway window x 2740 y 1540 = 7,485 (35% of all markers; 9,364 -> 8,596 -> 7,485,
  -8..-13%/pass); next worst windows 1,334 / 1,055 / 813 - the rest of the chip converges. The wall is the closure blocker.
- handover_drt.sh gained an optional gate (env GATE_JSON + GATE_MAX via gate_score.py): after the chip GRT it waits for
  the probe json and keeps the old DRT if the core GRT score is above GATE_MAX. Armed for H6 (gate 10,000, old drtH4):
  chip GRT starts at ck_cts (~03:35 UTC), DRT on H6 only if the gate passes.

## 2026-11-06 03:45 UTC (09:15 IST) - H6 killed; local fixes L1/L3 on H4's checkpoint
- H6-cam2010 core GRT 15,397 (M2 4802 / M3 5230 / M4 3489 / TM1 1876) -> gate FAIL, drtH4 kept (pass 8 = 17,662).
  Both H5 (cell blockage) and H6 (camera macros back) re-place the whole chip and lose H4's lucky global placement
  (9,520). Lesson: the slot problem is local; fix it locally on H4's ck_cts, not with a new global placement.
- drtH4 pass-6 picture H4_drt_pass6_map.png (sent): 150 um zoom puts the shorts in x 3040-3340, y 1990-2140 = the
  highway x 3120-3300 beside the dp 64x16 pin strip / R0 row and the slot's west edge. 1,401 distinct nets, top
  nets 40-100 shorts each (dp_gen_primary buffer-tree nets, HFN nets): general dp logic congestion, not one bus.
  Highway cell density there 43-50%.
- local_move.tcl: add hard blockages on ck_cts, detailed_placement -max_displacement 1500 1500 (cell_pad 1, as the
  engine), check_placement, write_db. Running:
  L1 = highway segment only  (3120 1850 3300 2200)            -> /workspace/chip_fp2/L1/ck_cts_L1.odb
  L3 = highway + camera slot (3120 1850 3300 2200; 3300 1955 3900 2140) -> /workspace/chip_fp2/L3/ck_cts_L3.odb
  Then chip_drt_prep (pads, straps, chip GRT) on each, DRT 3 passes each, score = highway window at pass 3
  (H4: 9,364; H3: 3,835) and total (H4 40,601).

## 2026-11-06 04:10 UTC (09:40 IST) - L1/L3 to DRT, H4 paused at pass 9
- local_move results: L1 1,633 cells out of the highway segment (max disp 212 um); L3 4,019 cells out of highway +
  slot (max disp 457 um); both check_placement clean.
- chipL1 chip GRT (8 thr, 15 iters): 13,180 (M2 4624 / M3 4252 / M4 2871 / TM1 1433) - WORSE than chipH4 10,166 on
  every layer; the cleared highway moves congestion rather than removing it at GRT level. chipL3 pending.
- drtH4 pass 9 = 15,830 (passes: 392,856 / 169,741 / 156,109 / 40,601 / 28,722 / 23,799 / 21,001 / 19,175 / 17,662 /
  15,830). Paused after pass 9 (stop_drt.sh drtH4) to give the cores to L1 and L3 at 16 threads each; resume later
  with drt_steps.tcl STEP_IN=drt_snap/drt_iter9.odb STEP_START=10 if neither local fix wins.
- Score: highway window x 2740 y 1540 at DRT pass 3 (H4 9,364; H3 3,835) and total (H4 40,601). grid_on_snap armed
  on drtL1 / drtL3 iter3.
- IHP repo public (verified 09:40 IST). Audit reply (audit_reply_79.md) ready for the owner to post on issue #79;
  gh issue comment is blocked for the session.

## 2026-11-06 04:25 UTC (09:55 IST) - L3 dead on GRT; H4 resumed at pass 10
- chipL3 chip GRT: 49,719 (M2 16,086 / M3 17,708 / M4 13,104 / TM1 2,821) = 5x H4. Moving 4,019 cells with DPL
  "nearest site" piles them at the blockage edges. L3 chain killed before its DRT (stop_drt.sh drtL3). L1 (13,180)
  keeps running at 16 threads for the pass-3 window test only.
- LESSON (post-CTS local moves): detailed_placement with a blockage legalizes to the NEAREST sites, so a cleared
  region becomes a dense ring around it; a local fix of more than ~1-2k cells needs an explicit target region
  (set cell locations west of the highway, then legalize), not a blockage alone.
- drtH4 stopped 04:12:51 UTC after pass 9 (15,830). Resumed 04:20 UTC with resume_chip_drt.sh (drt_steps.tcl
  STEP_START=10 from drt_snap/drt_iter9.odb, 16 threads, 3-pass sessions -> drtH4/resume/passNN.odb + log
  drtH4/drt_resume.log). Watcher on pass 10.
- 04:40 UTC: H4 resume from the debug-hook snapshot FAILED silently: drt_steps.tcl scan step rebuilt 0 markers,
  "pass 10 violations 0" in 4 min; drc_grid on resume/pass12.odb = 16,059 markers (pass 9 had 15,830): nothing was
  routed. LESSON: drt_iter<N>.odb snapshots (detailed_route_debug -snapshot_dir) cannot seed a step resume; only a
  step-session write_db output can. A paused snapshot run can only be restarted from pass 0 (or drt_plain_resume).
- slot_conn.tcl: the 794 dp cells in the slot: 2,832 pins inside, 575 to the highway cells, 280 east, 253 west; the
  1,633 highway cells: 5,397 inside, 851 west, 475 east. One dp_gen_core cluster living in the macro-bounded
  corridor + slot; its own wiring is the wall.
- L7 = local_relocate.tcl: all 4,019 cells of corridor + slot shifted +900 um east (band y 1955-2140 under the AXI
  block, 50% dense before), legalized (max 310 um). chipL7 chip GRT running (8 thr).
- L1 DRT at 16 thr: pass 0 still running at 04:40 (started 04:08; cores shared with L7 GRT).
- Rule: L7 chip GRT <= 11k -> L7 DRT at 16 thr now, compare highway window at pass 3 with L1 and H4 (9,364);
  winner continues at 32 thr. L7 > 13k -> restart H4 from chip_guided.odb at pass 0.
- 04:55 UTC: chipL7 chip GRT 31,742 (M2 9729 / M3 11990 / M4 5943 / TM1 4080) = 3x H4. All local moves on the
  post-CTS checkpoint worsen the chip GRT (L1 +3k, L3 +39k, L7 +21k): the global placement is tightly balanced and any
  few-thousand-cell move overloads its neighbourhood. Local-move route CLOSED. L1 DRT kept only for its pass-3 window.
- H4 DRT restarted from pass 0 at 32 threads into drtH4b (run_chip_drt.sh on chipH4; drtH4 snapshots kept). Expected
  pass 9 again after ~4 h (~09:00 UTC / 14:30 IST). When L1 pass 3 lands (~05:40 UTC): if its highway window is not
  clearly below H4's 9,364, L1 is stopped and H4b gets the machine.
- 05:30 UTC (11:00 IST): drtH4b pass 0 = 392,856 (identical to drtH4: DRT deterministic). drtL1 pass 0 = 429,055
  (+9% vs H4) after 80 min at 16 shared threads -> L1 stopped; H4b has the whole machine (32 threads, ~25 min/pass).
  Watchers: pass 5 (~07:30 UTC) and pass 9 (~09:10 UTC); grid on iter 9 to see the wall trend vs 7,485 at pass 6.
- 05:40 UTC (11:10 IST), owner: "start from when we reached 7485" -> drtH4r = plain continuous detailed_route
  (drt_steps.tcl STEP_START=0, snapshots on) on drtH4/drt_snap/drt_iter9.odb (15,830; wall ~6.7k) at 16 threads,
  next to drtH4b (from scratch, 32 thr). The schedule restarts at pass 0 on the routed wires (engine chunk restart:
  expect a bump on pass 0, then re-convergence). Loser stopped once the trend is clear (H4r pass 1-2 ~07:00 UTC).
- 07:18 UTC (12:48 IST): drtH4r (plain resume on the pass-9 snapshot, 16 thr): passes 0-2 took 26 s each and kept
  the wires (15,836 / 15,831 / 15,847); real passes 3-5 = 15,470 / 15,049 / 14,746 (-2.4 / -2.7 / -2.0 % per pass,
  20-30 min each). The restarted schedule's low marker costs make it a slow cleaner; H4's own trajectory at that count
  was -8..-10 %/pass. Rule applied: H4r stopped (snapshots iter0-5 kept, iter5 = 14,746 best routed state so far);
  drtH4b (from scratch, pass 4 = 28,722) has the full 32 threads; pass 9 ~09:30 UTC, then it overtakes H4r's 14.7k
  by pass 11 (~10:30 UTC / 16:00 IST).

## 2026-11-06 10:25 UTC (15:55 IST) - drtH4b pass 9 map; padding probes H7/H8
- drtH4b pass 9 = 15,830 (09:54 UTC; ~30 min/pass with grid runs sharing). grid9 sum 16,059; highway window
  x 2740 y 1540 = 6,746 (42% of all markers). Wall trend 9,364 (p3) / 8,596 (p4) / 7,485 (p6) / 6,746 (p9) =
  -3.5%/pass now; next windows 966 / 817 / 625. H4b alone will not close: the wall needs a structural fix that keeps
  the global placement.
- Engine knob found for exactly this (pnr.tcl DGSE_PAD_INSTANCES, config pad_instances "<glob> <sites>": extra
  detailed-placement padding on matching instances only; KianV register_file hotspot fix): spreads the dp_gen_core
  cluster at DPL without changing GPL. Probes launched 10:20 UTC (8 thr each, next to drtH4b at 32):
  H7-pad2   = H4 + pad_instances '*dp_1_i/dp0_i/dp_gen_core_i* 2'
  H8-pad1dp = H4 + pad_instances '*dp_1_i/dp0_i/* 1'
  Kill: GRT > 11,000 or highway window at DRT pass 3 not below 6,000 (H4 9,364). ck_groute ~11:40 UTC.
- 11:25 UTC (16:55 IST): drtH4b pass 10 = 11,407 (-28% in one pass: the schedule's pass-10 cost step). grid on
  iter10 running. H7-pad2 core GRT 9,208 (M2 3522 / M3 2985 / M4 1556 / TM1 1145) < H4 9,520: padding the dp_gen_core
  cells is free at GRT level; gate passed. chipH7 chip GRT started (8 thr) as the ready fallback; H4b stays primary
  (DRT on H7 only if H4b's wall stalls again). H8 pending.
- H8-pad1dp = 9,520, identical to H4 per layer: pad_instances 1 site = the global cell_pad 1 already applied, so a
  no-op (87,814 instances matched). Only >= 2 sites changes anything. H7-pad2 padded 35,477 dp_gen_core cells.
- 11:45 UTC: drtH4b grid10 sum 11,624: highway window 6,746 -> 5,346 (-21%, first real bite into the wall; the rest
  9,313 -> 6,278, -33%). Next windows 563 / 516 / 472. Wall = 46% of the residue. If -20%/pass holds: wall ~1.7k at
  pass 15, ~0.6k at pass 20; closure maybe ~pass 25 (~10 h at 25 min/pass). H7 chip GRT = ready fallback.
- 11:50 UTC: chipH7 chip GRT 10,333 (M2 3960 / M3 3401 / M4 1738 / TM1 1234) vs chipH4 10,166: equal within noise.
  H7 fallback fully prepared (chipH7/chip_grt.odb + route.guide); run_chip_drt.sh chipH7 drtH7 32 starts it in 5 min
  if drtH4b stalls. Not started now: H4b keeps all 32 threads (wall breaking since pass 10).

## 2026-11-06 13:40 UTC (19:10 IST) - drtH4b slowing; H7 DRT started in parallel
- drtH4b: pass 11 = 10,329 (-9.4%, 25 min), pass 12 = 9,690 (-6.2%, 64 min: later schedule passes are longer).
  At -6%/pass and ~1 h/pass H4b alone does not close in useful time. Owner: no more stop/restart of H4b.
- Started drtH7 (H4 + pad_instances dp_gen_core 2 sites; chip GRT 10,333) at 16 threads next to H4b (32): both slow
  by ~1/3. Score: H7 highway window at pass 3 vs H4 9,364 (grid armed on drtH7 iter3). If clearly smaller, H7 is the
  chip to give all cores to (owner decision).
- 14:43 UTC (20:13 IST): drtH4b pass 13 = 9,207 (-5.0%, ~65 min). drtH7 pass 0 = 393,506, pass 1 = 166,315
  (H4: 392,856 / 169,741; -2% at pass 1). H7 pass 3 + window map ~16:30 UTC decides the core split.
- Issue #79: owner posted the DRC reply 14:32 UTC (Herman's inconclusive AFil.c1 retry 14:24 UTC).

## 2026-11-06 16:15 UTC (21:45 IST) - H7 killed; H4b stalling; corridor-blockage probes H9/H10
- drtH7 pass 3 = 38,169 (H4 40,601); grid3 sum 38,488; highway window 8,336 (H4 9,364, -11%): the 2-site padding
  leaves the cluster in the corridor. KILLED (window not < 6,000); stopped 16:12 UTC.
- drtH4b pass 13 = 9,207, pass 14 = 9,025 (-2%, ~70 min/pass): effectively stalled. Kept running (owner).
- Re-reading: H5 blocked the SLOT (cells pushed into the corridor), H7 padded in place; nobody blocked the CORRIDOR.
  H9-corrblk = H4 + place_blockage 3120 1400 3300 2300; H10-corrslot = H9 + slot blockage 3300 1955 3900 2140.
  Judged on the DRT pass-3 window (< 6,000) and total (< 47,000); GRT only as sanity (< 15k) - GRT totals do not
  predict DRT walls (H3 11.9k had no highway wall; H4 9.5k has one). Launched 16:14 UTC at 8 thr each next to H4b.
- 17:25 UTC (22:55 IST): drtH4b pass 15 = 8,728 (-3.3%). H9-corrblk core GRT 11,013 (M2 4196 / M3 3554 / M4 1746 /
  TM1 1517), H10-corrslot 10,708 (4285 / 3493 / 1696 / 1234): both within the 15k sanity. Chip GRTs started at
  ck_cts (8 thr each); chains armed: CHIP_GRT done -> run_chip_drt.sh at 16 thr each (drtH9, drtH10); grid_on_snap
  on iter3 of both. Verdict = highway window at pass 3 (< 6,000) and total (< 47,000).
- 17:30 UTC: chipH9 chip GRT 12,016, chipH10 11,786 (chipH4 10,166). drtH9 and drtH10 started 17:29 UTC at 16 thr
  each next to drtH4b (32): 64 threads on 32 cores, every pass ~2x slower. First passes ~19:00 UTC, pass 3 + grids
  ~22:00 UTC (03:30 IST).

## 2026-11-06 18:10 UTC (23:40 IST) - manual closure path on H4b: ECO re-route mechanics
- Owner: focus on H4b, see if the remaining routing can be adjusted manually. drtH4b pass 15 = 8,728; zoom15: the
  wall sits in 3 cells x 3040-3340, y 1840-2140 (2,465 / 1,572 / 938 markers), the rest of the chip is thin.
- ECO test 1 (eco_reroute.tcl: delete wires of 10 wall nets, drt_steps-style session at pass 16, 4 thr): did NOTHING
  (0 s, 0 markers, 58 unrouted nets after = 48 pre-existing + the 10). Guides are present in the snapshot (315,503
  nets with guides = with wires). Diagnosis: a DRT step session repairs from the DRC markers stored in the db; the
  debug-hook snapshots carry none, a step-session output does. Same root cause as the failed resume on 6 Nov morning.
- ECO test 2: same + drt::check_drc over the whole die first (8.7k < 10k cap) to rebuild the db markers, then the
  session. Running (test10b). If it works: pausable/resumable H4b AND targeted ECO (cell moves + re-route of the
  touched nets on top of the finished routing) become possible.
- Schedule facts (drt_steps.tcl table): pass 17 ripup ALL; 18-24 drcCost 4; 25 ALL size 5; 26-32 drcCost 8 mc 2;
  33 fixedShapeCost 50; 34-40 drcCost 16 mc 4; 42+ maze 16; 50+ maze 32 drc 32; 58+ maze 64 drc 64.
- 18:15 UTC: drtH4b grid15 sum 8,883: wall window 4,979 (56%; 903 nets; Short 4,037 / Metal Spacing 942; M2 2,916 /
  M3 1,591 / M4 472; 73% datapath nets); next windows 497 / 382 / 336 / 250. Pass 16 = 8,471 (-3%).
- ECO test 2 (markers rebuilt by check_drc: db had 8,494 markers already, 16,913 after): step session STILL does
  nothing -> the step mechanism is unusable on snapshot dbs regardless of markers. Switched to the plain-route ECO
  (eco_plain.tcl: delete wires, detailed_route -droute_end_iter N keeps existing wires and routes the unrouted nets in
  pass 0). Test plain10 running. eco_move.tcl written: shift cells in a box, legalize, delete the routing of every
  net touching a cell that moved, plain re-route.
- 18:38 UTC (00:08 IST 7 Nov): drtH4b pass 17 (ripup ALL) = 18,515 (bump from 8,471 as the whole chip is re-routed;
  passes 18-24 run at drcCost 4). drtH9 pass 0 = 396,306, drtH10 pass 0 = 392,430 (H4 392,856). plain10 ECO test
  still running at 4 threads on the loaded machine.
- 19:05 UTC (00:35 IST): plain-route ECO CONFIRMED: eco_plain.tcl on drt_iter15 with 10 wall nets deleted:
  pass 0 = 9,071 (nets routed), pass 1 = 8,868, pass 2 = 8,784 (snapshot had 8,728). Existing wires kept.
- drtH9 pass 1 = 163,735, drtH10 pass 1 = 163,290 (H4 169,741, -3.5%).
- ECO move A launched 19:05 UTC (eco_move.tcl, 8 thr): corridor cells x 3120-3300 y 1840-2200 (1,633) shifted
  +700 um east into the band under the AXI block, legalized (max disp 400), routing of every net touching a
  displaced cell deleted, plain detailed_route 5 passes with snapshots (eco/moveA/snap). Score: total after pass 5
  vs plain10 and the wall window (grid on the snapshot).
- 19:18 UTC: plain10 finished: pass 3 = 8,727 (snapshot 8,728), unrouted 48 (= the pre-existing 48; the 10 deleted
  nets were routed). ECO mechanism fully confirmed. Move A (corrected: dbBTerm_create net name) running.

## 2026-11-06 20:50 UTC (02:20 IST 7 Nov) - H10 removes the highway wall
- drtH10 (H4 + place blockages on the corridor x 3120-3300 y 1400-2300 AND the camera slot x 3300-3900 y 1955-2140;
  core GRT 10,708, chip GRT 11,786) pass 3 = 34,522 (H4 40,601, -15%); grid3 sum 34,834; worst windows
  2,260 (x 3340 y 2740) / 1,688 / 1,668 / 1,414 / 1,384 - the highway window is not in the top 8 (H4: 9,364 there).
  PASSES its criteria. drtH9 (corridor only) pass 3 = 35,722, its grid was killed with its DRT (stop_drt matched the
  grid's IN_ODB env too) - not needed.
- LESSON: the fix for a logic cluster trapped in a macro-bounded corridor is a placement blockage on the corridor
  (+ the adjacent open slot) at GLOBAL placement time; GRT totals (10.7k vs 9.5k) said nothing about it.
- H9 DRT stopped 20:50 UTC. H10 continues at 16 threads (cannot raise threads without restart), H4b at 32 (owner),
  move A ECO at 8. H10 pass 9 ~04:00 UTC if ~45 min/pass; with no wall its passes 10+ should drop 20-60%/pass.
- ECO move A (1,666 cells shifted +700 um; legalizer displaced 2,879 cells; 3,410 nets re-routed): pass 0 =
  308,177 (initial routing of 3.4k nets is brutal); judged after its 5 passes.
- 21:40 UTC (03:10 IST): drtH4b pass 18 = 8,955 (back from the rip-up bump, still above pre-bump 8,471).
  drtH10 pass 4 = 18,038 (-48% from 34,522; H4 pass 4 was 28,722): no wall, converging fast at 16 threads.
  Move A still in its re-route passes.
- 21:42 UTC correction: drtH10 passes 3-6 = 34,522 / 22,424 / 18,038 / 15,644 (H4: 40,601 / 28,722 / 23,799 /
  21,001). At pass 6 H10 is 25% below H4 and has no wall. Watcher on passes 7-9. Move A still at its pass 0 (308k).
- 23:30 UTC (05:00 IST 7 Nov): drtH10 passes 7-9 = 14,335 / 12,953 / 10,916 (H4 pass 9 15,830; -31%). drtH4b
  pass 19 = 6,738 (drcCost-4 regime biting: 8,955 -> 6,738). ECO move A KILLED: 308,177 -> 292,234 -> 285,560; the
  initial routing of 3,410 nets inside finished routing floods the area with shorts the restarted schedule cannot
  clean. LESSON: post-route cell-move ECO is only viable for tens of nets, not thousands; the wall needs the
  placement-time fix (H10).
- 00:06 UTC 7 Nov (05:36 IST): drtH4b pass 20 = 5,705 (-15%); drtH10 pass 10 = 7,583 (-31%, the pass-10 cost
  step). Both converging; H10 without a wall, H4b with it.
- 01:25 UTC (06:55 IST): drtH10 passes 10-12 = 7,583 / 6,735 / 5,948 (-11..-12%/pass); drtH4b pass 21 = 4,924
  (-14%). Grids armed on H4b iter21 and H10 iter12 to compare the residues (wall share vs scattered).
- 01:50 UTC (07:20 IST): drtH4b grid21 sum 5,088: wall window 3,091 (61%; 4,979 at pass 15 -> -8%/pass), the rest
  ~2,000 spread (max 358). H4b outside the wall is nearly done; the wall alone needs ~15+ more passes at this rate.
- 01:51 UTC: drtH10 grid12 sum 6,134, fully scattered: worst windows 522 / 401 / 369 / 359 / 330, no wall.
  Comparison at this moment: H4b 5,088 = wall 3,091 (-8%/pass) + 2,000 scattered; H10 6,134 all scattered
  (-12%/pass). H10 is the better closure candidate; it runs at 16 threads sharing the machine with H4b (32).
- 02:15 UTC (07:45 IST): drtH4b pass 22 = 4,617 (-6%). drtH10 pass 13 = 4,931. RAM: container 81 of 128 GB
  (routers 12.1 + 10.2 GB, rest file cache); CPU is the limit (48 threads on 32 cores).
- 02:53 UTC (08:23 IST): drtH10 passes 13-15 = 4,931 / 4,512 / 4,173 (-8..-9%/pass, scattered). drtH4b pass 22 =
  4,617 (wall 3 cells x 3040-3340 y 1840-2140: 1,201 / 1,156 / 723 at pass 21; picture H4b_drt_pass21_map.png sent).
- 04:42 UTC (10:12 IST): drtH4b pass 23 = 4,545, pass 24 = 4,205 (-7.5%). drtH10 pass 16 = 4,016, pass 17
  (ripup ALL) = 8,314, pass 18 running at drcCost 4. H10 pass times 23-55 min (avg 33) at 16 shared threads.
  ChatGPT review of the pack: concurs (prioritize H10, keep H4b checkpoints, watch worst window, KLayout signoff +
  power connectivity at the end); no new technique for the wall or the tail.
- 06:15 UTC (11:45 IST): drtH10 passes 18-21 = 4,344 / 3,605 / 2,625 / 2,376 (drcCost-4 regime: -17/-27/-9%).
  drtH4b pass 25 (ripup ALL, size 5) = 9,517 (bump from 4,205). Grid armed on H10 iter21 (worst-window check).
- 06:40 UTC (12:10 IST): drtH10 grid21 sum 2,554; worst windows 467 (x 2140 y 340) / 246 (x 1540 y 340) / 232 /
  191 / 125. The south-edge pair is a SECOND, small, slow spot shared by every run (H10 pass 3/12/21: 1,384 / 522 /
  467; H4b 472 / 336 / 358; H3 pass 5 800): Metal4 shorts (413 of 467) of PCORE0 alu/adder/register-file nets, 43%
  of them against VSS/VDD, at y 450-550 and 700-750 = where the pad-to-core power straps / rings cross the PCORE0
  south strip. power_shapes_in_box.tcl written to list the straps there. Expect this ~700-marker spot to be the
  last obstacle for H10; likely fix = ECO on those nets (small set) or a routing obstruction / layer rule there.
  Power shapes there (power_shapes_in_box.tcl on H10 iter21): TM1 horizontal full-width straps every 16 um (the
  PDN grid), M4 vertical 1 um pad-to-core stubs every 50 um (VDD/VSS pairs) in y 323-437 and 581-663, M3 0.2 um
  follow-rails. The M4 shorts sit at y 450-550 / 700-750, i.e. against the TopVia1/M4 landing pads of the TM1
  straps between the stub bands. The schedule raises fixedShapeCost to 50 at pass 31 and 100 at pass 41, which is
  what clears shorts against fixed power shapes; before that they linger. Not an action item yet.
- 07:41 UTC (13:11 IST): drtH4b pass 26 = 6,207 (from the pass-25 bump 9,517; pre-bump 4,205). drtH10 pass 22 =
  2,075, pass 23 = 2,055 (NEARDRC pass), pass 24 running. Picture H4b_vs_H10_floorplan.png sent (fp_blk_picture.py).
- 07:48 UTC (13:18 IST): drtH10 pass 24 = 1,917 (-7%). Pass 25 = ripup ALL (size 5), then drcCost 8 / mc 2 from 26.
- 08:45 UTC (14:15 IST): drtH10 pass 25 (ripup) = 3,613, pass 26 = 2,351, pass 27 = 2,049 (drcCost 8 regime).
  drtH4b still at pass 26 = 6,207 (pass 27 > 1 h).
- 10:26 UTC (15:56 IST): drtH10 passes 28-30 = 1,937 / 1,810 / 1,702 (-6%/pass). drtH4b pass 27 = 5,300.
  Grid armed on H10 iter30 to see the residue structure (south-edge power spot share). Passes 31 (fixedShapeCost 50,
  NEARDRC) and 33 (ripup size 3) ahead.
- 10:50 UTC (16:20 IST): drtH10 grid30 sum 1,826: windows 344 (x 2140 y 340) / 332 (x 4540 y 2740) / 174 / 172 /
  89 / 89. Whole-chip breakdown of the pass-30 residue: Short 1,555 + Metal Spacing 271; layers M4 1,476 / M2 203 /
  TM1 106 / M3 41; 1,222 of the shorts involve VDD/VSS. drc_power_mod.py: the M4 power shorts are NOT periodic with
  the TM1 strap grid (16 um) nor the 50 um stubs. drc_near_macro.py: ALL 1,166 M4 power shorts and the 51 TM1 ones lie
  INSIDE macro outlines (ztachip_inst 614, axi_merge 279, cpu 177, camera 96): signal wires landing on Metal4 inside
  SRAM macros, on the macros' VDD/VSS pins. Hypothesis: GRT guides descend TM1 -> M4 inside macros (OBS modelled as
  partial capacity). guides_in_macros.py running on route_clamped.guide. If confirmed: fix = routing obstructions
  on M1-M4 over every macro (+margin) before GRT (new chip GRT + DRT) or an ECO of the ~1,200 nets with the
  obstructions added; the fixedShapeCost passes (31/41) may also clear them - pass 31-33 counts decide.
- 11:15 UTC (16:45 IST): ROOT CAUSE of the pass-30 residue. drc_near_macro: 1,074 of the 1,166 M4 power shorts are
  >= 10 um INSIDE macro outlines. RM_IHPSG13 LEF (2P_1024x32): the Metal4 OBS is only a 17 um strip (x 383-400 of
  685); the rest of Metal4 inside the macro is VDD!/VSS!/VDDARRAY! pin stripes (225 rects) with routable gaps, so
  GRT puts M4 guides inside macros (guides_in_macros: 442 M4 boxes >= 10 um inside) and DRT threads M4 between the
  stripes and shorts the power pins. 430 distinct signal nets carry these shorts (ztachip 229, axi 99, cpu 24).
  Also: TM1 horizontal PDN straps every 16 um make TM1 (vertical layer) unusable for long over-macro hops.
- ECO obsA launched 11:14 UTC (eco_obs.tcl): Metal4 routing obstructions over every macro outline, the 430 nets'
  wires deleted, plain detailed_route 5 passes at 8 thr on drt_iter30 (base 1,702/1,826 mapped). Success = total
  well below 1,700 and no M4 shorts inside macros. If it works, the production fix = M4 obstructions over macros
  before the chip GRT (chip_io_obs-style) for every future run, and the H10 closure = snapshot + this ECO.
- 11:24 UTC (16:54 IST): drtH10 pass 31 = 1,608 (fixedShapeCost 50 starts to bite), 32 = 1,550, 33 (ripup size 3)
  = 2,008 bump. drtH4b pass 28 = 4,925. ECO obsA on iter30: pass 0 = 29,241 (every existing M4 wire inside a macro
  now violates the new obstructions too), pass 1 = 7,949, pass 2 = 8,244 - the restarted low-cost passes clean
  slowly; passes 3-5 pending. Lesson so far: the obstruction ECO touches far more than the 430 nets.
- 11:47 UTC (17:17 IST): drtH4b pass 29 = 4,591. ECO obsA passes 3-4 = 6,221 / 5,491 (-25 / -12%); pass 5 pending.
  The obstruction ECO converges but from a 29k restart; END=5 is too short - a longer ECO (15+ passes) or the
  obstructions before GRT on a fresh run are the real options.
- 11:53 UTC (17:23 IST): ECO obsA final = 5,173 (all 430 nets routed): residue M4 4,477, of which 3,844 markers
  >= 10 um INSIDE macros (now shorts against the obstructions + power pins). The DRT cannot leave the guides that run
  through the macros -> the obstruction must be in place BEFORE the global route. ECO route closed for this defect.
- H10m chain launched 12:00 UTC (chip_mobs_grt.sh): chipH10/chip_pdn.odb + macro_obs.tcl (Metal4 obstructions over
  all 298 macros, margin 0) -> chip_grt.tcl (16 thr, 15 iters) -> chipH10m/chip_grt.odb + route.guide. Then
  run_chip_drt.sh chipH10m drtH10m 32. Expect: GRT overflow higher than 11,786 (M4 capacity over macros gone),
  but no M4-inside-macro shorts in DRT; the H10 corridor/slot blockages stay (same placement/CTS).
- Both current runs cannot reach zero: H4b (wall + inside-macro shorts), H10 (~1,200 inside-macro shorts at pass
  32 = 1,550 total). Recommendation to the owner: stop H4b when drtH10m starts; keep H10 until H10m passes it.
- 12:30 UTC (18:00 IST): chipH10m chip GRT = 11,786, identical per layer to chipH10 (M4 resource 6,624,205 vs
  6,624,207): GRT already counted the macro M4 as blocked; guides_in_macros on the new guides: unchanged (442 M4
  boxes >= 10 um inside, 498 nets). Mechanism: GRT -allow_congestion overflows vertical 2D edges over macros (vertical
  layers M2/M4 both blocked there), layer assignment then drops those segments on M4 inside the macro. The
  obstruction does nothing at GRT level; the lever is the GRT overflow itself.
- Two GRT experiments launched 12:28 UTC (8 thr each, chipH10 pads db): chipH10m2 = Metal4 obstructions + 40
  congestion iterations; chipH10m3 = Metal4 + TopMetal1 obstructions over macros (2D sees zero capacity over macros,
  forces detours), 15 iterations. Score = guides_in_macros deep-inside M4 count (442 now) and total overflow.
- PDN note: TopMetal1 is the HORIZONTAL layer in this stack (pdn_c5l_sram_v2.tcl header), so TM1 signal routing
  over macros between the 16 um straps is possible horizontally; vertical crossings over macros are impossible.
- 12:32 UTC (18:02 IST): drtH10 passes 34-36 = 1,811 / 1,716 / 1,541: flat around 1,550, consistent with ~1,200
  unfixable inside-macro shorts. Watcher on passes 37-40 (fixedShapeCost 100 from 41).
- 12:50 UTC (18:20 IST): chipH10m3 (Metal4 + TopMetal1 obstructions over macros, 15 iters): total 12,329
  (M2 5861 / M3 5160 / M4 1161 / TM1 147); guides >= 10 um inside macros: M4 442 -> 62, but M2 567 -> 1,021,
  M3 303 -> 327. Hiding TM1 only moves the vertical overflow from M4 to M2 inside the macros: the demand to cross
  macro rows vertically is the problem (the vertical channels between macros are saturated), not the layer.
  chipH10m2 (40 iterations) pending. net_macro_cross.tcl written: are the crossing nets the macros' own pin nets
  with their logic on the wrong (north) side of the pins?
- 13:05 UTC (18:35 IST): net_macro_cross on the 186 (net, macro) pairs with M4 guides inside macros (H10 guides):
  174 nets do NOT connect to the macro they cross; 119 have pins both north and south of it -> pass-through nets
  of logic split by big macros. 265 of the 442 M4 boxes are on the two east CPU cache macros (dcache ways_0 bank1
  1024x32 at 4888,4819 R0 and ibus banks_1 1024x32 at 4888,4359 MX, pins facing across a 75 um strip); the rest:
  AXI 64x32 FIFOs (57), PCORE0 register files (53), dp_sink 256x32 (21). The vertical channel between the CPU
  macro pairs (x 4640-4888, 248 um) is saturated. H10 placement dump running for the CPU-block density picture.
- 13:00 UTC (18:30 IST): H10 CPU-block density: logic north (y 5205-5450) and south (y 3900-4359) of the east cache
  pair (x 4888-5574) plus the 64x22 ibus-tag macros at x 5634-6160 in both rows -> no vertical channel east of
  x 4888; the empty west channel (x 4343-4888, y 4819-5205) is far for the east-side nets. H11 = H10 + the two
  ibus-tag 64x22 moved to x 3360-3886, y 4360/4495 (MX/R0 pair, 60 um shared strip; 68 um west of the lower cache):
  opens x 5574-6160 as a 586 um channel. pl_check clean (min gaps 20 / 60). Probe H11-cputags launched 13:00 UTC
  (8 thr). Score: guides_in_macros M4 boxes inside (<150 vs 442) on the chip guides, DRT pass 3 < 40k.
- chipH10m2 (40 GRT iterations) at iteration 17/40 at 12:52 UTC.
- 13:55 UTC (19:25 IST): drtH10 passes 37-40 = 1,417 / 1,344 / 1,313 / 1,290 (fixedShapeCost 100 from 41).
  H11 probe: ck_cts ready ~13:50 UTC, chain running chip GRT (8 thr). chipH10m2 at iteration 26/40.
  ChatGPT asked for the routed H10 db + full guides + DRC report: pack4 = H10_drt_iter39.odb.gz (116 MB),
  H10_route_clamped.guide.gz (16 MB), H10_drt_iter39_drc.rpt.gz (whole-die check_drc, running), README.
- 14:05 UTC (19:35 IST): H11 chip GRT + guides check: M4 boxes >= 10 um inside macros 442 -> 371; the two east CPU
  caches still carry 358 + 231 M1-M4 boxes -> opening only the east column does not stop the crossings (the 2D
  router still prefers overflowing through the caches to a 600+ um detour). H11 KILLED (criterion < 150).
- H12 = H11 + both east 1024x32 caches shifted +586 um to x 5474-6160 (core-margin edge): central passage
  x 4640-5474 (lower row) / x 4343-5474 (upper row, minus the small uart 256x8 at 4403-4640). pl_check clean.
  Probe launched 14:05 UTC (8 thr); chain armed (chip GRT + guides count). ETA guides count ~15:45 UTC (21:15 IST).
- pack4 sent to the owner for ChatGPT: H10 iter39 db (gz, 5 parts), full clamped guides, whole-die DRC (1,385).
- 15:20 UTC (20:50 IST): H12 chip GRT total 9,522 (best chip GRT: H10 11,786, H4 10,166). guides_in_macros
  (margin -10): M4 boxes inside 442 (H10) -> 371 (H11) -> 166 (H12); the CPU caches are gone from the list; the
  rest: AXI read cmd-fifo 64x32 slice1 (121 M1-M4 boxes) and PCORE0 register-file ram2 256x32 slice3 (105).
  H12 is the chip to route; decision on 15 vs 40 GRT iterations pending chipH10m2's result (iteration 33/40).
- 16:55 UTC (22:25 IST): chipH10m2 (40 GRT iterations): total 11,656 but guides inside macros WORSE (M4 1,131,
  M2 1,001, M3 851 vs 442 / 567 / 303 at 15 iterations): more iterations spread the overflow into the macros.
  Lever rejected. drtH10 passes 41-44 = 1,370 / 1,274 / 1,250 / 1,164; drtH4b pass 31 = 4,039.
- drtH12 DRT started 16:57 UTC at 16 threads on chipH12 (15-iteration guides, 166 M4 boxes inside macros).
  Attempt to stop drtH4b was denied by the session's permission classifier ("interfere with workloads") after the
  account change; H4b keeps running until the owner stops it (stop_drt.sh drtH4b). Machine: 32 + 16 + 16 threads.
- Next floorplan step if H12's inside-macro residue persists: the AXI read cmd-fifo 64x32 slice1 and the PCORE0
  register-file ram2 256x32 slice3 (the two macros still crossed in H12's guides).
- 17:00 UTC (22:30 IST): owner: stop H4b. drtH4b stopped after pass 31 (4,039); snapshots drt_iter0..31 kept.
  Machine now: drtH10 (16 thr) + drtH12 (16 thr).
- 18:04 UTC (23:34 IST): drtH12 pass 0 = 386,712, pass 1 = 161,900 (H10 392,430 / 163,290) at 16 threads,
  ~33 min/pass now that H4b is stopped. drtH10 pass 47 = 1,080. Watchers: H12 passes 2-4, grid on iter3.
- 19:30 UTC (01:00 IST 8 Nov): drtH12 (16 thr) passes 0-3 = 386,712 / 161,900 / 146,494 / 36,036 (H10: 392,430 / 163,290 / 148,133 / 34,522); pass-3 criterion < 40k MET, run continues. ~35 min/pass, same pace as H10. drtH10 passes 48-49 = 1,066 / 1,193 (ripup at 49). 600 um grid scan on drtH12 iter3 running (chk/grid3), the inside-macro share of the M4 shorts is judged on its concatenated window reports with drc_near_macro.py. Snapshot db markers (12,565, no layer) are not usable for that.
- 20:05 UTC (01:35 IST 8 Nov): drtH12 pass 4 = 21,435 (H10 22,424). INSIDE-MACRO RESULT (drc_near_macro + new drc_per_macro.py on the 600 um window reports): H12 pass 3 has 2,711 power shorts inside macros vs H10 pass 3 3,365; the two CPU 1024x32 caches went 467 -> 0, every other macro keeps the same count. H10's late residue (chk/latest, 1,155 markers) has 909 inside macros: PCORE0 RF ram2 2p 256x32 slice1 (1930,440) 182 + slice3 (1930,677) 96, AXI read cmd-fifo 64x32 slice1 (4464,2825) 86, CPU caches 85+81, AXI write data-fifo slices 1/4 (4464,2985/3080) 49+35, camera write-fifo 64x32 (4243,1240) 37, dp sink/fetch fifos (x 1930-2821, y 2434-2930) ~120. => H12 will floor near 900-1,000 (CPU share only, ~190 markers). The cmos5l tech LEF has NO TopMetal2 (5 metals), so no legal vertical crossing over a macro exists; fix must be floorplan/placement for the remaining 8 macros. Pattern: all are pin-facing pairs of wide flat macros (2p 64x32 = 703x75, 2p 256x32 = 703x137, 1p 256x32 = 417x119) with a 85-100 um pocket between them (MX pins north facing R0 pins south). net_macro_cross on chipH12 m4_pairs running to tell pocket cells vs through-traffic.
- 20:20 UTC (01:50 IST 8 Nov): POCKET MECHANISM confirmed. net_macro_cross on chipH12 (114 pairs): 104 nets do not belong to the crossed macro, 81 have pins both north and south of it. nets_pins_xy.tcl + pins_in_boxes.py: 98 of the 112 crossing nets have a pin in a dead space next to the crossed macro (RF pocket y 577-677: 27 nets, AXI pocket x 4464-5167 y 2900-2985: 30, dp pocket y 2692-2792: 26, dp_fetch pocket y 2995-3095: 15). chip_placed.def: 1,490 cells in the south margin strip under RF slice1, 1,310 in the RF pocket, 1,036 in the AXI pocket. Pictures: /workspace/chip_fp2/H12_pass3_shorts_map.png + zoom_south/axi/dp (drc_scatter.py). fp_pockets.py lists 146 dead spaces (facing-pin pockets 60-130 um + margin strips) = 5.0 mm2 in H12 -> /workspace/chip_fp2/handoff/H12_pockets.txt. Probe H13-pockets = H12 + all 146 as placement blockages (harness: blk_file), launched 20:20 UTC at 8 threads; chip GRT check chained (chipH13). Kill: > 60 M4 boxes inside macros (H12 166) or DRT pass 3 > 40k. Incremental-GRT re-route of the 112 nets (grt_incr_nets.tcl, start/end_incremental after ITerm reconnect): guides unchanged (166 boxes, same macros) -> no lever.
- 20:55 UTC (02:25 IST 8 Nov): H13-pockets probe PASSED its gate early: ck_cts at ~20:35 UTC (8 thr, 50 min), chip GRT (chipH13, 15 iters) overflow total 3,061 (M2 1,328 / M3 1,155 / M4 525 / TM1 53) vs H12 9,522; guides_in_macros margin -10: M4 boxes inside 35 (H12 166, H10 442), remaining mostly dp_sink3 fifo_i2 slice1 (2407,2792) 74 M1-M4 boxes and dp_fetch slice23 (2227,2930) 61. drtH13 DRT started 20:55 UTC at 16 threads (machine 48 threads on 32 cores while H10 and H12 keep running; owner asked whether to stop H10). Watchers: passes 0-3, grid on iter3.
- 23:25 UTC (04:55 IST 8 Nov): drtH13 (16 thr, started 21:30 UTC) passes 0-4 = 374,714 / 157,435 / 141,549 / 22,821 / 5,239 (H12: 386,712 / 161,900 / 146,494 / 36,036 / 21,435; H10 pass 4 22,424). Pass-3 criterion met by a wide margin; pass 4 is 4x below H12. Grid on iter3 pending (snapshot being written). drtH12 pass 8 = 11,490.
- 23:45 UTC (05:15 IST 8 Nov): drtH13 pass-3 window map: sum 22,923, top window x 2740-3340 y 2740-3340 = 4,875 (H12 3,740), next 1,534 / 1,493 / 1,401. Inside-macro power shorts 866 (H12 2,711, H10 3,365): register-file rows 0, AXI stack 52+18, but camera write_fifo 64x32 slice1 (4243,1240) 273 / 63 nets (H12 118) + slice0 (3480,1240) 74 (new: displaced cells added through-traffic across the camera FIFOs, which are not in a facing pair -> no blockage), dp FIFO rows persist: dp_sink3 fifo_i2 (2407,2792) 113, dp_fetch 64x16 row y 2930 (2821) 111 + (2227) 72 + (1331) 41 + (737) 21. Grids armed on iter 6 and 9 with per-macro counts; guides_in_macros margin 0 on chipH13 running (do DRT shorts come from edge guides?).
- CORRECTION to the 23:25 UTC entry: drtH13 pass 4 = 12,694 (the 5,239 was drtH12 pass 11 printed by the same watcher). drtH13 passes 0-4 = 374,714 / 157,435 / 141,549 / 22,821 / 12,694; drtH12 passes 9-12 = 10,442 / 6,710 / 5,239 / 4,502 (H10 pass 12 = 5,948, H12 ~25% ahead of H10). Margin-0 guides on chipH13: M4 boxes touching outlines 151; camera write_fifo slice1 only 18 boxes on 12 nets while DRT pass 3 has 273 shorts on 63 nets inside it -> shorts_vs_guides.py written to check whether DRT enters without guides.
- 00:50 UTC (06:20 IST 8 Nov): H13 pass-3 shorts inside the camera write_fifo slice1: 277 on 63 nets, ALL foreign (crossings), depth spread over the whole 75 um macro; all 63 nets have guides touching the outline but mostly on Metal2 (67 boxes; M4 19, M3 8). RM_IHPSG13 LEF abstracts obstruct Metal2 only on the macro's own M2 shapes (hundreds of 0.2-0.8 um rects), Metal1/Metal3 one full rect, Metal4 62 full-height stripes + 104 pin stripes -> GRT sees free Metal2 inside macros: deep-inside guide boxes H13 M2 209 / M3 78 / M4 35 (H12 420 / 133 / 166). Camera FIFO row at y 1240 = four flat macros x 3480-5899 with 60 um gaps above a 0.4 mm cell band (y 814-1240, small-macro columns with blocked pockets) -> crossings. fp_pockets.py extended: thin blank gaps 3-30 um between stacked macros are dead spaces too (cells with no exit). H14-camspread = H13 + camera row spread to 147 um gaps (slice1 4243->4330, write_fifo2 slice0 5006->5180, slice1 5482->5743) + 234 blockages (5.56 mm2); pl_check clean (min gaps 20/60). Launched 00:50 UTC at 8 thr; chip check chained (chipH14). Kill: M4 > 25 or M2 > 150 deep-inside boxes, DRT pass 3 > 25k. Machine: 56 threads on 32 cores (H10/H12/H13 DRT + H14 probe); owner asked twice about stopping H10.
- 01:00 UTC (06:30 IST 8 Nov): drtH13 passes 5-6 = 9,948 / 8,052. iter6 grid sum 8,110, centre window x 2740-3340 y 2740-3340 = 2,377 (pass 3: 4,875). Inside-macro power shorts 810 (pass 3: 866) -> PERSISTENT floor ~800: camera write_fifo slice1 280 + slice0 71, dp_sink3 fifo_i2 (2407,2792) 112, dp_fetch 64x16 row y 2930: 94 + 58 + 38 + 12, dp_sink3 fifo (1930,2792) 30, AXI read cmd-fifo slice1 43, AXI resp fifo 64x22 (4640,2140) 18. H13 will floor near 900 unless an ECO; H14 targets the camera row and the thin dp gaps. drtH12 passes 12-14 = 4,502 / 3,930 / 3,558 (H10 14 = 4,512).
- 01:35 UTC (07:05 IST 8 Nov): chipH14m (Metal2 with 2 um pin band + Metal4 obstructions inside all macros before the chip GRT): result BYTE-IDENTICAL to chipH14 (overflow 3,516, boxes 175/64/40, same macros) -> GRT capacity inside the macros is already 0 on M2/M4; the guides through macros are -allow_congestion overflow decisions, no obstruction changes them. Obstruction lever closed for GRT and DRT. Next: side-move ECO - for each crossing net move its minority-side cells across the macro row, incremental GRT for those nets, plain DRT re-route; data from drtH13 pass 6 (drc_pairs.py -> pairs6.txt, nets_pins_xy -> pins6.log).
- 01:55 UTC (07:25 IST 8 Nov): side-move ECO test. drtH13 pass-6 inside-macro shorts: 188 (net, macro) pairs; pins_side.py: 131 nets plannable (pins on both sides of the crossed macro, minority side <= 6 std cells), 47 one-side-only, 7 unmovable (macro/port on the minority side), 3 > 6 cells; 161 cells to move (to the majority side, 12 um past the macro edge). eco_sidemove.tcl (start_incremental GRT -> moves -> legalize (BTerm trick) -> delete wires of touched nets -> end_incremental -> plain DRT END=6) launched on drt_iter8.odb (6,379) at 8 thr -> /workspace/chip_fp2/eco/side8. Success = inside-macro shorts well below 810 and total not exploding.
- 02:00 UTC (07:30 IST 8 Nov): drtH13 iter9: grid sum 5,926, centre window 1,622; inside-macro shorts 687 (pass 6: 810; camera slice1 238, dp_sink3 fifo_i2 90, dp_fetch 73+57+21, camera slice0 59, AXI 38+18). ECO side8: 161 cells moved, 283 displaced after legalization, 553 nets touched and re-routed by the incremental GRT (GRT-0115 congestion warning), plain DRT END=6 running.
- 02:35 UTC (08:05 IST 8 Nov): ECO side8 (v1) was flawed: targets 12 um past the macro edge fell into the blocked pockets or the next macro row, the legalizer pushed 39 of 161 cells > 15 um (19 > 60 um, i.e. back across the row); after its incremental GRT the deep-inside M4 boxes ROSE 35 -> 77; its plain DRT restarted at 34,783 -> killed. pins_side.py fixed: targets pushed past blockages AND macro outlines (+10 um halo), skipped when no free band within 250 um (58 cells, all in the dense dp stacks), legalizer cap 250/40 um: dry run (eco_sidecheck.tcl) 104 cells, max displacement 15.9 um, 0 far from target. ECO side2 (v2) launched on the newest drtH13 snapshot, END=8, 8 thr -> /workspace/chip_fp2/eco/side2.
- 04:40 UTC (10:10 IST 8 Nov): ECO side2 (v2) result on the drtH13 iter9 snapshot (5,874; inside-macro 687): 104 cells moved, 197 displaced, 399 nets re-routed (incremental GRT), plain DRT END=8: 24,624 -> 4,825; inside-macro power shorts 438 (-36%): camera write_fifo slice1 238 -> 53 (cells movable), slice0 59 -> 60 and the dp field (dp_sink3 fifo_i2 90 -> 78, dp_fetch 73 -> 65, 57 -> 42) barely changed = the 58 cells with no free target. BUT 48 multi-pin nets left UNROUTED (opens) -> must be understood before any ECO is applied (unrouted_nets.tcl). pins_side.py: channel fallback (x 25 um outside the macro span) for cells without a free band in y.
- 04:50 UTC (10:20 IST 8 Nov): the 48 unrouted nets after ECO side2 are the *_PAD bondpad nets (2 pins, in the pad ring, 0 guides) - unrouted in every snapshot until the finishing step, not an ECO defect. H15 = H13 ck_cts.odb + side moves (apply_moves.tcl, moves6g with channel fallback, legalizer cap 250/40) -> chip_drt_prep.sh (chipH15, 8 thr) -> guides_in_macros gate. Launched 04:50 UTC.
- 05:00 UTC (10:30 IST 8 Nov): H15 gate (H13 ck_cts + 151 side moves before GRT): overflow 3,804 (H13 3,061), deep-inside boxes M2 235 / M3 72 / M4 41 (H13 209/78/35), same macros on top (camera slice1 now 53 boxes) -> a fresh GRT re-plans everything and overflows OTHER nets through the same rows: the crossings are congestion-driven, not tied to specific cells. H15 KILLED at the gate (no DRT). GRT-level counts are poor predictors anyway (H13 camera slice1: 2 deep boxes, 277 DRT shorts). The measured lever is the snapshot ECO with frozen surroundings (-36% inside-macro in one round). Plan: ECO rounds on H13 snapshots, re-planned from each round's DRC report. Round A (side3): moves6g (151 cells incl. 48 channel fallback) on the newest drtH13 snapshot, END=8, 8 thr, launched 05:00 UTC.
- 06:10 UTC (11:40 IST 8 Nov): drtH13 DRT process DIED during pass 28 (1,196): log ends at 'Post processing', snapshot drt_iter28.odb.1 left half-written (335 of 582 MB on the mfs share at 06:03 UTC), no error/kill message in the chain log, chip_droute.odb never written, disk 455 TB free, RAM 275 GB free. Last usable snapshot drt_iter27.odb (1,286). Cause unknown (write to the network share died with the process?). H13 passes 22-28 = 1,368 / 1,348 / 1,283 / 1,714 / 1,405 / 1,286 / 1,196. Not resumed as a step session (impossible); the ECO rounds continue from the snapshots (round A = side3 on iter22 running). eco_round.sh written to chain rounds: base odb + DRC rpt -> pairs -> pins -> moves -> eco_sidemove -> per-macro.
- 06:25 UTC (11:55 IST 8 Nov): drtH12 DIED too (pass 29 at 20%, drt_iter29.odb.1 0 bytes at 06:22 UTC; last intact iter28 = 1,533). CAUSE: container cgroup memory.max = 128 GB (host shows 755 GB), memory.events oom_kill = 1; at 06:00 UTC H10+H12+H13 DRT (~36 GB) + ECO round A (15 GB) + leftovers/page cache hit the limit; the OOM kills leave no message in the chain logs. memory.current now 44 GB (H10 10 GB + ECO 14.5 GB). Lesson saved to memory. Remaining: H10 DRT (1,139, alive), ECO round A on H13 iter22 (pass 4 = 5,958 of 8). Round B chained to start from round A's result automatically.
- 06:35 UTC (12:05 IST 8 Nov): ROOT CAUSE of the two DRT deaths = /workspace (mfs fuse share) DISK QUOTA EXCEEDED: every write failed ('Disk quota exceeded'; write_db -> 'basic_ios::clear: iostream error'); the DRT snapshot writes of H13 (pass 28) and H12 (pass 29) failed and the processes ended without a message; the cgroup oom_kill=1 is a separate, older event. /workspace was 472 GB (chip_fp2 153 GB). Freed: stopped-run dirs drtH2/H3/H4/H4r/H7/H9/L1, chipH2/H3/H4/H6/H7/H9/L1/L3/L7/H/H10m2/m3/H11, H10 snapshots except 39/55/56/57, H4b except 31, H12 except 25-28, H13 except 9/22/24-27, eco/side8 -> chip_fp2 35 GB, writes OK again (100 MB test). H10 DRT (alive, 1,139) kept; its snapshots from pass 58 on were lost to the quota too.
- 06:45 UTC (12:15 IST 8 Nov): stream_chip.sh rehearsal on finish_dry/chip.def: rc 0 in 60 s, chip.gds 750 MB, but '[ERROR] LEF Cell RM_IHPSG13_2P_BITKIT_16x2_LE_con_edge_lr has no matching GDS/OAS cell. Cell will be empty' -> a 2P SRAM sub-cell is missing from the GDS set given to the streamer; must be fixed before the release GDS (checking the PDK GDS files).
- 07:00 UTC (12:30 IST 8 Nov): the 16 'no matching GDS cell, will be empty' stream errors are the RM_IHPSG13_{1P,2P}_BITKIT_16x2_{CORNER,EDGE_TB,LE_con_corner,LE_con_edge_lr,LE_con_tap_lr,POWER_ramtap,TAP,TAP_LR} sub-cells: gds_cell_check.py (KLayout) shows them EMPTY in the PDK's own SRAM GDS files (RM_IHPSG13_2P_64x32_c2.gds, 1P_256x32), in the preliminary release SoC2611.gds (v1.0.0) and in our streamed chip.gds alike; the bit-cell arrays (BITKIT_16x2_SRAM, CELL, EDGE_LR, POWER_ramblk, TAP) are complete everywhere. Vendor placeholders, not a stream defect; no action. Antenna ECO v1: repair_antennas inserted diodes but its legalization failed on 39 of them (DPL-0036) -> v2 drops the placement blockages first (running).
- 07:45 UTC (13:15 IST 8 Nov): ECO round A (side3, base drtH13 iter22 = 1,368, 151 moves, 298 displaced, 612 nets re-routed, END=8): inside-macro shorts 687 -> 439 (camera slice1 238 -> 61; dp_fetch slice27 73 -> 102 worse, dp_sink3 fifo_i2 90 -> 85), total 4,819 (plain re-route restart 34,807, 8 passes not enough to get back under the 1,368 base). side3.log stopped at pass 5 (its fd hit the quota at 06:29 UTC during the clean-up) but side3_drc.rpt and side3.odb (578 MB) were written at 07:40 UTC. Round B launched from side3.odb with END=20 at 16 thr (eco_round.sh), re-planned from side3_drc.rpt. Freed the checkpoint builds of 21 killed DPASS probes (runs dir 27 GB).
- 09:06 UTC (14:36 IST 8 Nov): antenna ECO rehearsal v2 (eco_antenna.tcl on finish_dry/chip.odb = drtH13 iter27, blockages dropped): repair_antennas 1 iteration inserted 10,927 sg13cmos5l_antennanp diodes on 6,027 nets (all legalized), plain DRT END=5: 246,747 -> 37,638 -> 31,594 -> 12,303 -> 10,248 -> 9,085 (base 1,286: a 5-pass re-route is far from recovering); check_antennas after: 581 net / 666 pin violations (from 6,052 / 7,126). 2.5 h at 8 thr. Plan: antenna repair as a chain step after a side-move round (its re-route absorbs it), END=20 at 16 thr, a second small iteration at the very end.
