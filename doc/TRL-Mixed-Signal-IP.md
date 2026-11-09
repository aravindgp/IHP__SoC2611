# Mixed-Signal IP Quality Assessment using TRL scale

> **Declared level: TRL 2.** Only items with evidence in this repository are ticked, and every tick names the file
> behind it. SoC2611 is a digital SoC (RISC-V + AI accelerator), so the items about design equations, Verilog-A
> models, analog ports, mismatch and mixed-signal simulation do not apply; they are left unticked with the note
> "n/a (digital)". TRL1 and TRL2 are complete. TRL3 is incomplete because no gate-level (post-synthesis or
> post-route) simulation has been run yet; TRL5 is incomplete because the released layout is preliminary (routing
> closure in progress, DRC not clean, LVS not run). The level will be raised with the final release.

The provided set of the quality assessment criteria, using TRL (Technology Readiness Level) scale, is a tool for designers to auto evaluate a submitted design. The purpose of this tool is to
have a short overview of IP in terms of its maturity.

Paths are relative to the repository root. `SoC2611-main/testbenches/` and `SoC2611-main/verification/sim/` were
added on 9 November 2026 with the testbench sources and the simulation logs they refer to.

---

## TRL1 - Basic principles observed

- [x] Is the IP functionality clearly described?
  `doc/Specification.md` (function list, technology table), `README.md`, `SoC2611-main/README.md`.
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
  (`tb_dgrid_soc1_hb`: HyperRAM model, IHP SRAM macro models, JTAG VexRiscv core, clock gating), 31 Oct 2026;
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
  `doc/RegisterMap.md`: memory map, APB peripheral registers, accelerator host registers (sources:
  `HW/src/ztachip_pkg.vhd`, `SW/src/soc.h`, `SW/base/zta.h` of the design repository).
- [x] Do authors supply a complete test bench to validate the IP block-level architecture?
  `SoC2611-main/testbenches/vhdl/tb_dgrid_soc1_hb.vhd` (chip top + HyperRAM model), `tb_dgrid_soc1_fw.vhd`
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
  Gate level: `release/v.1.3.1/netlist/SoC2611.v.gz` (post-route Verilog) and `SoC2611.cdl.gz` (LVS netlist);
  the same for every earlier release. Synthesis script and statistics: `SoC2611-main/synthesis/`.
- [x] Are all dependencies of the IP schematics on logic libraries declared?
  `dependencies/README.md`, `doc/info.json` (PDK commit, sg13cmos5l_stdcell, sg13cmos5l_io, RM_IHPSG13 SRAM),
  `SoC2611-main/README.md` (source-to-release mapping).
- [ ] Are the analog IP ports fully specified at electrical level? n/a (digital); pad cells and supplies in
  `doc/Interfaces.md`.
- [x] Are the digital IP ports fully specified at logical level (e.g. protocols)?
  `doc/Interfaces.md` (every pin group with its protocol, clocking, timing constraints, boot strap, JTAG TAP),
  `doc/Datasheet.md` (QFN64 pin table), `SoC2611-main/constraints/design.sdc`.
- [ ] Do authors supply a mixed-signal test bench to validate the IP schematics?
  Not yet: the testbenches run on RTL; gate-level simulation is planned on the final netlist.
- [ ] Is any verification procedure given to check the IP schematic performance figures?
  Not yet (same as above).
- [ ] Are mixed-signal simulation results of the IP schematics reported for a typical case?
  Not yet (same as above).

## TRL4 - Full design at schematic level

- [ ] Are the mixed-signal simulation results of the IP schematics extended to process, supply and temperature (PVT) corners?
  Not yet. Corner definitions used by the flow: typ 1.20 V / 25 C, slow 1.08 V / 125 C, fast 1.32 V / -40 C
  (`SoC2611-main/docs/platform_README.md`). Multi-corner STA is part of the final release.
