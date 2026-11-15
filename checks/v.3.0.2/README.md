# Checks of candidate v.3.0.2 on the second machine

**COMPLETE. All five checks clean.**

Input: branch `candidate-v.3.0.2` (commit 54f06ed), `candidate/v.3.0.2/gds/SoC2611.gds.gz`,
sha256 `f213c9a0f2c3cce79976759edeaa55d4ed4c0f97db3af06b9f0d0ae46bd8ca09` (verified before the run).
`run_drc_check.sh` identical to the one of v.3.0.0. Host 8e54483c835d, KLayout 0.30.5,
IHP-Open-PDK dcb03b1e2d24250bccbb2e8783d55d2b4f734f14, deep mode. All five ran side by side,
started 2026-11-15 05:47 UTC; last one ended 10:02 UTC. Nothing killed by the system; no exceptions.

| Check | Command / file | Completed in | Result |
|---|---|---|---|
| GatPoly filler table | `TABLES="gatpolyfiller sealring" DENSITY=1 bash run_drc_check.sh 3 8` | 8,434 s | 0 markers |
| Seal ring table | same run | 12,438 s | 0 markers |
| Density deck | same run | 9,774 s | 0 markers |
| PDK antenna table | `run_drc.py --run_mode=deep --antenna_only --density_thr=16` (`antenna/`) | 15,276 s | 23 categories, 0 markers |
| NWell geometry, no connectivity | `nwell/nwell_noconn.drc` (same script as checks/v.3.0.0) | 21,926 s | NW.a, NW.b, NW.c, NW.d, NW.e, straddle: 0 |

- `drc_out/tables/SoC2611_SoC2611_full.lyrdb`: GFil.d, Seal.l, Seal.n, 0 markers. The 25 other rule tables run on the build machine.
- Density: Activ 38.82 %, GatPoly 20.92 %, Metal1 38.51 %, Metal2 37.99 %, Metal3 38.50 %, Metal4 39.47 %,
  TopMetal1 34.22 %, LBE 0 %; all inside the limits.
- Antenna: Ant.a, Ant.c, Ant.b/Ant.e Metal1–TopMetal1, Ant.d/Ant.f Via1–TopVia1, Ant.g, Ant.h, Ant.i; design read as 6600.0 um * 6600.0 um.
- NWell: the two NW.b gaps of v.3.0.0 (SRAM corners at x 1630.8 and 3120.7 um, y 2995 um) are gone; no new NW.a.
  NW.b1 review list (space < 1.80 um, net-blind, a violation only between different nets): 9 entries.
  5 at place 1 (new gap 0.629 um, both wells on VDD per the candidate README, so NW.b1 does not apply), 4 inside library
  cells (RSC_IHPSG13_DFNQX2, RSC_IHPSG13_DFNQMX2IX1, RM_IHPSG13_1P_COLCTRL2, sg13cmos5l_lgcp_1), as on v.3.0.0.
  Place 2 is no longer in the list (gap 1.92 um).
- candidate-v.3.0.1 (withdrawn) was started here and stopped after about 1 h; no result of it is used.
