# DGSEV2 platform entry for IHP SG13CMOS5L (prepared 2026-10-30)

Everything the DGSE engine (`aravindgp/DGSE`, branch `DGSEV2`) needs to place and route
`dgrid_soc1_chip_top` on **SG13CMOS5L** -- the CMOS-only SG13G2 variant with a
Metal1-Metal4 + TopMetal1 backend (5 routing layers, no Metal5 / TopMetal2) -- staged here
to be copied into the engine. Nothing in this directory has been run through OpenROAD
(no OpenROAD on the prep machine); every file says where its numbers come from.

| file | goes to (engine) | what |
|---|---|---|
| `pdks.json.fragment` | merge into `engine/flow/pdks.json` | the `ihp-sg13cmos5l` PDK entry (every key the engine reads, with notes) |
| `pdk_registry.json.fragment` | merge into `engine/flow/pdk_registry.json` | registry row (license / foundry / signoff status) |
| `platforms/ihp-sg13cmos5l-dgse/` | copy to `engine/flow/platforms/ihp-sg13cmos5l-dgse/` | the platform overlay pnr.tcl sources: `make_tracks.tcl`, `pdn.tcl`, `setRC.tcl`, `fastroute.tcl` (+ reference `tapcell.tcl`, `pad.tcl`, `fill.json`, `cells_latch.v`, `cells_clkgate.v`, `suppress_message.tcl`) |
| `macros.json.fragment` | merge into `engine/flow/macros.json`, or use as `macro_overrides` | the 13 RM_IHPSG13 macro types (LEF/GDS/lib paths, sizes, pin counts) |
| `pin_constraints.tcl` | referenced by config `pin_constraints` | die-edge pin sides matching the QFN64 pad budget |
| `fetch_cmos5l_pdk.sh`, `FILES.md` | run on the DGSE box | how to get the PDK tree, and the exact files the engine reads (not vendored here) |
| `macro_floorplan.py` -> `macro_floorplan.md`, `.svg`, `macro_slots.json`, `config_floorplan_fragment.json` | project config | macro tiling along the die edges, core/die estimate, `die_area_um` / `core_area_um` / `macro_halo` / `macro_placements` fragment |

## 1. How the engine defines a platform (what was found in the DGSE checkout)

* **`engine/flow/pdks.json`** is the platform. One object per PDK name (`sky130A`, `ihp-sg13g2`,
  `gf180`); `config.json "pdk"` selects it. `pnr.tcl` reads it with a flat regex (`jget`), so values
  are literal absolute strings (no `$PDK_ROOT`). Keys actually consumed: `platform_dir`, `liberty`
  (+ `liberty_ss`/`liberty_ff` for the RCX/STA gate, `rcx_rules`), `tech_lef`, `sc_lef`, `stdcell_gds`,
  `klayout_lyt`, `klayout_layermap`, `klayout_defmap`, `site`, `tiehi`, `tielo`, `min_buf`, `insbuf`,
  `abc_driver_cell`, `abc_load_ff`, `tap_cell`, `tap_distance`, `endcap_cell`, `fill_cells`,
  `cts_buf_list`, `cts_root_buf`, `io_hor`, `io_ver`, `min_route`, `max_route`, `min_clk_route`,
  `route_adjust`, `place_density`, `dont_use`, `magicrc`, `netgen_setup`, `klayout_lvs`, `cell_cdl`,
  `latchmap`, `power_net`, `ground_net`, `pins_to_drawing`.
* **`platform_dir`** holds the four Tcl files `pnr.tcl` sources in order: `make_tracks.tcl` (after
  `initialize_floorplan`), `pdn.tcl` (grid definition only; `pnr.tcl` then adds the sky130
  `vccd1/vssd1` macro rules, runs `pdngen` and `check_power_grid`), `fastroute.tcl` (before global
  placement, with `MIN_/MAX_ROUTING_LAYER` exported from `min_route`/`max_route`), `setRC.tcl`
  (after placement). For `ihp-sg13g2` the engine points `platform_dir` at the **ORFS platform**
  (`tools/orfs/flow/platforms/ihp-sg13g2`) and takes cell LEF / liberty / GDS from the PDK; for
  `gf180` it has its own overlay `engine/flow/platforms/gf180-dgse/` (ORFS tcl rewritten in pdngen
  command form). CMOS5L has **no ORFS platform**, so it gets an overlay like gf180's.
