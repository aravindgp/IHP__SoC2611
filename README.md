# SoC2611 — DGrid-SoC1 (DeepGrid Semi)

A RISC-V System-on-Chip with the ztachip AI accelerator, implemented on the IHP SG13CMOS5L process (5 metal layers,
1.2 V core, 3.3 V IO) in a 6.6 × 6.6 mm die for a QFN64 package. Submitted to the IHP Open-Silicon MPW
(Nov-2026, Mixed-Signal / SystemOnChip, issue
[IHP-GmbH/Open-Silicon-MPW#79](https://github.com/IHP-GmbH/Open-Silicon-MPW/issues/79)); target slot 20 November 2026.

This repository holds the documentation, the design sources and flow, the testbenches and simulation results, and
the tagged releases of the `SoC2611` top cell.

## Overview

| Item | Value |
|---|---|
| CPU | VexRiscv RV32IM, 8 KiB I-cache + 8 KiB D-cache, JTAG debug TAP (IDCODE `0x10001FFF`) |
| Accelerator | ztachip, 8 PCOREs (2 cells × 4), 16 threads each, FP32 unit |
| Memory | 298 RM_IHPSG13 SRAM macros (214 KiB) on chip; external HyperRAM (8 MB, HyperBus) as main memory |
| Peripherals | 8-bit DVP camera input with video DMA, UART, SPI master, GPIO 4+4, timer, APB bridge |
| Clocking | one 100 MHz input, core 50 MHz, camera 25 MHz, HyperBus 25 MHz; no PLL; ICG clock gating |
| Process / die | IHP SG13CMOS5L, 6600 × 6600 µm with seal ring, core 5920 × 5920 µm |
| Package / pads | QFN64: 48 signal pads, 16 supply pads (VDD/VSS 1.2 V, IOVDD/IOVSS 3.3 V) |
| Top cell | `SoC2611` (GDS, CDL, Verilog, RTL) |
| Readiness | TRL 2 declared (`doc/TRL-Mixed-Signal-IP.md`) |
| License | Apache-2.0 |

## Status (9 November 2026, evening)

- **Latest release: `release/v.1.3.1`**, preliminary, not for fabrication. First routed state with **no supply short**
  (0 shorts inside the SRAM macros, 0 nets touching VDD or VSS); 1,624 detailed-route violations remain, 1,532 of
  them in one 50 µm square where two SRAM slices overlap by 2.8 µm. A local floorplan ECO that moves the slice and
  re-routes the affected nets has removed that knot on trial databases (window 1,532 → 0 markers, both power rails
  pass the grid check); its clean-up runs are in progress. Day-by-day record: `STATUS_2026-11-07.md`,
  `STATUS_2026-11-08.md`, `STATUS_2026-11-09.md`; engineering log: `SoC2611-main/Flow/ROUTING_CLOSURE_LOG.md`.
- **Functional verification (RTL)**: firmware suite 6/6 PASS on the chip top with HyperRAM and IHP macro models,
  boot-ROM UART loader PASS, HyperBus controller 6/6, SRAM wrapper equivalence 37 pairs PASS
  (`SoC2611-main/verification/sim/`, testbenches in `SoC2611-main/testbenches/`).
- **Open before the final release**: routing closure to zero shorts, antenna repair, multi-corner timing (hold on
  CPU ↔ SRAM paths is open), IHP minimum DRC deck on the final full-fill GDS (density deck already passes), chip LVS,
  gate-level simulation.
- **Plan**: checked GDS (zero shorts, antenna, DRC, LVS, timing report, hashes) by 12 November for the 20 November
  slot; fallback the March 2027 run.

## Repository structure

```text
.
├── README.md, LICENSE
├── STATUS_2026-11-07.md / -08.md / -09.md     daily status, decisions and numbers
├── doc/
│   ├── info.json                 metadata (name, top cell, PDK commit, libraries, tools, TRL, release pointers)
│   ├── Specification.md          function, technology and physical data
│   ├── Datasheet.md              QFN64 pinout, supplies, package
│   ├── Interfaces.md             pin groups with protocols, clocks and timing constraints, reset/boot, BIST, package
│   ├── RegisterMap.md            address map, APB peripheral registers, accelerator host registers, boot sequence
│   └── TRL-Mixed-Signal-IP.md    readiness assessment, every tick with its evidence file
├── dependencies/README.md        PDK commit, cell/IO/SRAM libraries, CPU generator and tool versions
├── release/
│   ├── v.1.3.1/                  latest (see table below); gds/, netlist/, doc/, density_fullfill.txt, ReleaseNote.md
│   ├── v.1.3.0/, v.1.2.0/, v.1.1.0/, v.1.0.0/   earlier preliminary states, each with its ReleaseNote.md and hashes
├── SoC2611-main/
│   ├── README.md                 source-to-release mapping (library names, PDK commit, SRAM macros)
│   ├── rtl/                      SoC2611.v, single-file RTL export of the VHDL design
│   ├── docs/                     architecture (HardwareDesign.md), ASIC port (ASIC_PORT.md), programmer guides,
│   │                             JTAG core, platform and pad-list notes
│   ├── testbenches/              VHDL testbenches, cocotb drivers, run scripts, README with commands and expected output
│   ├── verification/
│   │   ├── sim/                  RTL simulation logs and JUnit result (see its README)
│   │   ├── drc/                  per-table DRC results on an intermediate snapshot, antenna summary
│   │   └── lvs/                  connectivity check log (chip LVS runs on the final database)
│   ├── constraints/              design.sdc, chip_extra.sdc, bond table, pad ring and port map
│   ├── synthesis/                Yosys script, statistics, SRAM macro inventory
│   ├── Flow/                     floorplan, routing-closure log, and scripts/ (dgse flow, signoff: ECO, guides,
│   │                             release chain, DRC/LVS/density, waivers, explainer-video generators)
├── measurements/                 empty until silicon
└── .github/workflows/            IHP workflow-sync check
```

## Releases

| Version | Date | Routing state | Contents | Status |
|---|---|---|---|---|
| v.1.3.1 | 9 Nov | 0 supply shorts, 1,624 violations (one congestion knot) | GDS (whole file + full-fill variant), CDL, Verilog, density report, docs, SHA-256 | preliminary, latest |
| v.1.3.0 | 9 Nov | first state with 0 supply shorts, 1,760 violations | same chain | preliminary |
| v.1.2.0 | 9 Nov | 42 shorts inside macros, 1,433 violations | same chain | preliminary |
| v.1.1.0 | 8 Nov | 1,005 violations | GDS, netlists, density | preliminary |
| v.1.0.0 | 2 Nov | first submission snapshot | GDS, netlists, docs | audited in #79 |

Every release is built by the same scripted chain (chip_finish → DEF-to-GDS stream → seal ring and label → PDK fill +
top-up fill → density check → netlists → hashes), so the final GDS is a re-run of the chain on the closed routing
database, not a rebuild. `doc/info.json` points at the latest release.

## Where to start

1. `doc/Specification.md`, then `doc/Interfaces.md` and `doc/RegisterMap.md` for what the chip is and how to talk to it.
2. `doc/TRL-Mixed-Signal-IP.md` for what has been verified, with the evidence files.
3. `STATUS_2026-11-09.md` for the current engineering state and the plan to the final GDS.
4. `release/v.1.3.1/ReleaseNote.md` for the exact state and hashes of the latest GDS.
5. `SoC2611-main/testbenches/README.md` to reproduce the simulations.

## Dependencies and tools

IHP-Open-PDK commit `dcb03b1e2d24250bccbb2e8783d55d2b4f734f14` (unmodified), `sg13cmos5l_stdcell`, `sg13cmos5l_io`,
`RM_IHPSG13` SRAM macros; GHDL, Yosys 0.70, OpenROAD dcf36133, KLayout 0.30.5, cocotb, SpinalHDL 1.9.3 /
VexRiscv `5ef1bc7`. Full list with versions in `dependencies/README.md`.

## Licensing

Apache License 2.0, see `LICENSE`. The ztachip sources keep their original Apache-2.0 notices.

## Contact

DeepGrid Semi, Aravind G. P. (aravind@deepgridsemi.com). Questions and reviews on the submission go through
Open-Silicon-MPW issue #79.
