# Mixed-Signal IP Quality Assessment using TRL scale

> **Declared level: TRL 6**, the highest level a design can reach before silicon. State of release `v.3.0.2`,
> 15 November 2026. Only items with evidence in this repository are ticked, and every tick names the file behind
> it. SoC2611 is a digital SoC (RISC-V + AI accelerator), so the items about design equations, Verilog-A models,
> analog ports and mismatch do not apply; they are left unticked with the note "n/a (digital)", and where an item
> asks for mixed-signal simulation the gate-level simulation of the routed netlist is given. TRL1 to TRL6 are
> complete in every item that applies. TRL7 and above need measured silicon: no SoC2611 chip has been made or
> measured yet, so those levels are not claimed.

The provided set of the quality assessment criteria, using TRL (Technology Readiness Level) scale, is a tool for designers to auto evaluate a submitted design. The purpose of this tool is to
have a short overview of IP in terms of its maturity.

Paths are relative to the repository root. The checks of the released file are in `release/v.3.0.2/checks/`; what
changed against `v.3.0.0` and which results are carried from it is in `release/v.3.0.2/checks/changes_from_v3.0.0.txt`.

---

## TRL1 - Basic principles observed

- [x] Is the IP functionality clearly described?
  `doc/Specification.md` (function list, technology table, ratings), `README.md`, `SoC2611-main/README.md`.
- [x] Is the IP principle of operation explained in detail?
  `SoC2611-main/docs/HardwareDesign.md` (accelerator architecture block by block: dp_core, core, stream, pcore,
  register bank, instruction decoder, ALUs), `SoC2611-main/docs/ASIC_PORT.md` (SoC integration, clock/reset/CDC
  plan, boot path), `doc/RegisterMap.md` (memory map, boot sequence), programmer guides in `SoC2611-main/docs/`.
- [ ] Are the IP architecture design equations fully listed? n/a (digital).
- [ ] Do authors supply any mixed-signal HDL functional model (e.g. Verilog-A) of the IP? n/a (digital); the RTL
  is supplied: `SoC2611-main/rtl/SoC2611.v` (single-file export) and the VHDL sources referenced in
  `SoC2611-main/README.md`.
- [x] Are functional simulation results of the IP reported for a typical case?
  `SoC2611-main/verification/sim/cocotb_icg.log`: firmware suite T01-T06 **6/6 PASS** on the chip top
  (`tb_soc2611_hb`: HyperRAM model, IHP SRAM macro models, JTAG VexRiscv core, clock gating), 31 Oct 2026;
  `SoC2611-main/verification/sim/cocotb_results.xml` (JUnit, 0 failures);
  `SoC2611-main/verification/sim/cocotb_bootldr.log`: boot-ROM UART loader BOOT -> GO -> HELLO **PASS**.
  Test list and pass criteria: `SoC2611-main/verification/sim/README.md`.

## TRL2 - Concept formulation

- [x] Is the IP architecture described at block level?
  `SoC2611-main/docs/HardwareDesign.md`, `SoC2611-main/docs/ASIC_PORT.md` section 2.6, `doc/Specification.md`.
- [x] Are the specifications of each individual block of the IP architecture clearly identified?
  Interfaces and function of each accelerator block in `SoC2611-main/docs/HardwareDesign.md`; memory per block
  in `SoC2611-main/docs/ASIC_PORT.md` section 4 and `SoC2611-main/synthesis/inventory.md` (298 macros by type);
  CPU configuration in `SoC2611-main/docs/asic_jtag_README.md`.
- [x] If the IP architecture can be configured by means of internal registers, is their mapping declared?
  `doc/RegisterMap.md`: memory map, APB peripheral registers, accelerator host registers.
- [x] Do authors supply a complete test bench to validate the IP block-level architecture?
  `SoC2611-main/testbenches/vhdl/tb_soc2611_hb.vhd` (chip top + HyperRAM model), `tb_soc2611_fw.vhd`
  (ASIC top + DDR model), `tb_hyperbus.vhd`, `tb_ihp_mem_equiv.vhd`, `tb_ramw_equiv.vhd`, `tb_fp32.vhd`;
  cocotb drivers `SoC2611-main/testbenches/cocotb/test_fw.py`, `test_bootrom.py`, `test_hyperbus.py`.
