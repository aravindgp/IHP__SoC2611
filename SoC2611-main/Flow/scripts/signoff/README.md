# Physical signoff flow: SoC2611 on IHP SG13CMOS5L

DRC, LVS, seal ring, pad ring and density fill for the QFN64 tape-out (IHP order 2 Nov 2026). Every
script calls the PDK's own KLayout decks and fill recipes (IHP-Open-PDK dev branch, `ihp-sg13cmos5l`).
Everything listed under "Validated" was run on real data on 2026-10-31.

## Environment

```
. HW/asic/signoff/env.sh        # sources the DGSE env (KLayout 0.30.5, OpenROAD nix build, Magic, Netgen)
                                # sets PDK_ROOT, PDK=ihp-sg13cmos5l, KLAYOUT_TECH, QT_QPA_PLATFORM
```
Every script sources `env.sh` itself. Python helpers need the `klayout` module, which the DGSE venv
`python3` provides. Scratch output goes to `HW/asic/signoff/work/`, which is not meant to be committed.

## Scripts

| script | purpose |
|---|---|
| `run_drc.sh <gds> <top> [-o dir] [-j N] [-m full\|minimum] [--block] [--maximal] [--no-antenna] [--no-density] [--flat]` | PDK `drc/run_drc.py`: all main rule tables + `antenna.drc` + `density.drc`, run in parallel. It merges the results into `<dir>/*_full.lyrdb` and prints a per-rule summary with waivers applied (`summary.txt/json`). Exit codes: 0 = no unwaived violations, 1 = violations, 2 = tool error. |
| `summarize_lyrdb.py [--waivers f]... [--json f] lyrdb\|dir` | Counts violations per rule and per cell, and applies waivers (`rule[@cell]` fnmatch patterns). |
| `run_lvs.sh <gds> <top> <cdl> [-o dir] [--deep] [--ports-ok] [--no-taps] [--implicit N] [--blackbox PAT]...` | PDK `lvs/run_lvs.py` (sg13cmos5l.lvs). `--blackbox` runs a patched private copy of the deck (`patch_lvs_deck.py`) that applies `blank_circuit(PAT)` before `align`. Exit codes: 0 = match, 1 = mismatch, 2 = error. |
| `lvsdb_report.py <lvsdb>` | Lists the circuits that don't match, with their first mismatching pins, nets and devices, plus a top-level port diff (what the deck's strict `flag_missing_ports` check fails on). |
| `make_sealring.py --width W --height H -o out.gds [--input chip.gds --top TOP]` | Seal ring. A pure-klayout.db port of the PDK PCell `sealring_code.py` (M1-M4-TM1 stack, edgeBox 25 um). The EdgeSeal boundary (39/4) is the die outline, and the metal ring sits 32.2-36.4 um from the die edge, with corner steps out to 53.2 um. `--input` adds the ring around an existing chip top. |
| `make_padring.py [--config padring/padring_qfn64.json] [--outdir dir]` | QFN64 pad ring. See "Pad ring + seal ring" below. |
| `padring/test_padring_openroad.sh [dir]` | Places the ring with OpenROAD from `padring.tcl` on a pad-only netlist, then `compare_padring.py` checks the DEF against `padring.gds`. |
| `fill_tiled.py <in.gds> <out.gds> [--tile 1000] [-j 3] [--no-activ] [--no-metal]` | Density fill using the PDK recipes (`macros/sg13cmos5l_filler_{ActGatP,Metal}.lym`), run tile by tile in separate KLayout processes (see "Density fill" below). Needs the seal ring in the layout. |
| `fill_topup.py <filled.gds> <out.gds> [-j 12] [--layers M1,M2,M3,M4,TM1,Activ,GatPoly] [--macros RE]` | **Density top-up after `fill_tiled.py`**: fills the irregular space the PDK lattice leaves between routes and cells with rule-clean free-form pieces (see "Density closure" below). Never inside macro outlines on Activ/GatPoly/M1-M4; TM1 also over the SRAMs. |
| `density_fast.py <gds> [-j 12] [--attrib] [--json f] [--csv f] [--ref density.lyrdb]` | **The PDK `density.drc` numbers in minutes** (AFil.g/g1/g2/g3, GFil.g, M1-4.j/k, M1-4Fil.h/k, TM1.c/d). Same layer derivation, chip area, 800 um windows/400 um step and edge "backup" windows as the deck. `--ref` diffs against a deck lyrdb; `--attrib` adds per-window macro and fill shares. Exit 0 = all pass. |
| `check_fill.py <gds> [--cell DG_TOPUP_FILL] [-j 8]` | Filler width/space/max-size (AFil.a/a1/b, GFil.a/b/c, MFil.a1/a2/b, TM1Fil.a/a1/b: rules only the maximal deck has) plus filler-to-drawn spacing, in one tiled pass. |
| `run_fill.sh <in> <out> [--no-activ] [--no-metal]` | The PDK's own untiled `scripts/filler.py`. Use it only on small layouts: it needed >9 GB on the 6.6 mm die. |
| `run_signoff.sh <chip.gds> <top> <chip.cdl> [--has-sealring] [--no-fill] [--no-topup] [--pdk-density] [-j N] [--srams] [--blackbox PAT]` | Runs seal ring (`make_sealring.py --input`), tiled fill (`fill_tiled.py`, `--abstract-macros` with `--srams`) + `fill_topup.py`, `density_fast.py` (`density.txt/json`), DRC without the 16 h density deck (`--pdk-density` adds it back) and LVS (`--deep`) in one go and writes `<top>_final.gds`. `--blackbox PAT` is passed through to LVS. |

