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
request: IHP-GmbH/Open-Silicon-MPW issue #79). State of 14 November 2026:

- **Latest release: `release/v.3.0.0`** (14 Nov 2026), the release `doc/info.json` names and the version meant
  for fabrication. Its `gds/SoC2611.gds.gz` (92,020,915 bytes, SHA-256
  `5cb1caa218ee16156cb656467195274cfbb17a92be66035459b41e853d3abccf`) is the one GDS of the release: fully filled,
  under 100 MB, and the file every check below ran on.
- Routing: 0 detailed-route violations, 0 signal nets without a wire; the power grid check passes on VDD and VSS.
- Input pins without a net: 0, on every standard cell, pad and SRAM macro; every net with loads has a driver.
  The routed netlist has the same wiring as the netlist after synthesis: 801,501 input pins compared, each driven
  by the same source.
- IHP minimum rule set (deep mode) on the GDS of the release: 26 of 26 rule tables and the GatPoly filler table
  completed, 0 violations. Density: 0 violations, by our own calculation and by IHP's density deck.
- LVS (KLayout, IHP deck): the netlists match, 354,825 instances of the chip top. SRAM macros and pad cells are
  black boxes with their pins.
- Connectivity: every signal net was traced in the GDS against the netlist, 343,545 nets, 0 open and 0 shorted pins.
- NWell rules without connectivity: 13 of 13 at 0.
- Antenna: 0 nets above the limit of the router's check, and 0 violations in every rule of the PDK antenna table.
- Timing, with the parasitics of the routed wires: hold is met at all three corners. System clock 64.4 MHz fast,
  45.5 MHz typical, 29.4 MHz slow; the double-rate input clock is twice that. The 100 MHz input clock of the
  constraints is met at the fast corner only, and the slow-corner figure is the one to rate the chip at.
- Simulation of the routed netlist, pad to pad (reset, boot from the external memory, firmware, UART): without
  delays, the quick suite, the full suite (6 of 6 checks) and a camera capture pass, and the quick suite and the
  capture pass again with random start values in every register; with the cell and wire delays of the timing
  analysis, the quick suite passes at the rated speed of each corner, and a control run far too fast fails as it
  must.
- Core supply: metal bars between the pad ring and the core; worst static drop at 0.78 W 71 mV on VDD and 122 mV
  on VSS (217 mV and 205 mV before).
- Die outline: on prBoundary.drawing (189/0), 6600 um by 6600 um, besides prBoundary.boundary (189/4) and
  EdgeSeal.boundary (39/4).
- Branches named `candidate-<version>` carry a candidate GDS for the checks on a second machine and
  `checks-<version>` the results; they are not releases.
- Functional verification (RTL): firmware suite 6/6 PASS on the chip top, boot loader, HyperBus and SRAM-wrapper
  tests PASS (`SoC2611-main/verification/sim/`).
- No silicon has been measured. The speeds are results of static timing analysis.
- What changed, the hashes and the known limits of each release are in its `ReleaseNote.md`.

> **Do not fabricate any earlier file.** Every release up to `v.2.4.0` and the candidates `v.2.5.0`, `v.2.3.1`
> and `v.2.4.1` have 384 buffers without a connection on their input pin: the top buffers of the buffer trees of
> the 22 signals with the most loads, among them the reset of the system clock domain with about 50,000 loads.
> Those signals do not reach their loads, so those chips would not work. The trees were built by a script of the
> flow on 30 October, which moved the loads to the new buffers and did not join the top buffers to the original
> signal. No check of those releases could see it: layout and netlist agree, so LVS matched; static timing analysis
> skips a pin without a driver; the firmware tests ran on the RTL. It was found on 13 November while a simulation of
> the routed netlist was being prepared. `v.3.0.0` connects the 384 inputs, routes the 44 nets of the 22 signals
> and adds the two checks that would have found it: input pins without a net, and the simulation of the routed
> netlist.

## Antenna nets per release

Two antenna checks are run. The first is the router's check (OpenROAD `check_antennas`, ratio limits of the
technology LEF) on the routed database: it asks for the protection diode on the layer under check. The second is
the antenna table of the PDK (KLayout, `antenna.drc`, rules Ant.a to Ant.i) on the layout: it takes the protection
diode from the complete net and allows a cumulative metal-to-gate ratio of 20,000 with a diode. State of
14 November 2026. Every release before `v.3.0.0` has the defect of the notice above, whatever its antenna count.

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
| `v.2.4.0` | 13 Nov | 78 | 101 | 6 | three passes: 865 more diodes, 98 buffers at SRAM pins | 54.7 / 45.5 / 29.4 MHz |
| `v.2.5.0`, candidate, withdrawn | 13 Nov | 0 | 0 | not finished | four passes: 91 more diodes directly under the wires, long Metal2 runs of 7 nets moved to Metal4 | 54.7 / 45.5 / 29.4 MHz |
| **`v.3.0.0`**, latest release | 14 Nov | **0** | **0** | **0** | the four passes of `v.2.5.0`, 12 buffers in front of the 6 TopMetal1 nets, 26 more diodes after the repair route | 64.4 / 45.5 / 29.4 MHz |

