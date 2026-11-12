# SoC2611 candidate v.2.1.0, for checking (12 November 2026)

**Not a release.** This branch exists so that the checks can run on a second machine straight from GitHub. The
release branch follows when every check has finished. Do not submit from this branch.

`gds/SoC2611.gds.gz` is the complete filled GDS in one file: seal ring, row filler cells, PDK fill and a thinned
top-up fill. Its hash is in `gds/SoC2611.gds.gz.sha256`.

Against v.2.0.1 this candidate carries the antenna repair (7,213 diode cells, 1,315 buffers at SRAM and pad pins),
a hold repair of 9 delay cells, and the row fillers next to one SRAM macro moved one site away (rule NW.f).

## State on the build machine when this branch was made

| Check | Result |
|---|---|
| Routing | 0 violations, 0 signal nets without a wire, power grid check passes |
| Density, own calculation | 0 violations |
| IHP minimum rule set on the layout without fill | 23 of 23 rule tables finished with 0 violations |
| IHP minimum rule set on this GDS | started on the build machine; nothing finished yet |
| Net trace of the GDS against the routed database | 343,085 signal nets, 0 open pins, 0 shorted pins |

## Run the check on another machine

```
git clone --depth 1 -b candidate-v.2.1.0 https://github.com/aravindgp/IHP__SoC2611
cd IHP__SoC2611/candidate/v.2.1.0
TABLES=gatpolyfiller DENSITY=0 bash run_drc_check.sh 1 16    # only the GatPoly filler table, 16 threads
bash run_drc_check.sh                                        # all 27 tables and the density deck
```

The script fetches the rule deck from the public IHP-Open-PDK repository at the commit the design was built with,
unpacks the GDS and runs the IHP minimum rule set in deep mode. Needs: git, Python 3, KLayout 0.30.x with
`pip install klayout docopt`, and 64 GB of memory for three tables at a time; the GatPoly filler table alone takes
about 20 GB at 8 threads and 1 hour 46 minutes (measured on the second machine for v.2.0.1).

The result is in `work/drc_out/progress.log`: one line per finished table and the verdict.