## Validated (2026-10-31)

### DRC (`run_drc.sh`, deep mode, main + antenna + density)

| layout | result |
|---|---|
| std cell `sg13cmos5l_dfrbp_1` | Clean apart from global density (GFil.g, M2-4.j, TM1.c). Density is block-level only. |
| SRAM `RM_IHPSG13_1P_1024x32_c2_bm_bist` (sg13g2 GDS, symlinked) | Clean apart from AFil.g and TM1.c (density). The CMOS5L forbidden-layer table passes, so the sg13g2 SRAM uses no Metal5/TM2/MIM. |
| IO cell `sg13cmos5l_IOPadInOut16mA` (as top) | Clean apart from density. |
| **DGSE-routed block on the cmos5l platform** (`work/c5l-mini`: 112 cells, engine run with `pdk: ihp-sg13cmos5l`, `gds/dg_mini.gds`) | **0 violations** except the 7 global density rules (block, waived with `--block`). Antenna clean. |
| seal ring alone, 400 x 400 um | Sealring table (Seal.*) clean, all other rules clean except density. |
| seal ring 400 um + tiled fill | **0 geometric violations.** Densities: Activ 32.6 %, GatPoly 17.6 %, M1/M2 35.0 %, M3/M4 31.7 %, TM1 27.6 %. All are diluted by the 36 um unfillable edge, which is 17 % of a 400 um die but about 2 % of a 6.6 mm die. |
| **empty QFN64 pad ring + seal ring, 6.6 mm** (`work/padring/padring.gds`) | 1383 markers in total. All of them are density markers from the empty die (AFil.g2/MxFil.h 800 um windows, plus globals), except two groups: **M1.e x 24** inside the IO cells (waived) and **Pad.fR_TM1 x 88**, a recommended rule (waived). No Seal.*, Pad.* (hard), latch-up or forbidden-layer errors. |
| **same, after `fill_tiled.py`** (`work/padring/padring_filled.gds`) | **0 unwaived violations.** Only M1.e x 24 (IO cells) and Pad.fR_TM1 x 88 (recommended) remain, both waived. **All density rules pass**, global and 800 um windows: Activ 47.9 %, GatPoly 24.8 %, M1 50.8 %, M2 48.1 %, M3/M4 47.1 %, TM1 48.3 %. Run time 770 s at `-j 4`, peak about 2.6 GB per process. The sealring table alone took 705 s (Seal.l). |

