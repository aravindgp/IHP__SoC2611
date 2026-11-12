# SoC2611 candidate v.2.3.0, for checking (13 November 2026)

**Not a release.** This branch exists so that the checks can run on a second machine straight from GitHub. The
release branch follows when every check has finished. Do not submit from this branch.

`gds/SoC2611.gds.gz` is the complete filled GDS in one file: seal ring, row filler cells, PDK fill and a thinned
top-up fill. Its hash is in `gds/SoC2611.gds.gz.sha256`.

Against v.2.2.0 this candidate carries two more speed steps: 244 strong buffers at small gates that drive long
nets, the routing closed again, and a hold repair of 4 delay cells. Speed on the routed wires, system clock:
54.2 MHz fast, 44.3 MHz typical, 28.7 MHz slow (v.2.2.0: 45.7 / 30.0 / 18.9 MHz). The 100 MHz input clock of the
constraints is met at the fast corner. The antenna state is that of the first repair pass.

## State on the build machine when this branch was made

| Check | Result |
|---|---|
| Routing | 0 violations, 0 signal nets without a wire, power grid check passes |
| Density, own calculation, on this file | 0 violations |
| IHP minimum rule set on this GDS | not run yet when the branch was pushed |

## Run the check on another machine

```
git clone --depth 1 -b candidate-v.2.3.0 https://github.com/aravindgp/IHP__SoC2611
cd IHP__SoC2611/candidate/v.2.3.0
bash run_drc_check.sh 5 8          # all 27 tables and the density deck, 5 tables at a time, 8 threads per table
```

The script fetches the rule deck from the public IHP-Open-PDK repository at the commit the design was built with,
unpacks the GDS and runs the IHP minimum rule set in deep mode. Needs: git, Python 3, KLayout 0.30.x with
`pip install klayout docopt`. Memory: about 14 GB per table; the GatPoly filler table takes about 20 GB at 8
threads and about 100 GB at 16 threads, so keep it at 8 when tables run side by side.

Times measured so far: seal ring table 2 h 53 min, GatPoly filler table 1 h 46 min at 8 threads, density deck
about 2 h, the other tables 7 to 60 minutes each.

## What to send back

`work/drc_out/progress.log` and every `*.lyrdb` and `*.log` file under `work/drc_out/`. If this machine can push to
the repository: commit them under `checks/v.2.3.0/` on a new branch `checks-v.2.3.0`. They are the evidence the
release carries for each table.
