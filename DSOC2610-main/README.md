# DSOC2610-main — sources, flow and source-to-release mapping

DSOC2610 is the IHP release name of the DeepGrid SoC **DGrid-SoC1** (internal top-level name `dgrid_soc1_chip_top`).
This directory holds what is needed to understand and reproduce the release in `../release/v.1.0.0/`.

## Contents
| Path | What |
|---|---|
| `rtl/DSOC2610.v` | Complete RTL as one Verilog file, exported from the VHDL/Verilog sources of DGrid-SoC1 (GHDL `--synth` export of the VHDL, VexRiscv Verilog, ztachip). Top module renamed `dgrid_soc1_chip_top` → `DSOC2610`. |
| `synthesis/` | Yosys script (`synth.ys`), statistics, SRAM inventory (298 RM_IHPSG13 macros) |
| `constraints/` | SDC (`design.sdc`, `chip_extra.sdc`), QFN64 pad ring + port map (`padring_qfn64.json`, `portmap_qfn64.json`), bond table |
| `Flow/scripts/signoff/` | Chip integration (pads, pad↔core power straps), GDS stream, CDL, seal ring, tiled fill, DRC/LVS, release scripts |
| `Flow/scripts/dgse/` | PDN script and detailed-route step/resume runner used with the DGSE (OpenROAD) P&R flow |
| `verification/` | DRC table summaries, OpenROAD antenna summary, connectivity check of the current (preliminary) layout |

## Source-to-release mapping
1. **RTL → netlist**: `synthesis/synth.ys` (Yosys 0.70+277) maps to the **sg13g2** standard-cell and SRAM liberty
   files. SG13CMOS5L uses the **identical** standard-cell library (same 84 cells, same layouts) under the prefix
   `sg13cmos5l_`, and the same RM_IHPSG13 SRAM macros (Metal1-4 only). The P&R netlist is the Yosys netlist with the
   textual rename `sg13g2_` → `sg13cmos5l_` (no other change; checked byte-for-byte against the P&R input).
   The script still names the internal top `dgrid_soc1_chip_top`; the release renames it to `DSOC2610`.
2. **P&R**: DGSE flow (OpenROAD dcf36133) on IHP-Open-PDK `dcb03b1e2d24250bccbb2e8783d55d2b4f734f14`,
   `ihp-sg13cmos5l`, die 6600 × 6600 µm, core 340..6260 µm; PDN `Flow/scripts/dgse/pdn_c5l_sram_v2.tcl`.
3. **Chip integration**: `Flow/scripts/signoff/run_chip_integrate.sh` adds the 64 sg13cmos5l IO cells, bondpads and
   pad↔core-ring power straps to the routed core (ports moved from the die edge to the pads).
4. **GDS**: `stream_chip.sh` (DEF → GDS with the cmos5l layer map), `make_sealring.py` (seal ring + registration
   label), `fill_tiled.py --abstract-macros "RM_IHPSG13_.*"` (PDK fill recipes; SRAM macros as keep-out outlines).
5. **Release**: `ihp_release.py` renames the top cell to `DSOC2610` and writes the GDS with the Open-Silicon-MPW
   KLayout save options; `ihp_sealring_label.py` completes the seal-ring label; `ihp_repo_docs.py` writes the docs.

## Status (preliminary)
Routing is not yet DRC-clean, antenna repair and hold-timing closure are open, LVS has not been run. The
verification summaries here were taken on a reduced LVS view (IO/SRAM FEOL removed, all metal kept) of an
intermediate routing snapshot — not on the released GDS. The final release will carry DRC on the unmodified filled
GDS (IHP precheck + density), with input hashes.
