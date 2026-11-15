# SoC2611 candidate v.3.0.1, for checking (15 November 2026)

**Not a release.** This branch exists so that the checks can run on a second machine straight from GitHub. The
release branch follows when every check has finished. Do not submit from this branch.

`gds/SoC2611.gds.gz` is the complete filled GDS in one file: seal ring, row filler cells, PDK fill and a thinned
top-up fill. Its hash is in `gds/SoC2611.gds.gz.sha256`.

## What changed against v.3.0.0: two NWell rectangles, nothing else

The extra NWell check on v.3.0.0 (branch checks-v.3.0.0, folder checks/v.3.0.0/nwell) found two NW.b gaps of
0.485 um (rule 0.62 um), at the top right corners of two RM_IHPSG13_1P_64x16_c2 macros: the macro NWell ends at
y 2995.025 um, the NWell of the standard-cell row beside it starts at y 2995.510 um. Both wells are on VDD, so the
rule is NW.b, whose text says such regions are merged. v.3.0.1 draws that merge: one NWell rectangle in the top cell
at each corner, overlapping both wells.

| Patch | x (um) | y (um) | Size | Nearest N+ diffusion outside NWell |
|---|---|---|---|---|
| 1 | 1630.400 to 1631.080 | 2995.020 to 2995.520 | 0.68 x 0.50 um | 0.555 um (NW.d asks 0.31 um) |
| 2 | 3120.240 to 3120.920 | 2995.020 to 2995.520 | 0.68 x 0.50 um | 0.332 um (NW.d asks 0.31 um) |

No Activ, GatPoly, fill or metal is under either patch. Every other shape of the file is the same as in v.3.0.0:
the files were compared cell by cell, and the only difference is the two rectangles on NWell 31/0 in the top cell.
Routing, netlist, timing, antenna diodes, simulation and the supply bars are therefore those of v.3.0.0.

## State on the build machine when this branch was made

| Check | Result |
|---|---|
| NWell gaps below 0.62 um, NWell not SRAM marker, whole chip | 0 (2 in v.3.0.0) |
| Density, own calculation, on this file | 0 violations |
| Subset proof: this file = the checked full-fill file minus thinned top-up fill | passed |
| IHP minimum rule set, LVS, NWell rules of the maximal deck | running on the build machine |

## Run the check on another machine

```
git clone --depth 1 -b candidate-v.3.0.1 https://github.com/aravindgp/IHP__SoC2611
cd IHP__SoC2611/candidate/v.3.0.1
bash run_drc_check.sh 5 8          # all 27 tables and the density deck, 5 tables at a time, 8 threads per table
```

The script fetches the rule deck from the public IHP-Open-PDK repository at the commit the design was built with,
unpacks the GDS and runs the IHP minimum rule set in deep mode. Needs: git, Python 3, KLayout 0.30.x with
`pip install klayout docopt`. Memory: about 14 GB per table; the GatPoly filler table takes about 20 GB at 8
threads and about 100 GB at 16 threads, so keep it at 8 when tables run side by side.

To share the work with the build machine, only the long tables can be run here:
`TABLES="sealring gatpolyfiller" DENSITY=1 bash run_drc_check.sh 2 8`

Most useful beside them: the NWell geometry check without connectivity that found the two gaps
(`checks/v.3.0.0/nwell/nwell_noconn.drc` on branch checks-v.3.0.0), and the PDK antenna table, on this GDS.

## What to send back

`work/drc_out/progress.log` and every `*.lyrdb` and `*.log` file under `work/drc_out/`, plus the NWell and antenna
results if they were run, committed under `checks/v.3.0.1/` on a new branch `checks-v.3.0.1`.