* **Macros**: `config.json "macros"` is a list of NAMES resolved by `engine/macro_catalog.py` against
  `engine/flow/macros.json` (keys `lef gds lib verilog width_um height_um`), merged with
  `config "macro_overrides"`; a name absent from the catalog is accepted as a project-owned macro when
  the override gives `lef` + `lib`. The orchestrator exports `DGSE_MACRO_LEFS/LIBS`; `pnr.tcl` reads
  them before `link_design`, places macros from `macro_placements` (`inst:x:y:orient`, instance
  ORIGIN) or `macro_placer: rtl` (rtl_macro_placer) or `macro_placement -halo`, cuts rows with
  `macro_halo` (default 45 um), checks every macro is inside `core_area_um`.
* **Other config keys** used here: `pdk`, `clock_port`, `clock_mhz`, `extra_clocks`,
  `internal_clocks`, `die_area_um` + `core_area_um` (explicit floorplan instead of `core_util`),
  `macro_halo`, `place_density_override`, `pin_constraints` (a Tcl of
  `set_io_pin_constraint -region <edge>:* -pin_names {...}`), `pdn_tcl` / `post_pdn_tcl`,
  `fill_cells`, `extra_lefs`, `extra_gds`, `fill_rules`, `checkpoints`, `threads`.
* **Stream-out**: KLayout `def2stream_dgse.py` with the PDK `.lyt`, into which the orchestrator
  splices the LEF list (`<lef-files>`), copying `klayout_layermap` next to it; `klayout_defmap` is
  passed as `layer_map` (needed on gf180 where unmapped layers streamed to wrong GDS numbers).
* **Signoff dispatch**: DRC takes the Magic path when `magicrc` is set, otherwise the KLayout branch
  -- whose runner path is **hard-coded** to `pdk/IHP-Open-PDK/ihp-sg13g2/.../drc/run_drc.py`
  (`--path --topcell --precheck_drc --no_density --run_dir`). LVS takes the KLayout path
  (`klayout_lvs` = run_lvs.py, `cell_cdl`, `scripts/verilog2cdl.py`) when `netgen_setup` is empty.