**Antenna:** included by default (`antenna.drc`). Clean on the routed block.

**`sg13cmos5l_maximal.drc`** is OFF by default (`--maximal` turns it on). run_drc.py's own help calls it
"not applicable in CMOS5L". On the empty 6.6 mm pad ring it grew past 13 GB without reporting a rule, so
never run it on the full chip on this machine.

**Memory:** main tables on the 6.6 mm pad ring used up to about 1.2 GB per table process, with `-j N`
processes running at once. Use `-j 3`/`-j 4` while P&R jobs are running (cgroup limit 32 GB, shared).

### LVS (`run_lvs.sh`)

| layout vs netlist | result |
|---|---|
| `sg13cmos5l_dfrbp_1` vs PDK stdcell CDL | MATCH (flat). |
| negative test: `inv_1` with one W changed in the CDL | MISMATCH detected, exit code 1. |
| **DGSE-routed `dg_mini` vs engine CDL** (`build/dg_mini.cdl`, from verilog2cdl over `sg13cmos5l_stdcell_sram.cdl`) | **MATCH with `--deep --ports-ok`.** In deep mode all circuits match and the 28 signal ports match. Strict port mode fails only because DGSE's GDS carries no **VDD/VSS text labels**. Flat mode is unusable for routed blocks: std-cell pin labels leak into top-level net names. **Always use `--deep` for blocks and the chip.** |
| SRAM `RM_IHPSG13_1P_1024x32` (transistor level) vs its CDL | Not clean. (1) The sg13g2 SRAM CDL names the metal resistor in `RSC_IHPSG13_CDLYX1_DUMMY` `lvsres`, but the CMOS5L deck extracts `res_metal1`. Fix it with `sed 's/ lvsres / res_metal1 /'` on the CDL; that circuit then matches. (2) In deep mode, `RSC_IHPSG13_CINVX2/X8` and `FILLCAP4/8` get flattened on the layout side. `--blackbox 'RSC_IHPSG13_CINVX*'` fixes CINVX, but FILLCAP still has 2 unnamed pins. (3) Flat mode ran for more than 30 min and was killed. SRAMs are IHP-qualified hard macros, so at chip level black-box them: `--blackbox 'RM_IHPSG13_*'`. That is UNTESTED on a chip so far (see gaps). |

### Pad ring + seal ring

`make_padring.py` writes into `work/padring/`:

- **`padring.gds`** (top cell `soc2611_padring`, 6600 x 6600 um), containing:
  - the seal ring;
  - 4 `sg13cmos5l_Corner` cells;
  - 64 pads: 48 signal plus 16 supply (VDD/VSS/IOVDD/IOVSS on each side);
  - 504 IO fillers;
  - 64 bondpads.
- **`bondpad_70x70.gds/.lef`**: the CMOS5L bondpad, equivalent to the PCell `bondpad` with shape=square, stack=nil (the PDK default). It is TopMetal1 70x70, Passiv opening with 2.1 um enclosure, plus dfpad. ORFS's `bondpad_70x70` cannot be used because it is drawn on Metal5/TopMetal2.
- **`padring.tcl`**: OpenROAD commands for the same ring (`make_io_sites -offset 140`, `place_pad -row ... -location`, `place_corners`, `place_io_fill`, `connect_by_abutment`, `place_bondpad -offset {5 -70}`). Run it after `initialize_floorplan` in a chip-level P&R with pad instances in the netlist.
- **`padring_stub.v`**: pad instances only. Instance names are `pad_<signal>` and `pad_<side>_<VDD|VSS|IOVDD|IOVSS>`.
- **`bond_table.csv`**: package pin, pad, cell and bondpad centre, as input for the bonding diagram.