- [x] Is any verification procedure given to check the IP block-level performance figures?
  `SoC2611-main/testbenches/README.md` (commands and expected output per test), `SoC2611-main/docs/ASIC_PORT.md`
  sections 3 and 7 (pass criteria), scripts in `SoC2611-main/testbenches/scripts/`.
- [x] Are architectural simulation results of the IP reported for a typical case?
  `SoC2611-main/verification/sim/hb_check2.log` (HyperBus controller 6/6 PASS),
  `tb_ihp_mem6.log` (IHP SRAM wrappers vs reference models, 37 pairs PASS), the firmware suite above.

## TRL3 - Proof of concept at schematic level

- [x] Are the IP schematics available at transistor level (analog parts) and gate level (digital parts)?
  Gate level: `release/v.3.0.2/netlist/SoC2611.v.gz` (routed Verilog) and `release/v.3.0.2/netlist/SoC2611.cdl.gz`
  (LVS netlist). Synthesis script and statistics: `SoC2611-main/synthesis/`.
- [x] Are all dependencies of the IP schematics on logic libraries declared?
  `dependencies/README.md`, `doc/info.json` (PDK commit, sg13cmos5l_stdcell, sg13cmos5l_io, RM_IHPSG13 SRAM),
  `SoC2611-main/README.md` (source-to-release mapping).
- [ ] Are the analog IP ports fully specified at electrical level? n/a (digital); pad cells and supplies in
  `doc/Interfaces.md` and `doc/Datasheet.md`.
- [x] Are the digital IP ports fully specified at logical level (e.g. protocols)?
  `doc/Interfaces.md` (every pin group with its protocol, clocking, timing constraints, boot strap, JTAG TAP),
  `doc/Datasheet.md` (QFN64 pin table), `SoC2611-main/constraints/design.sdc`.
- [x] Do authors supply a mixed-signal test bench to validate the IP schematics?
  Digital: the gate-level test bench of the routed netlist, pad to pad (reset at the pad, boot from the HyperRAM
  model, firmware checks, UART), in `SoC2611-main/testbenches/gate_level/` with its `README.md`.
- [x] Is any verification procedure given to check the IP schematic performance figures?
  `SoC2611-main/testbenches/gate_level/README.md` (tests, pass criteria, commands) and
  `release/v.3.0.2/checks/simulation_summary.txt` (what each run checks, including a control run that must fail);
  static timing on the routed wires: `release/v.3.0.2/checks/timing_routed_wires.txt`.
- [x] Are mixed-signal simulation results of the IP schematics reported for a typical case?
  Digital: `release/v.3.0.2/checks/simulation_summary.txt`: without delays the quick suite, the full suite (6 of 6
  checks) and a camera capture pass, also with random start values in every register; with the delays of the
  routed wires at the typical corner the quick suite passes at an 11.0 ns input clock.

## TRL4 - Full design at schematic level

- [x] Are the mixed-signal simulation results of the IP schematics extended to process, supply and temperature (PVT) corners?
  Corners: typical 1.20 V 25 C, slow 1.08 V 125 C, fast 1.32 V -40 C. Simulation with the cell and wire delays of
  each corner: the quick suite passes at a 17.1 ns (slow), 11.0 ns (typical) and 7.8 ns (fast) input clock, and a
  control run far too fast fails (`release/v.3.0.2/checks/simulation_summary.txt`). Static timing at the three
  corners with hold met everywhere (`release/v.3.0.2/checks/timing_routed_wires.txt`).
- [ ] Are the mixed-signal simulation results of the IP schematics extended to technology mismatching? n/a (digital).
- [x] Are the authors defining the mixed-signal supply domains of the IP schematics and their individual power requirements?
  `doc/Interfaces.md` and `doc/Datasheet.md`: one core domain VDD/VSS 1.2 V and one pad domain IOVDD/IOVSS 3.3 V,
  16 supply pads, power per corner from `SoC2611-main/verification/power/power_estimate.txt`, static voltage drop
  in `release/v.3.0.2/checks/supply_drop.txt`.
- [x] Does the IP description include any power consumption model (e.g. as a function of input stimuli)?
  `SoC2611-main/verification/power/power_estimate.txt`: power per corner and per group from static analysis of the
  routed chip at a toggle rate of 0.1, and the model P = P_leakage + P_dynamic x (f_system / 50 MHz). An estimate:
  no silicon has been measured.

## TRL5 - Full design at layout level

