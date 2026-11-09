# SoC2611 elbow, loop 1 on 10 Nov 2026: staged macro move (OpenROAD dcf36133)

## Why K2 / K2b went wrong (from the dcf36133 GRT source + the v2 logs)
1. **Stale capacity.** `eco_macroshift.tcl` runs `global_route -start_incremental` *before* moving the macros.
   `startIncremental()` calls `initFastRoute()`, which computes the macro blockages from the current placement.
   After that, the callback (`inDbPostMoveInst`) only marks nets dirty; it never recomputes capacity. So K2's 283 nets
   were global-routed against the **old** macro positions: their guides go across the new footprints and avoid the
   vacated gap.
2. **EXTRA_NETS are never re-global-routed.** `updateDirtyNets()` re-routes a dirty net only if
   `pinPositionsChanged()` is true. The disconnect+reconnect of one ITerm saves the pin set at PreDisconnect and
   finds the same set at the end. Result: the wire is destroyed and the **old guides are kept**.
   - This hit K2's 131 knot nets and all 563 nets of K2b.
   - Evidence: DRT reports the same "Number of guides: 3,464,923" in K2.log and K2b.log.
   - So K2b was 563 nets re-routed by DRT along guides that cross the lifted macros. That gave 45k TopMetal1 shorts
     (the only layer left over the macros); it was not GRT overflow.
3. **Phantom usage.** `initFastRoute` turns every existing wire into capacity usage (`findNetsObstructions`). The
   scripts delete wires after `-start_incremental`, but `removeWireUsage` only runs on wires that still exist. The
   deleted nets therefore still occupy their old tracks.
4. **Unstripped wires.** Nets lying under the new footprints were not stripped: 1,386 shorts against the macro
   instances and the 143 power shorts.
   - The 143 are Metal4 signal wires crossing the macros' Metal4 power pins: 40 VDD!/VSS!/VDDARRAY! stripes of 2.81 um
     cover 47 % of the macro width.
   - With MX orientation, the full-height VSS! and the VDD! 0-38.8 um band sit at y 2996-3034.8, exactly the newly
     covered band.
5. **PDN not moved** (invisible to DRT, which reports nothing between two fixed shapes):
   - core Metal1 rails, Metal4 stripes and Via1-3 now sit under the macro (a VDD stripe over a VSS! pin is a hard
     short for LVS);
   - the macro TopVia1 stayed at the old y.
6. **Plain `detailed_route`** restarted pass 0 chip-wide, which gave the 34k.

## Recommendation: option d1, move only slice[27] east by 63.36 um (132 Metal2 pitches)
- New box x 2883.92-3120.72, y 2930.44-2994.80. It clears the 256x32 edge (2883.44) by 0.48, and the 2.8 um overlap
  is gone.
- The lower channel now runs straight up to slice34 (y 3094.8). The westward jog can use 184 um of height
  (y 2910-3094: the vacated 63×64 um field plus the pocket) instead of the 20 um slot, about 9x the Metal3 tracks.
- Newly covered area: 63.36 × 64.36 = 4,078 um².
  - K2: 3 × 236.8 × 40 = 28,416 um².
  - b40: 10,298 um². b63: 16,311 um².
- Pin nets: 43 (b: 172, K2: 129).
- The x shift is parallel to the TopMetal1 straps, so the macro-grid vias are translated by dx exactly. Only about 18
  Metal1 rails and 1-2 Metal4 stripe pairs are cut.
- The pitch-multiple shift keeps the pin-to-track offsets (the DRT-0418 situation does not change).
- The east is free: the next macros are 64x22 at x 3350.4 and 64x32 at 3470.4. Std cells under the new box get
  pushed east.
- Expected strip set: 43 pin nets + nets of the pushed cells + footprint nets + 110 knot nets = about 200-300.
  The side-move rounds handled this range well. The exact number comes from the dry run.

Options compared:
- **b (column east 40):** leaves 22.88 um (about 47 Metal2 tracks) of the 60 um channel still dead-ending. It moves 4
  macros and 172 pin nets. Only worth it at 63.36, and then it equals d1 plus 3 extra macros.
- **a (K2 staged correctly):** works with these scripts (`shift_K2.txt`). But the strip set is at least 283 + 131 + 132
  (marker lower bound), so 550 or more. The pocket shrinks from 100 to 60 um (K2: 421 shorts in it, many on
  TopMetal1), and the y move needs re-derived TopVia1 (less certain path). Second choice.
- **c (TopMetal1):** dcf36133 has no per-net layer range (`getNetLayerRange` = global/clock only). The only way is
  explicit guides (`dbGuide_create` / `read_guides`), i.e. `/workspace/knot/out/guide_knot.py` + `eco_knot.tcl`
  GUIDES_FILE.
  - TopMetal1 is horizontal and must land on Metal4 outside the macros, so it adds only 3-6 tracks to the slot. It
    helps the E-W nets, not the N-S jog.
  - Still valid as the fallback. eco_knot's EXTRA_NETS path has flaw 2 above; its GUIDES_FILE nets are fine.