Geometry:
- The IO row starts 140 um from the die edge (LibreLane `PAD_EDGE_SPACING`).
- Bondpads sit in the 70-140 um band and abut the pad cell's TopMetal1 `pad` pin.
- The inner edge of the IO ring is at 320 um, inside the DGSE 340 um core inset.
- There are 16 pads per side at a **372 um pitch**, centred between the corners. The QFN64 lead pitch is 0.5 mm on a 9 mm body, so wire bonding is uncritical.
- Orientations follow OpenROAD: pads N/FS/W/FW, corners N/FN/S/FS.

**Cross-check:** `padring/test_padring_openroad.sh` gives `PADRING DEF == GDS`. All 132 pads, corners and bondpads match exactly, and the filler coverage XOR is 0.

**Pad order:** the order in `padring_qfn64.json` is a DRAFT grouped by interface (HyperBus south, camera north, misc east, GPIO and camera control west). Edit the JSON and re-run.

### Density fill

- `fill_tiled.py` filled the whole empty 6.6 mm frame with Activ, GatPoly, M1-M4 and TM1 in **219 s**, 49 tiles, `-j 3`. Peak was 2.6 GB per process and 6.4 GB in total.
- The untiled PDK `filler.py` was killed at 9.3 GB.
- Tile seams lose about 1.5 % of fill cells (4032 vs 4096 on the 400 um test) and stay DRC-clean.
- The fill frame is the inside of the seal ring, so the seal ring must exist first.
- Activ fill does not fit between standard-cell rows (AFil.d keeps 1 um from NWell edges). Active density in the core comes from the cells themselves plus `decap_*`/`fill_*` (decap_8 39 %, fill_8 27 % Activ). Fill raises it in the IO ring, the core-to-pad gap and macro channels.
- Alternative for metals: OpenROAD `density_fill -rules engine/flow/platforms/ihp-sg13cmos5l-dgse/fill.json`, which the DGSE flow already wires into `pnr_resume*.tcl`. Then run `fill_tiled.py --no-metal` for Activ/GatPoly only.

### Density closure on the full chip (2 Nov, rehearsal chip `/workspace/chip_rehearsal2`)

**Problem.** The PDK lattice fill alone (`fill_tiled.py --abstract-macros "RM_IHPSG13_.*"`, 17 min) left
**212 density violations** on the rehearsal chip (PDK `density.drc`, 16 h): AFil.g2 x21, M1Fil.h x25,
M2Fil.h x85, M3Fil.h x42, M4Fil.h x37 (800 um windows at 15-25 %), plus global **M2.j 27.87 %** (min 35)
and **GFil.g 14.89 %** (min 15). TM1 passed with no margin (25.08 %, min 25).

**Root cause: the std-cell core, not the SRAMs.** (`density_fast.py --attrib`.)
- The 298 RM_IHPSG13 macros (12.94 mm2, 29.7 % of the die) are dense on every layer they use: Activ
  34-44 %, GatPoly 19-20 %, M1 37-40 %, M2 33-41 %, M3 37-46 %, M4 41-48 % (measured from the SRAM GDS,
  per macro type). Only TopMetal1 is 0 % inside them.
- Outside the macros the averages were Activ 35.6 %, GatPoly 12.9 %, M1 34.5 %, **M2 23.9 %**, M3 33.2 %,
  M4 33.8 %. The failing windows are 86-97 % std-cell core (3-11 % macro, 0-2 % pad ring), with only
  0.4-10 % of their area filled: the lattice squares (3.5/4 um at 5/6 um pitch, 1x1 at 2.5 um) need
  1.84-4.84 um of free space aligned to the global lattice, which the routed core rarely has.
- Macro interiors cannot be filled (they use Activ..M4; the SRAM docs give no fill allowance), so the
  fix had to come from the space between routes and cells.

