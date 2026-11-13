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

The design is implemented and released for the submission checks of the IHP Open-Silicon-MPW run (submission
request: IHP-GmbH/Open-Silicon-MPW issue #79). State of 13 November 2026:

- **Latest release: `release/v.2.4.0`** (13 Nov 2026), the release `doc/info.json` names. Its
  `gds/SoC2611.gds.gz` is the one GDS of the release: fully filled, under 100 MB, and the file every check below
  ran on.
- Routing: 0 detailed-route violations, 0 signal nets without a wire; the power grid check passes on VDD and VSS.
- IHP minimum rule set (deep mode) on the GDS of the release: 26 of 26 rule tables and the GatPoly filler table
  completed, 0 violations. Density: 0 violations, by our own calculation and by IHP's density deck.
- LVS (KLayout, IHP deck): the netlists match, 354,671 instances of the chip top. SRAM macros and pad cells are
  black boxes with their pins.
- Connectivity: every signal net was traced in the GDS against the netlist, 0 open and 0 shorted pins.
- Timing, with the parasitics of the routed wires: hold is met at all three corners. System clock 54.7 MHz fast,
  45.5 MHz typical, 29.4 MHz slow; the double-rate input clock is twice that. The 100 MHz input clock of the
  constraints is met at the fast corner only, and the slow-corner figure is the one to rate the chip at.
- Since `v.2.3.0`: a fifth speed step and the registers of the clock generator clocked from the root of the clock
  tree, and two more antenna passes.
- Antenna: 78 nets are above the ratio limit of the router's check in `v.2.4.0`, and 6 nets are above the limit of
  the PDK antenna table through TopMetal1. The antenna rules are not part of the minimum rule set. See the table
  below.
- Die outline: `v.2.4.0` carries it on prBoundary.boundary (189/4) and EdgeSeal.boundary (39/4). The candidates
  from `v.2.5.0` on carry it also as one rectangle on prBoundary.drawing (189/0), 6600 um by 6600 um.
- In work, each a release only when all checks on its GDS have finished:
  - `v.2.5.0`: the chip of `v.2.4.0` with no net above the limit of the router's antenna check and the die outline
    also on 189/0. Candidate on branch `candidate-v.2.5.0`; its checks are running.
  - `v.3.0.0`: the chip of `v.2.5.0` with the 6 TopMetal1 nets of the PDK antenna table repaired and the longest
    wires of the fast corner laid straight. In preparation.
  - `v.2.3.1` and `v.2.4.1`: reissues of `v.2.3.0` and `v.2.4.0` with one change, the die outline also on 189/0.
    The candidate of `v.2.4.1` is in `candidate/v.2.4.1/`; it is not a release.
- Branches named `candidate-<version>` carry a candidate GDS for the checks on a second machine and
  `checks-<version>` the results; they are not releases.
- Functional verification (RTL): firmware suite 6/6 PASS on the chip top, boot loader, HyperBus and SRAM-wrapper
  tests PASS (`SoC2611-main/verification/sim/`).
- No silicon has been measured. The speeds are results of static timing analysis.
- What changed, the hashes and the known limits of each release are in its `ReleaseNote.md`.

## Antenna nets per release

Two antenna checks are run. The first is the router's check (OpenROAD `check_antennas`, ratio limits of the
technology LEF) on the routed database: it asks for the protection diode on the layer under check. The second is
the antenna table of the PDK (KLayout, `antenna.drc`, rules Ant.a to Ant.i) on the layout: it takes the protection
diode from the complete net and allows a cumulative metal-to-gate ratio of 20,000 with a diode. State of
13 November 2026.

| Release | Date | Router check: nets above the limit | Router check: gate pins | PDK antenna table: nets above a limit | Antenna repair in the file | System clock, fast / typical / slow |
|---|---|---|---|---|---|---|
| `v.1.0.0` | 2 Nov | not checked | | not run | none | |
| `v.1.1.0` | 8 Nov | about 6,000 | | not run | none | |
| `v.1.2.0`, `v.1.3.0`, `v.1.3.1` | 9 Nov | not counted on these files | | not run | none | |
| `v.2.0.0-rc1`, `v.2.0.0-rc2` | 10 Nov | 6,129 | | not run | none | |
| `v.2.0.1` | 12 Nov | 6,129 | 7,222 | not run | none | 15.0 / 12.7 / 10.0 MHz |
| `v.2.1.0` | 12 Nov | 590 | 668 | not run | first pass: 7,213 diodes and 1,315 buffers | 15.8 / 13.2 / 10.3 MHz |
| `v.2.2.0` | 12 Nov | 582 | 656 | not run | first pass | 45.7 / 30.0 / 18.9 MHz |
| `v.2.3.0` | 13 Nov | 592 | 671 | 6 | first pass | 54.2 / 44.3 / 28.7 MHz |
| **`v.2.4.0`**, latest release | 13 Nov | 78 | 101 | 6 | three passes: 865 more diodes, 98 buffers at SRAM pins | 54.7 / 45.5 / 29.4 MHz |
| `v.2.5.0`, candidate | 13 Nov | **0** | **0** | run not finished | four passes: 91 more diodes directly under the wires, long Metal2 runs of 7 nets moved to Metal4 | 54.7 / 45.5 / 29.4 MHz |