- [x] Is the IP complete layout available?
  `release/v.3.0.2/gds/SoC2611.gds.gz`: the whole chip with seal ring, row fillers and fill, the file
  `doc/info.json` names.
- [x] Are all dependencies of the IP layout on logic libraries declared? `dependencies/README.md`, `doc/info.json`.
- [x] Do authors supply a clean DRC report?
  IHP minimum rule set in deep mode on the released GDS: 26 of 26 rule tables and the GatPoly filler table, 0
  violations (`release/v.3.0.2/checks/drc_minimum_fullfill.txt` and the result databases next to it); on the layout
  without fill 23 of 23 tables, 0 violations (`drc_minimum_nofill.txt`); density 0 violations
  (`release/v.3.0.2/density.txt`, IHP density deck in `density_ihp_deck.txt`); the NWell rules of IHP's maximal deck
  that need no connectivity and every NWell gap, 0 (`nwell_rules.txt`); both antenna checks 0
  (`antenna_summary.txt`, `antenna_ihp_table.txt`). The rest of the maximal deck was not run on the whole chip.
- [x] Do authors supply a clean LVS report?
  `release/v.3.0.2/checks/lvs_summary.txt`: KLayout with the IHP deck, netlists match, 0 warnings, 0 errors, 67 of
  67 circuits, 354,825 instances; SRAM macros and pad cells as black boxes with their pins. Independent of LVS,
  every signal net traced in the GDS against the netlist (`connectivity_trace.txt`) and every input pin checked for a
  net (`open_inputs.txt`).
- [x] Are post-layout mixed-signal simulation results of the IP layout reported for PVT corners?
  Digital: the simulation with the cell and wire delays of the routed layout at the slow, typical and fast corner,
  and the static timing of the routed wires at the same corners (see TRL4).

## TRL6 - Full design for SoC integration

- [ ] Does the IP come with suitable descriptors for digital-on-top integration (e.g. Liberty, LEF)?
  n/a: SoC2611 is a complete chip with its pad ring, not a hard IP for integration into another design. The LEF and
  Liberty files it is built from are the PDK's (`dependencies/README.md`).
- [ ] Is the IP incorporating any BIST mechanism? If so, is it properly documented?
  n/a: no BIST is used. 195 of the 298 SRAM macros are `_bm_bist` variants; their BIST ports are tied off, which is
  documented in `doc/Interfaces.md` "Memory BIST" (memory test runs in firmware over JTAG or UART).
- [x] Does the IP document fully define its digital interface?
  `doc/Interfaces.md` and `doc/Datasheet.md` (pins, protocols, clocks and rated speeds, reset, boot strap, JTAG,
  supplies), `doc/RegisterMap.md` (memory map, registers, firmware rules).

## TRL7 - Lab demonstrator prototype

- [ ] Has any dedicated test chip been designed for the hard IP?
  SoC2611 is itself the test chip: release `v.3.0.2`, submitted to the IHP Open-Silicon-MPW run (issue #79). Not
  ticked because the level needs the measured chip.
- [ ] Is the hard IP test chip fully documented (e.g. pad ring)?
  Pad ring, pinout and package in `doc/Datasheet.md` and `doc/Interfaces.md`; not ticked for the same reason.
- [ ] Are experimental results available from the IP dedicated test chip (Silicon proven)? Not yet: no silicon.
- [ ] Do authors supply any comprehensive comparison between IP test chip and post-layout results? Not yet.

## TRL8 - In-field demonstrator prototype

- [ ] Has the hard IP been integrated in a SoC context?
- [ ] Are experimental IP results available from this SoC (Silicon proven)?
- [ ] Do authors supply any comprehensive comparison between IP SoC and test-chip results?

## TRL9 - Commercial application

- [ ] Are the IP authors providing support for bug fixing or enhancement requests?
  Yes, through GitHub issues on `https://github.com/aravindgp/IHP__SoC2611` (the design team); not ticked because the
  level is not reached.
- [ ] Does the IP documentation include any training materials?
  Programmer guides for the accelerator are in `SoC2611-main/docs/` (not ticked for the same reason).
- [ ] Are the EDA tools and versions used for developing the IP documented?
  `doc/info.json` "tools" and `dependencies/README.md` (Yosys, OpenROAD, KLayout, GHDL, SpinalHDL, cocotb,
  Verilator, Icarus Verilog versions).
- [ ] Is the hard IP integrated in any commercial IC? No.