* **No pad ring anywhere** in `pnr.tcl` (ORFS's `pad.tcl` / `place_pads` is not wired in); pins are
  placed on the die edge (`place_pins -hor_layers io_hor -ver_layers io_ver`).

## 2. What was derived from where

| item | value for CMOS5L | source |
|---|---|---|
| std cells | `sg13cmos5l_stdcell` (84 cells, same cells/areas as sg13g2, e.g. dfrbp_1 52.6176 um2; tie `L_HI`/`L_LO`, buf `A X`) | `libs.ref/sg13cmos5l_stdcell/{lef,lib}`; local `cmos5l_typ.lib` |
| tech LEF | `sg13cmos5l_tech.lef`: Metal1 H / Metal2 V / Metal3 H / Metal4 V (pitch 0.48 x 0.42), TopMetal1 H (pitch 3.28, offset 1.64, min width/space 1.64, 2 um thick); via rules `via1Array..via3Array`, `viaTop1Array`; no SITE (CoreSite 0.48 x 3.78 is in the cell LEF) | fetched tech LEF |
| routing layers | `min_route Metal2`, `max_route TopMetal1`, `min_clk_route Metal3`, adjustment 0.05 | LibreLane `RT_MIN_LAYER Metal2` / `RT_MAX_LAYER TopMetal1`; ORFS sg13g2 fastroute |
| tracks | LEF pitches (ORFS values for shared layers) | tech LEF; LibreLane `tracks.info` differs (noted in `make_tracks.tcl`) |
| PDN | rails Metal1 0.44/7.56 followpins; Metal4 V straps 1.0/2.0/50/10; TopMetal1 H straps 2.0/4.0/50/10; ring Metal4 + TopMetal1 5.0/2.0; macro grids connect Metal4 -> TopMetal1 | LibreLane `FP_PDN_*` (stripes), ORFS pdn.tcl (rails, ring, macro grid shape); macro LEFs (power pins `VDD! VSS! VDDARRAY!` on Metal4, vertical) |
| IO | `sg13cmos5l_IOPad{In,Out4mA,Out16mA,Out30mA,TriOut*,InOut*,Analog,Vdd,Vss,IOVdd,IOVss}` 80 x 180, `sg13cmos5l_Corner` 180 x 180, `sg13cmos5l_Filler{200..10000}`, sites `sg13cmos5l_ioSite` / `sg13cmos5l_cornerSite`, pins `vdd vss iovdd iovss`, pad edge spacing 140 | `sg13cmos5l_io.lef`, `librelane/sg13cmos5l_io/config.tcl` |
| corners | typ 1.20 V 25 C, slow 1.08 V 125 C, fast 1.32 V -40 C (cells); macros fast corner is `_fast_1p32V_m55C` | lib directory listings |
| dont_use | ORFS list + `sdfbbp_1` | ORFS config.mk, PDK `synth_exclude.cells` = `pnr_exclude.cells` |
| fill | ORFS fill.json minus Metal5/TopMetal2; GDS layers 8/10/30/50/126, datatype 22 | ORFS fill.json, `sg13cmos5l.map` |
| DRC / LVS | `drc/ihp-sg13cmos5l.drc` + `run_drc.py` (deep, no_recommended), `lvs/sg13cmos5l.lvs` + `run_lvs.py`; density/antenna decks in `drc/rule_decks` | LibreLane config.tcl, repo listing; LVS is new in v0.2.0 |
| SRAM macros | `libs.ref/sg13cmos5l_sram` -> symlink to `ihp-sg13g2/libs.ref/sg13g2_sram`; LEF pins Metal2 (all on the bottom edge), power Metal4, OBS Metal1-4, nothing above | local `/tmp/pdk/sg13g2/sram_lef` copies of all 13 LEFs |
| PDK source | IHP-Open-PDK branch `dev` (`ihp-sg13cmos5l/`), mirror `IHP-GmbH/ihp-sg13cmos5l` v0.2.0 (archived, 597570e, 2026-09-23); not on `main` | GitHub API |

## 3. Uncertain / to verify on the DGSE box

1. **DRC runner path is hard-coded** in `orchestrator.py` (sg13g2 `run_drc.py`). Needs a
   `pdk.get("klayout_drc_runner", <sg13g2 default>)`; the fragment carries the key already.
2. **5-layer stack through the engine**: `pnr.tcl` is layer-name agnostic (everything comes from
   pdks.json and the platform tcl), `tests/pd/test_pdn.py` attributes vias by tech-LEF order, so
   nothing is known to assume Metal5/TopMetal2. The ORFS files that did (make_tracks, setRC, pdn,
   fill.json) are rewritten here. Grep the engine for `TopMetal2|Metal5` before the first run anyway.
3. **`io_hor`/`io_ver`**: set to Metal3/Metal2 per the LEF directions (ORFS and LibreLane agree); the
   engine's sg13g2 entry has them swapped and still ran -- if `place_pins` objects, swap.
4. **SITE**: the PDK tech LEF has no SITE (as sg13g2's); `CoreSite` comes from `sg13cmos5l_stdcell.lef`,
   which `pnr.tcl` reads before `initialize_floorplan`. The engine's sg13g2 note kept the ORFS tech
   LEF for this reason; check that `-site CoreSite` resolves with the PDK LEFs alone.
5. **KLayout `.lyt`**: `sg13cmos5l.lyt` carries an empty `<lef-files>` (splice works as for sg13g2)
   and `<map-file>sg13cmos5l.map</map-file>` relative to the `.lyt`; `klayout_layermap` makes the
   orchestrator copy the map beside the patched `.lyt`. Confirm the streamed GDS has Metal4 on 50/0
   and TopMetal1 on 126/0 (gf180 lesson).
6. **Macro power**: `VDDARRAY!` tied to VDD (one 1.2 V domain). Macro PDN connection relies on
   TopMetal1 straps crossing the macro's vertical Metal4 stripes: works for R0/MX/MY/R180 **only**;
   a R90/R270 macro gets no supply (pdngen cannot draw vertical TopMetal1). `macro_floorplan.py`
   emits R0/MX only; if `rtl_macro_placer` is used it must be told not to rotate, or the macro grid
   needs a different strategy. Judge IR with `dgse-pd pdn` on the floorplan checkpoint; the
   LibreLane strap widths (1 um Metal4, 2 um TopMetal1 at 50 um) are a starting point for a
   40 mm2 die, a denser alternative is commented in `pdn.tcl`.
7. **PDN ring widths**: ORFS's 5.0/2.0, not LibreLane's core-ring defaults (2.0 width / 1.0 spacing,
   which would violate TopMetal1's 1.64 um minimum spacing).
8. **Tracks**: LEF/ORFS pitches, not LibreLane's `tracks.info` (which has Metal1/3 at 0.42 x 0.42,
   Metal2/4 at 0.48 x 0.48, TopMetal1 at 2.28). A detailed-route probe decides.
9. **Pad ring**: the chip top does not instantiate pads and the engine has no pad stage. `pad.tcl`
   is adapted from ORFS for when both exist; bondpads are not in the PDK (ORFS `bondpad_70x70` is
   drawn for the sg13g2 stack -- use `libs.tech/klayout/tech/scripts/bondpad.py`), sealring via
   `sealring.py`. The engine run until then is core-only with die-edge pins (`pin_constraints.tcl`).
10. **TopMetal2 references to remove**: none remain in the files here; in the engine itself the
    sg13g2 `setRC.tcl`/`pdn.tcl` are ORFS's and are not used by this entry. `GDS_ALLOW_EMPTY`
    placeholder cells in the SRAM GDS (`RM_IHPSG13_\dP_BITKIT_16x2_*`) may need the same tolerance
    in `def2stream_dgse.py`.
11. **RCX rules**: `IHP_rcx_patterns.rules` is the sg13g2 OpenRCX pattern file (symlinked by IHP);
    one corner only, 7-layer stack described -- verify OpenRCX ignores the missing layers, else drop
    `rcx_rules` as the sg13g2 entry does.
12. **CDL / LVS**: hyphen-free symlink needed (`pdk/sg13cmos5l_stdcell.cdl`), same KLayout reader
    quirk as sg13g2; CMOS5L LVS deck is unexercised (release note "LVS infrastructure added").
13. **Magic/Netgen**: present in the PDK since v0.2.0 but deliberately not used (`magicrc` empty
    keeps the orchestrator on the KLayout DRC/LVS path the sg13g2 run attested).
14. **config/base.json needs to change** (not done here, outside this directory): `"pdk":
    "ihp-sg13cmos5l"`; `"macros"` must become the 13 NAMES (today it is a list of dicts with
    `count/lef/gds/lib/status`, which `macro_catalog.entry()` cannot hash) with the bodies from
    `macros.json.fragment` either in the engine catalog or under `"macro_overrides"`; plus
    `die_area_um`, `core_area_um`, `macro_halo`, `macro_placements` from
    `config_floorplan_fragment.json`, `pin_constraints`, and `place_density_override` (~0.55) for a
    macro-dominated die.

## 4. Floorplan starting point (macro_floorplan.py)

Model: pad-ring inset 340 um (140 bondpad/sealring + 180 pad + 20 ring) -> core 5720 um at the
6.4 mm die; macros in rows along the edges, every row pair facing a channel that holds the group's
own logic (PCORE datapath) and is at least as wide as the pin-escape arithmetic needs; pins face
the channels (R0 down / MX up); the remaining groups, the central logic and the VexRiscv caches in
the centre. Numbers: 291 macros / 18.54 mm2 (config/base.json counts, LEF sizes), std cells
19.41 mm2 of which 11.52 mm2 are the VexRiscv cache arrays as flops (`--caches macro` replaces them
by 1.1 mm2 of SRAM, as the repo die model assumes).

Groups (what belongs together; see `macro_floorplan.md` for the table):

* **PCORE0..7** (16 macros each, 1.52 mm2 + 0.51 mm2 logic): xregister file 4 x 1P_256x64 +
  1 x 1P_256x48 (136x512 as 272x256, time-multiplexed), register banks 8 x 2P_256x32 (two 128x256
  1W2R banks per PCORE), iregister 2 x 1P_64x64 + 1 x 1P_64x16 (inferred from the widths).
* **LOOKUP**: 16 x 1P_512x16 + 16 x 1P_512x8 (stream lookups 24x512, core level).
* **SOC**: 1 x 2P_1024x32 (TCM) + 4 x 1P_1024x64 (scratchpad x2, instruction ROM x2).
* **AFIFO**: 10 x 2P_64x32 + 7 x 2P_64x22 (dual-clock FIFOs with two port clocks: camera, HyperBus/AXI).
* **DPFIFO** (109 macros, 4.63 mm2): the remaining 1P_256x64/256x48/256x32/256x8/64x64/64x16 --
  DP sink/instruction/fetch FIFOs and AXI fabric FIFOs; central, rows facing the DP logic.
  Attribution of DPFIFO and of the iregister split is from the inventory, not the netlist: rerun
  with `--netlist build/dgrid_soc1_chip_top_synth.v` to bind real instance names.

Result (default: 3 PCOREs on S, 3 on N, PCORE6 + LOOKUP on W, PCORE7 + SOC + AFIFO on E, DPFIFO
central, halo 30, util 0.65):

| | |
|---|---|
| PCORE block | 8 rows, 4 channels of 108-136 um (wire and logic estimates agree), 1813 x 1525 um, macro fill 48 % |
| S/N bands | 1525 um deep; W/E bands 1630 um; centre at 6.4 mm: 2180 x 2391 um = 5.2 mm2 for 12.1 mm2 needed |
| verdict at 6.4 mm | **does not fit**; W/E stacks overflow by 0.5 / 1.8 mm too |
| smallest fitting die (this row model) | **7.7 mm** (core 7.0 mm); util 0.75 / halo 20 / exit 90: 7.45 mm; caches left as flops: 9.05 mm |
| repo die model with the real inset | core 34.7 mm2 -> 5.89 mm core -> **6.57 mm die** (the die model's die = 1.15 x core implies only ~210 um of pad ring) |

So the 6.4 mm target is below even the optimistic die model once the 340 um pad-ring inset is
counted, and the row-with-channel floorplan costs another ~20 %. To reach the QFN64 limit (6.6 mm,
core 5.92 mm = 35 mm2) the design needs ~15-20 % less area (8 threads/PCORE, smaller lookups /
ROM / TCM -- the reserve cuts in RUN-ihp-synth-01.md) or a denser macro arrangement than rows
(back-to-back pairs with logic only on one side, macros abutted in the 2P register-bank group),
and the VexRiscv caches must become macros (as flops they alone cost 17.7 mm2 at 65 %). The
`config_floorplan_fragment.json` written here is the 6.4 mm placement of the 182 edge-band macros
(placeholder instance names), usable as a first `macro_placements` once the area question is
settled; `macro_floorplan.py --die 7700 --search` etc. regenerates it for another die.

## 5. Steps on the DGSE machine

```
# 0. PDK tree (dev branch directory beside ihp-sg13g2; sram symlink must resolve)
PDK_ROOT=/home/oem/Documents/soc4_deliverable/DGSE/pdk/IHP-Open-PDK HW/asic/dgse/platform_ihp-sg13cmos5l/fetch_cmos5l_pdk.sh

# 1. engine files
cp -r HW/asic/dgse/platform_ihp-sg13cmos5l/platforms/ihp-sg13cmos5l-dgse  $DGSE/engine/flow/platforms/
#    merge pdks.json.fragment -> engine/flow/pdks.json, pdk_registry.json.fragment -> engine/flow/pdk_registry.json,
#    macros.json.fragment -> engine/flow/macros.json (or keep them in config "macro_overrides")
#    orchestrator.py: make the KLayout DRC runner path come from pdk["klayout_drc_runner"] (item 3.1)

# 2. netlist for the engine (GHDL >= 3 from oss-cad-suite; the engine reads rtl/*.v only)
MEM=ihp HW/asic/dgse/export_verilog.sh                      # -> source/rtl/dgrid_soc1_chip_top.v (TOP in the script)
HW/asic/scripts/ihp_fix_macro_names.py source/rtl/dgrid_soc1_chip_top.v source/rtl/dgrid_soc1_chip_top.v --no-stubs
#    (restores RM_IHPSG13_* module/pin spelling, drops the behavioural macro bodies: the flow reads the macro Liberty files)

# 3. project config (config/base.json): pdk ihp-sg13cmos5l, macros = 13 names (+ macro_overrides), die_area_um /
#    core_area_um / macro_halo / macro_placements from config_floorplan_fragment.json, pin_constraints =
#    <abs path>/pin_constraints.tcl, place_density_override 0.55, checkpoints true
#    -> bin/dgse-pd decide dgrid-soc1 --change KEY=VALUE ... for each (never edit a run's config directly)

# 4. run
bin/dgse-pd brief dgrid-soc1            # then the normal run: synth -> floorplan checkpoint
dgse-pd floorplan <run>                 # macro geometry / channel checks on ck_macros.odb
dgse-pd pdn <run> --checkpoint floorplan   # IR / connectivity of the Metal4 + TopMetal1 grid (VDD, VSS; macro VDDARRAY! on VDD)
#    then global route (the 1 h gate), not detailed route, to see whether the channels hold

# 5. after P&R: gls with the sg13cmos5l_stdcell.v + sg13cmos5l_udp.v + macro verilog models (HW/asic/cocotb, CHIP=hb MEM=ihp)
```

Reference material fetched for this entry sits in the prep machine's scratch
(`/root/.claude/jobs/658ac326/tmp/cmos5l/raw`: LibreLane config.tcl, tracks.info, exclude lists,
tech/cell/IO LEFs, .lyt/.map, DRC deck, ORFS ihp-sg13g2 platform files); none of it is needed on
the DGSE box beyond what `FILES.md` lists.
