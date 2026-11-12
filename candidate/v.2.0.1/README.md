# SoC2611 candidate v.2.0.1, for checking (12 November 2026)

**Not a release.** This branch exists so that the checks can run on a second machine straight from GitHub. The
release branch follows when every check has finished. Do not submit from this branch.

`gds/SoC2611.gds.gz` is the complete filled GDS in one file: seal ring, row filler cells, PDK fill and a thinned
top-up fill. Its hash is in `gds/SoC2611.gds.gz.sha256`.

## State on the build machine when this branch was made

| Check | Result |
|---|---|
| Density, own calculation | 0 violations |
| Density, IHP density deck | passed, no violations |
| IHP minimum rule set | 25 of 26 rule tables finished with 0 violations; the seal ring table and the GatPoly filler table are running |
| NWell width and spacing, measured without connectivity | 0 places outside the SRAM macros |

## Run the check on another machine

```
git clone --depth 1 -b candidate-v.2.0.1 https://github.com/aravindgp/IHP__SoC2611
cd IHP__SoC2611/candidate/v.2.0.1
TABLES=gatpolyfiller DENSITY=0 bash run_drc_check.sh 1 8     # only the GatPoly filler table, 8 threads
bash run_drc_check.sh                                        # all 27 tables and the density deck
```

The script fetches the rule deck from the public IHP-Open-PDK repository at the commit the design was built with,
unpacks the GDS and runs the IHP minimum rule set in deep mode. Needs: git, Python 3, KLayout 0.30.x with
`pip install klayout docopt`, and 64 GB of memory for three tables at a time; the GatPoly filler table alone takes up
to 35 GB at 4 threads and about 3 hours.

The result is in `work/drc_out/progress.log`: one line per finished table and the verdict.
