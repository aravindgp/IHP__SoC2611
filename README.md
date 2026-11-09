# SoC2611

A RISC-V System-on-Chip with an AI accelerator targeting the IHP SG13CMOS5L process and packaged in a QFN64 form factor.

This repository contains the design assets, documentation, testbenches, signoff flow, and release materials for the `SoC2611` top cell.

## Overview

- SoC type: RISC-V based digital SoC (VexRiscv RV32IM + ztachip AI accelerator, 8 PCOREs)
- Platform: IHP SG13CMOS5L (1.2 V core, 3.3 V IO)
- Package: QFN64 (48 signal pads, 16 supply pads)
- Die size: 6.6 mm × 6.6 mm
- On-chip memory: 298 RM_IHPSG13 SRAM macros (214 KiB); external HyperRAM as main memory
- Top cell: `SoC2611`
- Readiness: TRL 2 declared (`doc/TRL-Mixed-Signal-IP.md`)
- License: Apache-2.0

## Project status

This project is in a preliminary stage and is intended for fabrication (work in progress). Submission request:
IHP-GmbH/Open-Silicon-MPW issue #79.

Important design notes:

- Latest release: `release/v.1.3.1` (9 Nov 2026): 0 supply shorts, 1,624 detailed-route violations open in one congestion knot; a local floorplan ECO that removes the knot is in its clean-up runs (see `STATUS_2026-11-09.md`).
- Hold timing on CPU ↔ SRAM paths remains open.
- DRC/LVS are not yet clean (density deck passes; the IHP minimum deck and chip LVS run on the final database).
- Functional verification (RTL): firmware suite 6/6 PASS on the chip top, boot loader, HyperBus and SRAM-wrapper tests PASS (`SoC2611-main/verification/sim/`).
- A final release will supersede this repository snapshot.

## Repository structure

```text
.
├── .github/
├── LICENSE
├── README.md
├── STATUS_2026-11-07.md, STATUS_2026-11-08.md, STATUS_2026-11-09.md
├── doc/
│   ├── Datasheet.md
│   ├── Specification.md
│   ├── Interfaces.md
│   ├── RegisterMap.md
│   ├── TRL-Mixed-Signal-IP.md
│   └── info.json
├── dependencies/
│   └── README.md
├── measurements/
├── release/
│   ├── v.1.3.1/        (latest, preliminary; see its ReleaseNote.md)
│   │   ├── ReleaseNote.md
│   │   ├── doc/            (Datasheet.md, Specification.md)
│   │   ├── gds/            (SoC2611.gds.gz, full-fill variant)
│   │   ├── netlist/        (SoC2611.cdl.gz, SoC2611.v.gz)
│   │   └── density_fullfill.txt
│   ├── v.1.3.0/, v.1.2.0/, v.1.1.0/, v.1.0.0/   (earlier preliminary states)
├── SoC2611-main/
│   ├── Flow/
│   ├── constraints/
│   ├── docs/
│   ├── rtl/
│   ├── synthesis/
│   ├── testbenches/
│   ├── verification/
│   └── README.md
└── ...
```

## Key directories

### `doc/`
Project documentation and metadata:

- `Specification.md` — functional and architectural specification
- `Datasheet.md` — pinout, supplies and packaging information
- `Interfaces.md` — pin groups with protocols, clocks and timing constraints, reset and boot, BIST, package
- `RegisterMap.md` — address map, APB peripheral registers, accelerator host registers, boot sequence
- `TRL-Mixed-Signal-IP.md` — technology readiness assessment, each ticked item with its evidence file
- `info.json` — repository metadata and design information

### `dependencies/`
`README.md` lists the PDK commit, the standard-cell, IO and SRAM libraries, the CPU generator and the tool versions.

### `release/v.1.3.1/` (latest, preliminary)
Release of 9 November 2026: GDS of the first routed state with no supply short (1,624 detailed-route violations
open in one congestion knot), seal ring, PDK and top-up fill (density 0 violations), CDL and Verilog netlists,
SHA-256 hashes in its `ReleaseNote.md`. Not for fabrication; the IHP minimum DRC deck and LVS run on the final
database. `doc/info.json` points at this release.

### `release/v.1.3.0/`, `v.1.2.0/`, `v.1.1.0/`, `v.1.0.0/`
Earlier preliminary states, each with its release note, hashes, GDS and netlists.

### `SoC2611-main/`
The main design workspace:

- `Flow/` — floorplan, routing-closure log and the design and signoff flow scripts
- `constraints/` — timing and physical constraints, bond table, pad ring
- `docs/` — architecture, ASIC port, programmer guides, JTAG core, platform and pad-list notes
- `rtl/` — hardware RTL sources
- `synthesis/` — synthesis script, statistics and SRAM macro inventory
- `testbenches/` — VHDL testbenches, cocotb drivers, run scripts and how to run them
- `verification/` — simulation results (`sim/`), DRC tables and antenna summary (`drc/`), connectivity check (`lvs/`)

## Design goals

The SoC2611 design is intended to combine:

- a RISC-V processor subsystem,
- an AI accelerator,
- a silicon implementation on the IHP SG13CMOS5L process,
- and a hardware flow suitable for a 64-pin QFN package target.

## Documentation

For a technical understanding of the design, start with:

1. `doc/Specification.md`
2. `doc/Interfaces.md` and `doc/RegisterMap.md`
3. `doc/Datasheet.md`
4. `doc/TRL-Mixed-Signal-IP.md`
5. `SoC2611-main/README.md`

## Licensing

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.

## Notes

This repository is a research and development SoC implementation. It is useful for design review, documentation, and flow validation, but it should be treated as a preliminary design snapshot until the final release is published.
