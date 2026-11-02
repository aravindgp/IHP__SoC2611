# RVSoC2794 — DGrid-SoC1

A preliminary RISC-V System-on-Chip (SoC) with an AI accelerator targeting the IHP SG13CMOS5L process and packaged in a QFN64 form factor.

This repository contains the design assets, documentation, signoff flow, and release materials for the `RVSoC2794` top cell.

## Overview

- SoC type: RISC-V based digital SoC
- Platform: IHP SG13CMOS5L
- Package: QFN64
- Die size: 6.6 mm × 6.6 mm
- Core concept: RISC-V CPU + AI accelerator
- Top cell: `RVSoC2794`
- License: Apache-2.0

## Project status

This project is currently in a preliminary stage and is not intended for fabrication.

Important design notes:

- Detailed routing has not converged yet.
- Hold timing on CPU ↔ SRAM paths remains open.
- DRC/LVS are not yet clean.
- A final release will supersede this repository snapshot.

## Repository structure

```text
.
├── .github/
├── LICENSE
├── README.md
├── doc/
│   ├── Datasheet.md
│   ├── Specification.md
│   ├── TRL-Digital-Hard-IP.md
│   └── info.json
├── release/
│   └── v.1.0.0/
│       ├── gds/
│       ├── netlist/
│       └── release-notes/
├── RVSoC2794-main/
│   ├── Flow/
│   ├── constraints/
│   ├── rtl/
│   ├── synthesis/
│   ├── verification/
│   └── README.md
└── ...
```

## Key directories

### `doc/`
This directory contains the project documentation and metadata:

- `Specification.md` — functional and architectural specification
- `Datasheet.md` — pinout, electrical, and packaging information
- `TRL-Digital-Hard-IP.md` — technology readiness assessment
- `info.json` — repository metadata and design information

### `release/v.1.0.0/`
Contains the public release artifacts for the current version, including:

- GDS output for layout export
- Netlists used for verification and LVS
- Release documentation and notes

### `RVSoC2794-main/`
This is the main design workspace and contains the flow and implementation assets:

- `Flow/` — design and signoff flow scripts
- `constraints/` — timing and physical constraints
- `rtl/` — hardware RTL sources
- `synthesis/` — synthesis-related files and reports
- `verification/` — verification inputs, outputs, and results

## Design goals

The RVSoC2794 design is intended to combine:

- a RISC-V processor subsystem,
- a DeepGrid AI accelerator,
- a silicon implementation on the IHP SG13CMOS5L process,
- and a hardware flow suitable for a 64-pin QFN package target.

## Documentation

For a technical understanding of the design, start with:

1. `doc/Specification.md`
2. `doc/Datasheet.md`
3. `doc/TRL-Digital-Hard-IP.md`
4. `RVSoC2794-main/README.md`

## Licensing

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.

## Notes

This repository is a research and development SoC implementation. It is useful for design review, documentation, and flow validation, but it should be treated as a preliminary design snapshot until the final release is published.
