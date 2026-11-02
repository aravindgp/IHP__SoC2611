# RVSoC2794 — DGrid-SoC1

> **Status: PRELIMINARY — not for fabrication.** Detailed routing has not converged and hold timing on
> CPU↔SRAM paths is open; DRC/LVS are not clean yet. A final release will replace this one.

RISC-V SoC with an AI accelerator (DeepGrid Semi), IHP SG13CMOS5L, QFN64, die 6.6 × 6.6 mm.
Category Digital / RiscV based digital SoC (RVSoC). Top cell `RVSoC2794` in every view. License: Apache-2.0.

- `doc/` — Specification, Datasheet (pinout), TRL assessment, `info.json`
- `release/v.1.0.0/` — GDS (`gds/RVSoC2794.gds.gz`), netlists (`netlist/RVSoC2794.cdl.gz` for LVS, `RVSoC2794.v.gz`), release note
- `RVSoC2794-main/` — flow scripts, constraints, verification reports
- `dependencies/` — none (SRAM macros and IO cells are IHP library cells from the PDK)