- `v.2.4.0` is the latest release: 78 nets are above the limit of the router's check, none above 4 times the limit.
- The 6 nets of the PDK antenna table are the same in `v.2.3.0` and `v.2.4.0`. Each is one small gate on 1.3 to
  1.9 mm of TopMetal1, which is 1.64 um wide: rule Ant.e through TopMetal1, ratio 20,029 to 29,054 against the
  limit of 20,000. Every other rule of the table is at 0. The result is in `release/v.2.4.0/checks/antenna_ihp_table.txt`.
- `v.2.5.0` has no net above the limit of the router's check. It is a candidate: its release folder follows when
  every check on its GDS has finished. The PDK antenna table is running on its layout; the 6 TopMetal1 nets are
  expected in it, because that candidate does not change them.
- `v.3.0.0`, in preparation, is the chip of `v.2.5.0` with a buffer in front of the receiving pin of those 6 nets,
  so that both checks are at 0. The PDK antenna table will run on its layout before it is released.
- The antenna rules are not part of the IHP minimum rule set of the precheck. A net above the limit is a risk for
  the gate oxide of one transistor during manufacturing, not a logic error.
- From `v.2.2.0` to `v.2.3.0` the count of the router's check rose by 10 because the wires of the nets with new
  drive buffers were laid again; the later passes repaired those nets as well.
- The releases `v.2.0.0` and `v.2.0.0-rc3`, which exist on their own branches only, are the chip of `v.2.0.1`
  (6,129 and 6,111 nets).

## Repository structure

```text
.
├── .github/
├── LICENSE
├── README.md
├── STATUS_2026-11-07.md, STATUS_2026-11-08.md, STATUS_2026-11-09.md, STATUS_2026-11-10.md   (records of those days)
├── candidate/
│   └── v.2.4.1/        (candidate GDS and DRC run script for checks on a second machine; not a release)
├── doc/
│   ├── Datasheet.md
│   ├── Specification.md
│   ├── Interfaces.md
│   ├── RegisterMap.md
│   ├── TRL-Mixed-Signal-IP.md
│   └── info.json
├── dependencies/
│   └── README.md
├── release/
│   ├── v.2.4.0/        (latest; the release doc/info.json names)
│   │   ├── ReleaseNote.md
│   │   ├── gds/            (SoC2611.gds.gz: the one GDS, fully filled)
│   │   ├── netlist/        (SoC2611.cdl.gz, SoC2611.v.gz)
│   │   ├── density.txt
│   │   └── checks/         (DRC verdicts and result databases, LVS, net trace, timing, both antenna checks, NWell rules)
│   ├── v.2.3.0/, v.2.2.0/, v.2.1.0/, v.2.0.1/               (earlier complete releases, same layout)
│   ├── v.2.0.0-rc2/, v.2.0.0-rc1/                           (release candidates of 10 November)
│   ├── v.1.3.1/, v.1.3.0/, v.1.2.0/, v.1.1.0/, v.1.0.0/     (preliminary states, not for fabrication)
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

### `release/v.2.4.0/` (latest)
Release of 13 November 2026, the one `doc/info.json` points at. One fully filled GDS (`gds/SoC2611.gds.gz`: seal
ring, PDK fill and a thinned top-up fill), CDL and Verilog netlists, the density of exactly this file, and under
`checks/` the verdicts and result databases of the IHP minimum rule set, the LVS summary, the net trace, the
timing on the routed wires, the antenna summary of the router, the result of the PDK antenna table, the NWell
rules and the proof that the packaged file is the checked file. SHA-256 hashes, what changed and the known limits
are in its `ReleaseNote.md`.

### `release/v.2.3.0/`, `v.2.2.0/`, `v.2.1.0/`, `v.2.0.1/`
Earlier complete releases with the same layout and the same checks: `v.2.3.0` (four speed steps, 54.2 / 44.3 /
28.7 MHz), `v.2.2.0` (two speed rounds, 45.7 / 30.0 / 18.9 MHz), `v.2.1.0` (the first antenna repair, 590 nets
left of 6,129, 15.8 / 13.2 / 10.3 MHz) and `v.2.0.1` (the first clean chip with the hold repair, 15.0 / 12.7 /
10.0 MHz).

### `release/v.2.0.0-rc2/`, `v.2.0.0-rc1/`, `v.1.3.1/` to `v.1.0.0/`
Release candidates of 10 November and the preliminary states before them, each with its release note, hashes, GDS
and netlists. Not for fabrication.

### `candidate/v.2.4.1/`
Not a release. The candidate GDS of the reissue `v.2.4.1` (the chip of `v.2.4.0` with the die outline also on
prBoundary.drawing 189/0), its hash and the script that runs the minimum rule set on it on a second machine. Its
`README.md` states which checks had finished when it was made. Do not submit from this folder.

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

This repository is a research and development SoC implementation. The releases from `v.2.0.1` on are complete
with their checks, and the release named in `doc/info.json` is the one meant for the submission. The states before
`v.2.0.1` are kept as a record and are not for fabrication. Folders under `candidate/` are not releases.
