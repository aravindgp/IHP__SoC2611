# SoC2611 candidate v.3.0.2, for checking (15 November 2026)

**Not a release.** This branch exists so that the checks can run on a second machine straight from GitHub. The
release branch follows when every check has finished. Do not submit from this branch.

`gds/SoC2611.gds.gz` is the complete filled GDS in one file: seal ring, row filler cells, PDK fill and a thinned
top-up fill. Its hash is in `gds/SoC2611.gds.gz.sha256`.

**candidate-v.3.0.1 is withdrawn.** It joined the NWell regions with two rectangles whose joints were narrower than
0.62 um (11 NW.a markers in the NWell rules of IHP's maximal deck). Do not use it.

## What changed against v.3.0.0: two row filler cells removed, nothing else

The extra NWell check on v.3.0.0 (branch checks-v.3.0.0, folder checks/v.3.0.0/nwell) found two NW.b gaps of
0.485 um (rule 0.62 um), at the top right corners of two RM_IHPSG13_1P_64x16_c2 macros: the macro NWell ends at
y 2995.025 um, the NWell of the first cell of the row beside it starts at y 2995.510 um. In both places that first
cell is a row filler. v.3.0.2 leaves those two fillers out; the next cell of the row becomes its first cell.

| Place | Filler left out | NWell of the new first cell to the macro NWell corner |
|---|---|---|
| 1 | sg13cmos5l_fill_1, r0 at (1631.04, 2993.76) um | 0.629 um (tiehi cell; rule 0.62 um) |
| 2 | sg13cmos5l_fill_4, r0 at (3120.96, 2993.76) um | 1.92 um (flip-flop) |

Fillers have no devices and no nets. In the thinned file the NWell box that the filler edge fix of v.2.1.0 kept for
the filler at place 1 is gone with it. The full-fill file and the layout without fill were compared with those of
v.3.0.0 cell by cell: the only differences are the two filler instances. The 13 NWell rules of the maximal deck on
40 um windows around both places give exactly the same markers as on v.3.0.0 (all of them window-edge effects).

## State on the build machine when this branch was made

| Check | Result |
|---|---|
| NWell gaps below 0.62 um, NWell not SRAM marker, whole chip | 0 (2 in v.3.0.0) |
| Density, own calculation, on this file | 0 violations |
| Subset proof: this file = the checked full-fill file minus thinned top-up fill | passed |
| IHP minimum rule set, LVS, NWell rules of the maximal deck | running on the build machine |

## Run the check on another machine

```
git clone --depth 1 -b candidate-v.3.0.2 https://github.com/aravindgp/IHP__SoC2611
cd IHP__SoC2611/candidate/v.3.0.2
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
results if they were run, committed under `checks/v.3.0.2/` on a new branch `checks-v.3.0.2`.
