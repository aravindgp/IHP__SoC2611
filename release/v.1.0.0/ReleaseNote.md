# SoC2611 v.1.0.0 — release note

> **Status: PRELIMINARY — not for fabrication.** Detailed routing has not converged and hold timing on
> CPU↔SRAM paths is open; DRC/LVS are not clean yet. A final release will replace this one.

- GDS: `gds/SoC2611.gds.gz` (top cell `SoC2611`), seal ring + density fill included, saved with the KLayout options of
  Open-Silicon-MPW (GDS2, dbu 0.001, no PCell/library context, zero-length paths eliminated).
- Netlists: `netlist/SoC2611.cdl.gz` (LVS; IHP SRAM and IO cells as library cells), `netlist/SoC2611.v.gz`.
- Documentation: `doc/` (Specification, Datasheet with the QFN64 pinout).
- Known open items: detailed routing not converged (metal spacing/shorts on Metal2-4/TopMetal1), core routing into
  the pad-ring margin, 102 pad nets unrouted, hold timing on CPU↔SRAM paths, LVS not run.