- `v.3.0.0` is the latest release: both antenna checks are at 0. The result of the PDK antenna table is in
  `release/v.3.0.0/checks/antenna_ihp_table.txt`.
- The 6 nets of the PDK antenna table in `v.2.3.0` and `v.2.4.0` were each one small gate on 1.3 to 1.9 mm of
  TopMetal1, which is 1.64 um wide: rule Ant.e through TopMetal1, ratio 20,029 to 29,054 against the limit of
  20,000; every other rule of the table was at 0. In `v.3.0.0` each has a buffer with a large input gate in front
  of its receiving pin.
- After the repair route of `v.3.0.0`, 22 nets were above the limit of the router's check: nets moved to make room
  for the repaired signals, and 4 of the repaired signals themselves. 26 diodes directly under the wires brought the
  count back to 0.
- The fast-corner speed of `v.3.0.0` is higher because the four longest wires of the fast corner, each about 20 mm
  between pins less than 3 mm apart, are laid straight; the typical and slow corners are unchanged.
- `v.2.5.0` was withdrawn when the defect of the notice above was found; its checks were not finished.
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
│   └── v.2.4.1/        (candidate GDS and DRC run script for checks on a second machine; not a release; has the open-input defect)
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
│   ├── v.3.0.0/        (latest; the release doc/info.json names)
│   │   ├── ReleaseNote.md
│   │   ├── gds/            (SoC2611.gds.gz: the one GDS, fully filled)
│   │   ├── netlist/        (SoC2611.cdl.gz, SoC2611.v.gz)
│   │   ├── density.txt
│   │   └── checks/         (DRC verdicts and result databases, density on the IHP deck, LVS, net trace, timing, both
│   │                        antenna checks, NWell rules, input pins without a net, simulation, supply drop)
│   ├── v.2.4.0/, v.2.3.0/, v.2.2.0/, v.2.1.0/, v.2.0.1/     (earlier releases, same layout; open-input defect, not for fabrication)
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

### `release/v.3.0.0/` (latest)
Release of 14 November 2026, the one `doc/info.json` points at. One fully filled GDS (`gds/SoC2611.gds.gz`: seal
ring, PDK fill and a thinned top-up fill), CDL and Verilog netlists, the density of exactly this file, and under
`checks/` the verdicts and result databases of the IHP minimum rule set, the density deck, the LVS summary, the net
trace, the timing on the routed wires, the antenna summary of the router, the result of the PDK antenna table, the
NWell rules, the check of input pins without a net and of the wiring against synthesis, the simulation summary, the
supply drop and the proof that the packaged file is the checked file. SHA-256 hashes, what changed and the known
limits are in its `ReleaseNote.md`.

### `release/v.2.4.0/`, `v.2.3.0/`, `v.2.2.0/`, `v.2.1.0/`, `v.2.0.1/`
Earlier complete releases with the same layout and the checks of their time: `v.2.4.0` (three antenna passes,
54.7 / 45.5 / 29.4 MHz), `v.2.3.0` (four speed steps, 54.2 / 44.3 / 28.7 MHz), `v.2.2.0` (two speed rounds, 45.7 /
30.0 / 18.9 MHz), `v.2.1.0` (the first antenna repair, 590 nets left of 6,129, 15.8 / 13.2 / 10.3 MHz) and
`v.2.0.1` (the first clean chip with the hold repair, 15.0 / 12.7 / 10.0 MHz). All of them have the 384 open buffer
inputs of the notice under Project status. Not for fabrication.

### `release/v.2.0.0-rc2/`, `v.2.0.0-rc1/`, `v.1.3.1/` to `v.1.0.0/`
Release candidates of 10 November and the preliminary states before them, each with its release note, hashes, GDS
and netlists. Not for fabrication.

### `candidate/v.2.4.1/`
Not a release. The candidate GDS of the reissue `v.2.4.1` (the chip of `v.2.4.0` with the die outline also on
prBoundary.drawing 189/0), its hash and the script that runs the minimum rule set on it on a second machine. Its
`README.md` states which checks had finished when it was made. It has the 384 open buffer inputs of `v.2.4.0`. Do
not submit from this folder.

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

This repository is a research and development SoC implementation. The release named in `doc/info.json`,
`v.3.0.0`, is the one meant for the submission. All earlier releases are kept as a record and are not for
fabrication: those before `v.2.0.1` are preliminary states, and `v.2.0.1` to `v.2.4.0` have the 384 open buffer
inputs of the notice under Project status. Folders under `candidate/` are not releases.
