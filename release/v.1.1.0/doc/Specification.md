# SoC2611 (SoC2611) — Specification

> **Status: PRELIMINARY — not for fabrication.** Detailed routing has not converged and hold timing on
> CPU↔SRAM paths is open; DRC/LVS are not clean yet. A final release will replace this one.

## Function
- VexRiscv RISC-V CPU (RV32IM, JTAG debug, I/D caches), boot ROM copy to a tightly-coupled memory, UART loader.
- ztachip AI accelerator: 4 PCOREs, data path, scratchpad SRAM, AXI-lite control.
- AXI interconnect (lean AXI split/merge), HyperBus memory interface, camera input + video stream writer,
  UART, timer, GPIO, APB bridge. Single main clock with integrated clock gating (2 ICG cells).

## Technology and physical data
| Item | Value |
|---|---|
| Process | IHP SG13CMOS5L (CMOS only, Metal1-4 + TopMetal1), 1.2 V core, 3.3 V IO |
| Die / seal ring | 6600 × 6600 µm, seal ring at the die edge |
| Core | 5920 × 5920 µm (340 µm pad-ring margin) |
| Package | QFN64 (64 pads: 48 signal, 16 supply) |
| Standard cells | ~290k after synthesis (~6.2 mm²), ~335k after P&R |
| SRAM | 298 RM_IHPSG13 macros, 214 KiB, ~12.9 mm² |
| IO | sg13cmos5l_io (IOPadIn / Out4mA / InOut4mA / supply pads), 70 × 70 µm bondpads |