- **Rejected:** flip (MX→R0 puts the pins on the gap side) and a 2.8 um nudge (the channel offset stays).

## Morning sequence
Set `SIGNOFF=<repo>/Flow/scripts/signoff`, `DGSE=<repo>/Flow/scripts/dgse`, `IN=<latest clean-up db>` (the 32-pass
guidetest continuation).

1. **Compare the options (read-only, about 5 min):** `bash compare_options.sh $IN`
   - Gate: d1 has no `FOOT ERROR`, a STRIP total of about 300 or less, and PUSH under about 60 cells.
   - Look at `PDN ... new-footprint` (cuts) and `old-footprint via:Metal4-TopMetal1` (vias to translate).
2. **Loop 1:** `bash run_lift_loop.sh $IN L1_d1 shift_d1_s27_east63.txt knot_extra_nets.txt`
   - ECO (eco_lift_staged.tcl, no DRT) gates:
     - `GRT-0009 rerouting N` with N ≥ 0.9 × strip set (the script stops otherwise);
     - `stripped multi-pin nets without guides: 0`;
     - `guides on Metal1-3 inside the new footprints` about 0;
     - `nets with wires still under the new footprints: 0`;
     - `ECO_PDN_AUDIT ... clean`;
     - `check_placement` passes.
   - DRT: drt_steps STEP_START=17 END=19 STEP_ALL_AS_INCR=1. Pass 17 (ALL→INCR) routes the stripped nets.
     - Expect the pass-17 count in the 3-6k range of the side-move rounds.
     - More than 20k means stop and look at the layer mix.
   - Count: knot_measure (window/elbow, total, power shorts) and pg_check (check_power_grid VDD/VSS plus audit).
   - GO if all hold: elbow square ≤ 300, total ≤ 1,760, power shorts 0, PG ok.
3. **If GO:** continue drt_steps 20-31 in sessions (passes 23/26 are ALL→INCR again and pick up leftovers).
4. **Before any GDS from it:** run KLayout DRC + LVS (DRT cannot see fixed-vs-fixed PDN overlaps).

## Failure modes and the response
| Symptom | Response |
|---|---|
| GRT-0009 N ≪ S | The N-1-pin trick failed. Fallback: full `global_route -allow_congestion` (non-incremental, all guides consistent with the new placement; slower), or explicit guides. |
| Pass 17 explodes, mostly TopMetal1/TopVia1 | Guides still cross the macro (check the guides-inside gate); raise TM1_ADJ to 0.5. |
| Unrouted nets after 19 | Run pass 23 (INCR), or eco_plain on the listed nets. |
| check_placement fails | MAXDISP="250 80"; cells pushed into the flop cluster at x 3085-3114 (the rows above y 2995 are unaffected). |
| PG fails / audit not clean | `PDNFIX_STANDALONE=1 IN_ODB=eco.odb OUT_ODB=... MOVES=eco_moves.txt` then `pdn_fix_moved_macros.tcl`; after DRT, `repair_pdn_vias -all` (exists in dcf36133) for vias with DRC. |
| GRT-0113 | Only with REGION_ADJ on zero-capacity tiles; leave REGION_ADJ empty in loop 1. |
| New pin-access DRCs on slice27 | dx must stay a multiple of 0.48. |

## API status (dcf36133; verified against source/tests unless marked)
**Verified:**
- `odb::dbWireDecoder` begin/next/getLayer/getPoint → {x y}/getPoint_ext/getVia/getTechVia and the
  `$odb::dbWireDecoder_*` opcodes (test_wire_codec.tcl);
- `dbSBox_create` (layer box / via point + shape-type string), `dbSBox_destroy` (create_sboxes.tcl, smash_vias.tcl);
- `getViaXY` → {x y} (Point out-typemap);
- `dbBlockage_create block x1 y1 x2 y2`; `dbGuide_destroy`, `getGuides`;
- `global_route -end_incremental -allow_congestion -verbose`; `check_power_grid -net -error_file -dont_require_terminals`;
- `repair_pdn_vias -all|-net`; `pdngen -ripup` (rips up the whole grid, so not used).

**Not available in Tcl:** `dbWireShapeItr` / `dbShape` (not %included in odb.i); `dbWire::getBBox` (std::optional);
`dbTransform::apply(Rect&)` (swig maps `Rect & r` to an output-only argument). The pin boxes are transformed by hand
(R0/MX/MY/R180).

**Uncertain:**
- `dbWireDecoder getRect` (RECT patches are skipped);
- recreated rail pieces get Direction UNDEFINED (DEF writes a rect; check write_def/streaming once);
- whether `set_global_routing_layer_adjustment TopMetal1` after a range call overrides (the scripts avoid the overlap).

**Not tested on a real db:** the scripts were only exercised with a mock decoder. Run step 1 first; it is read-only.