**Fix: `fill_topup.py`** after the lattice fill. Free space per layer = seal-ring interior minus macro
outlines (kept out by the layer's largest rule distance) minus every PDK-recipe exclusion; it is cut by a
5 um grid (0.43 um lines; TM1 13 um / 3.01 um) and opened by the min. filler width, and any piece with a
Euclidean width/space/notch marker is dropped. Pieces are free-form Manhattan polygons of 1x1..4.57x4.57 um
(GatPoly 0.7..4.2, TM1 5..10). Rule distances +10 nm. TM1 is also filled over the SRAMs (no TM1 inside).

| rule | limit | lattice fill only | + `fill_topup.py` |
|---|---|---|---|
| AFil.g / g1 (global Activ) | 35..55 % | 36.49 % | 44.25 % |
| AFil.g2 / g3 (800 um windows) | 25..65 % | 21 fail, min 21.11 % | pass, 37.03..54.00 % |
| GFil.g (global GatPoly) | >= 15 % | **14.89 % FAIL** | 24.52 % |
| M1.j / k | 35..60 % | 35.82 % | 49.10 % |
| M2.j / k | 35..60 % | **27.87 % FAIL** | 36.92 % |
| M3.j / k | 35..60 % | 35.61 % | 45.58 % |
| M4.j / k | 35..60 % | 37.61 % | 56.75 % (3.2 points below the max) |
| M1Fil.h / k (windows) | 25..75 % | 25 fail, min 18.25 % | pass, 39.61..60.91 % |
| M2Fil.h / k | 25..75 % | 85 fail, min 15.49 % | pass, 27.90..43.26 % |
| M3Fil.h / k | 25..75 % | 42 fail, min 14.96 % | pass, 30.78..63.30 % |
| M4Fil.h / k | 25..75 % | 37 fail, min 15.44 % | pass, 43.32..70.12 % |
| TM1.c / d | 25..70 % | 25.08 % | 33.05 % |
| **total** | | **212 violations** | **0** |

Added: M1 5.79, M2 3.94, M3 4.34, M4 8.34, TM1 3.47, Activ 3.38, GatPoly 4.20 mm2 (3.9 M shapes).

**Validation.**
- `density_fast.py` vs the PDK deck on the lattice-filled chip: the same 212 violations (212 common, 0 extra,
  0 missing), max ratio difference 0.0005 %-points, globals identical to 3 decimals. On three 800 um
  clips of the topped-up chip (std-cell core / std-cell core / pad ring + SRAMs) the PDK deck's layer
  densities equal `density_fast.py`'s to 0.01 % and no window rule fires.
- Fill DRC: PDK tables activfiller, gatpolyfiller, metalnfiller, topmetal1, topmetal1filler, offgrid,
  angle on the three clips: **0 violations**. `check_fill.py` on all 3.9 M top-up shapes (width, space,
  max size, maximal-deck rules): **clean**.
- Not run: the full-chip PDK density deck on the topped-up chip (16 h); `density_fast.py` replaces it in
  the loop. Start it at low priority only when the machine is idle.

**Run time on the full chip** (measured next to the running DRT, load average 60-75 on 32 CPUs):
`fill_tiled.py` 17 min, `fill_topup.py -j 12` 23 min (~4 GB), `density_fast.py -j 12` 8.5 min (~4 GB;
the macros are measured once per master and instance instead of being flattened in every tile:
`--no-macro-split` is the slow reference mode, >50 min). GDS grows from 0.82 to 1.13 GB.

**Margins to watch on the final chip:** M2.j is at 36.9 % (needs 35) and M4.j at 56.8 % (max 60); the
lowest M2 window is 27.9 % (needs 25). If the final routing adds a lot of M4 and M4.k fails, re-run
`fill_topup.py --shrink M4=0.2` (pieces pulled back from the free-space edge; on a std-cell clip
`M4=0.5` cut the M4 top-up from 0.213 to 0.047 mm2 per 0.64 mm2). Do not drop the M4 top-up entirely:
lattice-only M4 had 37 M4Fil.h windows below 25 %.

```bash
S=HW/asic/signoff
python3 $S/fill_tiled.py chip_seal.gds chip_pdkfill.gds --top soc2611_chip_top -j 2 --abstract-macros 'RM_IHPSG13_.*'
python3 $S/fill_topup.py chip_pdkfill.gds chip_final.gds --top soc2611_chip_top -j 12
python3 $S/density_fast.py chip_final.gds -j 12 --attrib --json density.json      # exit 0 = all pass
python3 $S/check_fill.py chip_final.gds --cell DG_TOPUP_FILL -j 8                  # optional, flat drawn layers: slow
```

## Waivers (`waivers/`)

- `drc_waivers.txt`, applied by default:
  - **`M1.e@sg13cmos5l_IOPad*`**: 6 markers each in IOPadOut4mA, InOut4mA, Out16mA and InOut16mA, inside the output driver (x 33.7/38.2 um, y 17-63 um). A flat check confirms the geometry. The deck does not flag it when the IO cell itself is top. The cell is unmodified PDK IO, so ask IHP to confirm.
  - **`Pad.fR_*`**: recommended rule (TM1 exit length 7 um). The bondpad abuts the 3 um-high pad-pin strip, the same as ORFS sg13g2.
- `block_density.txt`, used only with `--block`: all global and windowed density rules, for std-cell, macro and block runs. Never use it on the final chip.

## Chip integration + signoff runbook (post-DRT core ODB -> tape-out GDS)

The DGSE chip runs (e.g. `c7w32-6600-respread`) route the **core only**. `pin_constraints.tcl` places
the 60 chip ports with `set_io_pin_constraint -region bottom|left|top|right:*`, i.e. **on the die
edge**, so their wires cross the 340 um margin where the pad ring goes. No pad cells are in the
netlist. The integration below fixes that as a post-route ECO on the routed ODB. Nothing in the core
run has to change.

**Validated end to end on `work/c5l-mini2k`.** This is a DGSE cmos5l run on a 2000 um die with the
pins on the die edge, the same situation as the chip.
- Integration: 44 pads.
- Seal ring and tiled fill.
- **DRC: 0 unwaived.** Only Pad.fR_TM1, a recommended rule, remains, and it is waived. All density rules pass.
- **LVS: MATCH in strict port mode.**

The pad and power-strap steps were also run on the real `c7w32-6600-respread/build/ck_cts.odb`:
- 64 pads placed, 60 ports moved.
- Pad-PDN sync: 1819 shapes added, 935 deleted.
- BEOL DRC (M1-TM1, all vias, pad rules) of PDN + pad ring + straps across the whole 6.6 mm chip: **0 unwaived**.
- Peak memory was 1.3 GB.

What the scripts do:

| step | script | what it does |
|---|---|---|
| 0 | `make_padring.py --portmap padring/portmap_qfn64.json` | `work/padring/`: `padring.tcl`, `pad_connect.tcl` (pad -> pad pin -> chip port), bondpad LEF/GDS. Check the map first with `padring/check_portmap.py` (48 pads vs 60 ports of the chip7w32 netlist: 0 errors). |
| 1 | `chip_integrate.tcl` STOP_AFTER=place | Creates the 64 pad instances. Moves every core net from its die-edge BTerm to the pad's `p2c`/`c2p`/`c2p_en`. **Destroys those nets' routing** (it ran to the die edge). Creates the external nets/ports `<pad>_PAD`. Runs padring.tcl (sites, pads, corners, IO fill, abutment, bondpads), connects the supply bondpads, places pins on the bondpads. |
| 2 | `pad_pdn_straps.tcl` | **Pad <-> core-ring power.** pdngen cannot add `-connect_to_pads` to an existing grid, so it re-runs the core's own PDN script (pdn v2 detects the pads and adds `-connect_to_pads`) on a scratch copy with no routing. It then diffs every PDN shape not entirely inside the core and writes `straps.tcl` (DEL old + ADD new: straps, their vias, re-trimmed stripe ends). |
| 3 | `chip_integrate.tcl` START_AT=pdn | Sources `straps.tcl`, then `global_route` (it routes only the unrouted nets: 28 of 130 in the mini test) and `detailed_route` (existing routing kept; LVS proves it). Re-creates the bondpad pins (DRT-0302 workaround). Writes `chip.odb/.def/.v`. |
| 4 | `stream_chip.sh` | DEF -> GDS with the cmos5l map. LEF: tech + stdcell + IO + all SRAMs + bondpad. GDS: stdcell + IO + SRAMs + bondpad (DGSE `def2stream_dgse.py`). |
| 5 | `make_chip_cdl.sh` | `verilog2cdl.py`. Merges the cell CDLs (dedups the RSC_* subckts repeated in every SRAM CDL, `lvsres`->`res_metal1`, fixes a PDK IO-CDL bug where `ptap1` slipped onto the previous line), sets IO-cell `iovdd/iovss` to IOVDD/IOVSS, adds IOVDD/IOVSS ports, and inlines everything (no `.INCLUDE`: KLayout cuts include paths at '-'). |
| 6 | `run_signoff.sh ... --srams` | Seal ring -> `fill_tiled.py` -> `run_drc.sh` -> `make_lvs_view.py` -> `run_lvs.sh --deep`. |

**LVS view.** The open CMOS5L deck does not match IHP's IO cells even standalone (IOPadIn: diode/LevelDown mismatches). `make_lvs_view.py` therefore:
- reduces IO cells, and with `--srams` the RM_IHPSG13 macros, to their metal stack (FEOL deleted);
- empties their CDL subckts.

LVS then proves:
- the core netlist (std-cell transistors);
- all pad and macro pin connections;
- pad <-> bondpad;
- the pad-ring rails;
- the pad <-> core-ring straps.

It does not cover the IHP-qualified IO and SRAM internals. All 30 SRAM GDS have every CDL pin labelled at the top, which is what this needs.

### Commands (tonight; run steps 1-3 after the DGSE DRT has finished and freed its memory)

```bash
S=HW/asic/signoff                       # from the repo worktree root
R=/root/.claude/jobs/658ac326/tmp/dgse/DGSE/runs/c7w32-6600-respread
O=$S/work/chip_c7w32                    # output dir
PDN=HW/asic/dgse/runs/cmos5l-01/pdn_c5l_sram_v2.tcl     # = config pdn_tcl of the run

# 0. pad ring files + port-map check (seconds)
python3 $S/make_padring.py --portmap $S/padring/portmap_qfn64.json        # -> $S/work/padring
python3 $S/padring/check_portmap.py $S/padring/padring_qfn64.json $S/padring/portmap_qfn64.json \
        $R/build/soc2611_chip_top_synth.v                                # expect "0 error(s)"

# 1-3. integrate the routed core (final.odb when the engine has written it; else the last ck_droute*.odb)
bash $S/run_chip_integrate.sh $R/build/final.odb $S/work/padring $O $PDN 16
#    stop early to inspect: append "place" | "straps" | "pdn" as 6th argument
#    look at: $O/1_place.log  2_straps.log  3_route.log  route_drc.rpt (must be empty)

# 4. GDS
bash $S/stream_chip.sh $O/chip.def soc2611_chip_top $O/gds/chip.gds $S/work/padring

# 5. LVS netlist
bash $S/make_chip_cdl.sh $O/chip.v $O/chip.def soc2611_chip_top $O/lvs/chip.cdl

# 6. seal ring + fill + DRC + LVS  (final tape-out GDS: $O/signoff/soc2611_chip_top_final.gds)
bash $S/run_signoff.sh $O/gds/chip.gds soc2611_chip_top $O/lvs/chip.cdl -o $O/signoff --die 6600 -j 3 --srams
#    results: $O/signoff/drc/summary.txt, $O/signoff/lvs/run_lvs.stdout (+ lvsdb_report.py *.lvsdb)
```

**Expected cost on the chip** (estimated from the tests):
- Steps 1-2: about 2 min, under 2 GB (measured on ck_cts).
- Step 3: GRT plus DRT initialisation and pin access over 300k instances and 298 SRAMs, then routing about 60 nets. Probably tens of minutes and a GDS-size memory footprint; run it at 16 threads once the core DRT is done.
- Stream: minutes, a few GB.
- Fill: on the full 6.6 mm chip each 1 mm tile process reached **12 GB** (rehearsal 1 Nov; the 2 mm test needed <3 GB). run_signoff.sh now runs fill at `FILL_J=2` by default; never run fill, DRC or LVS while a DGSE DRT (15-16 GB) is running.
- Full DRC: main tables plus antenna plus density, likely more than 1 h. The sealring table (Seal.l) was the slowest on the filled frame (705 s).
- LVS (deep, SRAM view): tens of minutes, several GB.

### For the next P&R run (removes the ECO)
- Put the pad cells into the chip-top netlist, using the instance names of `pad_connect.tcl`.
- `source work/padring/padring.tcl` between `initialize_floorplan` and PDN. pdn v2 then adds `-connect_to_pads` by itself.
- Drop the die-edge `pin_constraints.tcl`.

## Open gaps / risks

1. **DGSE engine signoff uses the wrong decks for cmos5l.** The engine's own `drc`/`lvs` stages report "sg13g2 deck" even with `pdk: ihp-sg13cmos5l` (seen in work/c5l-mini/events.jsonl). `pdks.json` already notes "ENGINE CHANGE NEEDED". Use the scripts here for signoff, not the engine's PASS.
2. **SRAM black-box at chip level** (`--blackbox 'RM_IHPSG13_*'`) is implemented (`patch_lvs_deck.py`; the mechanism was verified on SRAM sub-cells) but not yet tested on a chip with SRAMs. It depends on the SRAM GDS pin labels lining up with the CDL pin names. Test it on the first routed chip, or on a small DGSE block with one SRAM.
3. **RC extraction:** there are no CMOS5L OpenRCX rules. `ihp-sg13cmos5l/libs.tech/librelane/IHP_rcx_patterns.rules` is a **symlink to the sg13g2 file** (LayerCount 7: M1-M5, TM1, TM2). OpenRCX maps by layer index, so CMOS5L TopMetal1 (layer 5) would get sg13g2 **Metal5** tables. That is wrong for TM1 (2 um thick, 3.5 um oxide; see `libs.tech/parasitics/itf/sg13cmos5l_typ.itf`). M1-M4 match the ITF stack (M1 0.42, M2-M4 0.49 um; ox 0.96/1.03/1.03/1.34). Approximation: use the rules as they are for M1-M4 signal routing; TM1 carries almost only power. Or keep the global-route/placement parasitics (`setRC.tcl`) for STA signoff, with margin. A proper fix is to generate rules from the ITF (OpenRCX `bench` flow plus a field solver), which is not done.
4. **Seal.l runtime on the filled chip.** The sealring table's Seal.l is flat and slow on fill-heavy layouts. If it dominates, run it once separately (`run_drc.sh ... -- --table=sealring`) and the other tables with `-- --table=...` lists.
5. **Seal ring generator is a port, not the PCell itself.** The pycell4klayout-api submodule ("cni") is empty in this PDK checkout, so `scripts/sealring.py`/`bondpad.py` cannot run. The port is DRC-clean (Seal.* table), but compare it with IHP's PCell output if a populated PDK becomes available.
6. **Pad.fR_TM1** (recommended) could be fixed by shrinking dfpad and Passiv on the IO-cell side. It is not done; check IHP's packaging/bond rules for the 70 um pad and the 372 um pitch.
7. **IHP die-edge rules:** the edge spacing (140 um ring offset, 25 um edgeBox in the seal ring) follows the PDK/LibreLane defaults. Whether IHP's dicing street lies outside the 6.6 mm EdgeSeal boundary should be confirmed with IHP (see `HW/asic/dgse/IHP_confirmation_request_2026-10-30.md`, item 4).
8. **Power labels:** DGSE GDS has no VDD/VSS text, so strict-port LVS of a core-only GDS fails. At chip level the supplies come from the pad cells.
