# SoC2611 architecture

Diagrams of SoC2611, release v.3.0.2, each with a short description. They are drawn from the RTL, the released
netlist and the GDS; each page lists its sources at the end. The figures are SVG files in `figures/`.

| Page | Figure | What it covers |
|---|---|---|
| [01_system_overview.md](01_system_overview.md) | block diagram | blocks of the chip top, buses, pad groups, parts on the board |
| [02_memory_map.md](02_memory_map.md) | memory map | address map seen by the CPU, boot, trap vector rule, APB registers, UART and timer scaling |
| [03_clocks_and_resets.md](03_clocks_and_resets.md) | clock tree, reset distribution | clock generation, frequencies, clock-domain crossings, reset tree and local resets |
| [04_boot_and_dataflow.md](04_boot_and_dataflow.md) | boot sequence, data flow | boot ROM copy, strap, UART loader, JTAG path; camera to HyperRAM, accelerator, UART |
| [05_accelerator.md](05_accelerator.md) | ztachip block diagram | configuration, interfaces, data path, PCORE array, inside a PCORE, the 205 accelerator macros |
| [06_physical.md](06_physical.md) | floorplan, pin-out, core supply | die to scale from the GDS with all 298 macros by owner block, QFN64 pin-out, supply entry and voltage drop |
| [07_schematics.md](07_schematics.md) | eight cell-level schematics | clock generator and clock gates, reset synchroniser and tree, pad cells, RWDS delay, one-port SRAM at double rate, clock-domain crossings, buffer tree repair, antenna diode |
