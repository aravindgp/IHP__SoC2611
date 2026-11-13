# SoC2611 candidate v.2.3.1, for checking (13 November 2026)

**Not a release.** This branch exists so that the checks can run on a second machine straight from GitHub. The
release branch follows when every check has finished. Do not submit from this branch.

`gds/SoC2611.gds.gz` is the complete filled GDS in one file: seal ring, row filler cells, PDK fill and a thinned
top-up fill. Its hash is in `gds/SoC2611.gds.gz.sha256`.

v.2.3.1 is a reissue of v.2.3.0 with one change in the layout: the top cell carries the die outline also as one
rectangle on prBoundary.drawing (189/0), 6600 um by 6600 um. v.2.3.0 has the outline on prBoundary.boundary (189/4)
and on EdgeSeal.boundary (39/4) only; IHP's density deck takes the chip area from prBoundary (189/0) first, and the
foundry tape-in check of an earlier release warned that the layout dimension was too small. The file is built from
the same routed database as v.2.3.0 with the same flow; no mask layer and no net is touched. Speed on the routed
wires, system clock: 54.2 MHz fast, 44.3 MHz typical, 28.7 MHz slow. Nets above the antenna ratio limit: 592, as in
v.2.3.0.

## State on the build machine when this branch was made

| Check | Result |
|---|---|
| Routing | 0 violations, 0 signal nets without a wire, power grid check passes |
| Density, own calculation, on this file | 0 violations |
| IHP minimum rule set on this GDS | not run yet when the branch was pushed |

## Run the check on another machine

```
git clone --depth 1 -b candidate-v.2.3.1 https://github.com/aravindgp/IHP__SoC2611
cd IHP__SoC2611/candidate/v.2.3.1
bash run_drc_check.sh 5 8          # all 27 tables and the density deck, 5 tables at a time, 8 threads per table
```

The script fetches the rule deck from the public IHP-Open-PDK repository at the commit the design was built with,
unpacks the GDS and runs the IHP minimum rule set in deep mode. Needs: git, Python 3, KLayout 0.30.x with
`pip install klayout docopt`. Memory: about 14 GB per table; the GatPoly filler table takes about 20 GB at 8
threads and about 100 GB at 16 threads, so keep it at 8 when tables run side by side. The run of v.2.3.0 with
these options took 4 h 20 min and peaked at about 98 GB.

To share the work with the build machine, only the long tables can be run here:
`TABLES="sealring gatpolyfiller" DENSITY=1 bash run_drc_check.sh 2 8`

## What to send back

`work/drc_out/progress.log` and every `*.lyrdb` and `*.log` file under `work/drc_out/`, committed under
`checks/v.2.3.1/` on a new branch `checks-v.2.3.1`. They are the evidence the release carries for each table.