- [ ] Are the mixed-signal simulation results of the IP schematics extended to technology mismatching? n/a (digital).
- [x] Are the authors defining the mixed-signal supply domains of the IP schematics and their individual power requirements?
  `doc/Interfaces.md` and `doc/Datasheet.md` "Supplies": one domain pair VDD/VSS 1.2 V (core) and IOVDD/IOVSS
  3.3 V (pads), 16 supply pads, budget about 200 mW at 50 MHz (IR analysis pending).
- [ ] Does the IP description include any power consumption model (e.g. as a function of input stimuli)? Not yet.

## TRL5 - Full design at layout level

- [x] Is the IP complete layout available?
  `release/v.1.3.1/gds/` (whole chip with seal ring and fill; preliminary: 0 supply shorts, 1,624 detailed-route
  violations open, see `release/v.1.3.1/ReleaseNote.md` and `STATUS_2026-11-09.md`).
- [x] Are all dependencies of the IP layout on logic libraries declared? `dependencies/README.md`, `doc/info.json`.
- [ ] Do authors supply a clean DRC report?
  Not clean yet. Available: density deck PASS on every release (`release/v.1.3.1/density_fullfill.txt`),
  per-table results of the IHP minimum deck on an intermediate snapshot (`SoC2611-main/verification/drc/tables/`),
  antenna summary (`SoC2611-main/verification/drc/antenna_openroad_summary.txt`), waivers
  (`SoC2611-main/Flow/scripts/signoff/waivers/`). The full deck on the final GDS is part of the final release.
- [ ] Do authors supply a clean LVS report?
  Not yet at chip level. Block-level LVS of the IO cell, a standard cell and a routed test block MATCH
  (`SoC2611-main/Flow/scripts/signoff/README.md`); chip LVS runs on the final database.
- [ ] Are post-layout mixed-signal simulation results of the IP layout reported for PVT corners? Not yet.

## TRL6 - Full design for SoC integration

- [ ] Does the IP come with suitable descriptors for digital-on-top integration (e.g. Liberty, LEF)?
  n/a: SoC2611 is a complete chip, not a hard IP for integration. The LEF/Liberty it depends on are the PDK's.
- [ ] Is the IP incorporating any BIST mechanism? If so, is it properly documented?
  No BIST is used. 195 of the 298 SRAM macros are `_bm_bist` variants; their BIST ports are tied off
  (`doc/Interfaces.md` "Memory BIST", `SoC2611-main/rtl/SoC2611.v`: `*_bist_*` ports driven to 0).
- [x] Does the IP document fully define its digital interface?
  `doc/Interfaces.md` and `doc/Datasheet.md` (pins, protocols, clocks, reset, boot strap, JTAG), `doc/RegisterMap.md`.

## TRL7 - Lab demonstrator prototype

- [ ] Has any dedicated test chip been designed for the hard IP?
- [ ] Is the hard IP test chip fully documented (e.g. pad ring)?
- [ ] Are experimental results available from the IP dedicated test chip (Silicon proven)?
- [ ] Do authors supply any comprehensive comparison between IP test chip and post-layout results?

## TRL8 - In-field demonstrator prototype

- [ ] Has the hard IP been integrated in a SoC context?
- [ ] Are experimental IP results available from this SoC (Silicon proven)?
- [ ] Do authors supply any comprehensive comparison between IP SoC and test-chip results?

## TRL9 - Commercial application

- [ ] Are the IP authors providing support for bug fixing or enhancement requests?
  Yes, through GitHub issues on `https://github.com/aravindgp/IHP__SoC2611` (DeepGrid Semi); not ticked because the
  level is not reached.
- [ ] Does the IP documentation include any training materials?
  Programmer guides for the accelerator are in `SoC2611-main/docs/` (not ticked for the same reason).
- [ ] Are the EDA tools and versions used for developing the IP documented?
  `doc/info.json` "tools" and `dependencies/README.md` (Yosys, OpenROAD, KLayout, GHDL, SpinalHDL, cocotb versions).
- [ ] Is the hard IP integrated in any commercial IC? No.
