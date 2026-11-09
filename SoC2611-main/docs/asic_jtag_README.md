# VexRiscv for the DGrid-SoC1 ASIC: JTAG debug, reset vector 0, black-boxed memories

Drop-in replacement for `HW/riscv/asic/riscv.vhd` (same entity `riscv`, all existing ports
unchanged), with three differences:

1. **JTAG debug port**: VexRiscv `DebugPlugin` + SpinalHDL `JtagBridge` (a real 4-bit-IR TAP,
   IDCODE `0x10001FFF`) + `SystemDebugger`, the same debug stack as the Briey/Murax demos.
   This replaces the Xilinx `BSCANE2` used in `HW/riscv/xilinx_jtag`.
2. **Reset vector `0x00000000`** (TCM boot ROM), set in the generator, not patched into the VHDL.
3. **All memories are black boxes**: the I$ data/tags, D$ data/tags and register file are
   instances of SpinalHDL's standard black box `Ram_1w_1rs` instead of inline VHDL arrays,
   so the ASIC memory layer can map them onto SRAM macros. See `mem_blackboxes.md`.

Everything else matches `HW/riscv/sim/riscv.scala`: IBusCached (8 KiB, 2 ways, 32 B lines),
DBusCached (8 KiB, 1 way), AXI4 32-bit iBus/dBus masters, `CsrPluginConfig.smallest(mtvecInit = 0x80000020)`,
MUL/DIV, full barrel shifter, SYNC register file, early branch, YamlPlugin.

## Files

| File | Content |
|---|---|
| `riscv.scala` | generator (package `vexriscv.riscv`) |
| `riscv.vhd` | generated core (+ default `'0'` on the three JTAG inputs, see below) |
| `cpu0.yaml` | YamlPlugin output, needed by openocd (`vexriscv cpuConfigFile`) |
| `ram_blackboxes_ref.vhd` | behavioural `Ram_1w_1rs` (simulation / functional spec); compile **before** `riscv.vhd` |
| `mem_blackboxes.md` | every black-box instance with generics, ports and semantics |

## Versions

* SpinalHDL **v1.9.3** (git head `029104c77a54c53f1edda327a3bea333f7d65fd9`, same as `HW/riscv/sim/riscv.vhd`)
* VexRiscv commit **`5ef1bc775fdbe942875dd7906f22aa98e6cffaaf`** (the "Git hash" in the sim/xilinx cores;
  its `build.sbt` pins SpinalHDL 1.9.3, Scala 2.11.12)
* sbt 1.9.9 launcher (project `build.properties` selects sbt 1.6.0), OpenJDK 11

## Regenerate

```sh
curl -L -o vex.tgz https://codeload.github.com/SpinalHDL/VexRiscv/tar.gz/5ef1bc775fdbe942875dd7906f22aa98e6cffaaf
tar xzf vex.tgz && cd VexRiscv-5ef1bc775fdbe942875dd7906f22aa98e6cffaaf
mkdir -p src/main/scala/vexriscv/riscv
cp <repo>/HW/riscv/asic_jtag/riscv.scala src/main/scala/vexriscv/riscv/
sbt "runMain vexriscv.riscv.riscv"          # writes riscv.vhd and cpu0.yaml in the current dir
# give the JTAG inputs a default so instantiations without them still elaborate:
sed -e "s/^    jtag_\(tms\|tdi\|tck\) : in std_logic;\$/    jtag_\1 : in std_logic := '0';/" \
    riscv.vhd > <repo>/HW/riscv/asic_jtag/riscv.vhd
cp cpu0.yaml <repo>/HW/riscv/asic_jtag/
```

The only change to the generated VHDL is that `sed` (3 lines of the `riscv` entity).

## New ports (entity `riscv`)

| Port | Dir | Description |
|---|---|---|
| `jtag_tck` | in (default `'0'`) | JTAG TCK; clocks the TAP (own clock domain, crossed into `io_mainClk` by `FlowCCByToggle`) |
| `jtag_tms` | in (default `'0'`) | JTAG TMS |
| `jtag_tdi` | in (default `'0'`) | JTAG TDI |
| `jtag_tdo` | out | JTAG TDO (changes on TCK falling edge); no output-enable – drive a pad, or tri-state it outside the TAP-shift states if several TAPs share TDO |
| `debug_resetOut` | out | debugger reset request (openocd `reset`/`soft_reset_halt`); already resets the CPU internally, export it if the SoC peripherals should be reset too |

There is no TRST: the TAP resets with TMS high for 5 TCK (openocd does this). The debug
logic (`debugClockDomain`) is reset by `resetCtrl_mainClkReset` only, so a debugger reset
(`debug_resetOut`) resets the CPU but not the debug state. `hardwareBreakpointCount = 0`
(same as `xilinx_jtag`): code in the boot ROM can only be single-stepped, not
breakpointed; raise it in `RiscvConfig.default` if needed (a few flops per breakpoint).
`soc_base.vhd` / the `riscv` component in `ztachip_pkg.vhd` do not connect the new ports
yet; with the component unchanged the inputs take their default `'0'` and the outputs
are open.

## openocd

Use the VexRiscv fork of openocd (`https://github.com/SpinalHDL/openocd_riscv`, target `vexriscv`)
and `cpu0.yaml` from this directory:

```tcl
adapter speed 1000
set _CHIPNAME dgrid
jtag newtap $_CHIPNAME bridge -expected-id 0x10001fff -irlen 4 -ircapture 0x1 -irmask 0xF
target create $_CHIPNAME.cpu0 vexriscv -endian little -chain-position $_CHIPNAME.bridge
vexriscv readWaitCycles 12
vexriscv cpuConfigFile HW/riscv/asic_jtag/cpu0.yaml
poll_period 50
init
soft_reset_halt
```

(adapter/interface config first, e.g. `-f interface/ftdi/olimex-arm-usb-tiny-h.cfg`; this is the
Briey `tcl/target/briey.cfg` recipe with the chip name changed.) Then `riscv64-unknown-elf-gdb`
`target extended-remote :3333`, `load`, `continue`. A `soft_reset_halt` restarts at the reset
vector 0 (boot ROM).

## Checks

* `ghdl -a --std=08 -frelaxed ram_blackboxes_ref.vhd riscv.vhd` (GHDL 1.0): clean.
* Firmware suite (`HW/asic/cocotb`, `test_fw`, FAST_UART=1) with this core replacing
  `HW/riscv/asic/riscv.vhd` in the `filelist.f` order (config.vhd -> tb/config_sim.vhd as
  FAST_UART=1 does), JTAG pins unconnected: **6/6 PASS** (boot at 0 in the TCM boot ROM,
  strap gpio_in(3) -> jump to 0x4000; T01..T06 pass, LED sequence as with the old core).

```sh
cd HW/asic/cocotb
make VHDL_SOURCES="<filelist.f with HW/riscv/asic/riscv.vhd replaced by
     HW/riscv/asic_jtag/ram_blackboxes_ref.vhd HW/riscv/asic_jtag/riscv.vhd>
     HW/simulation/mem128.vhd HW/asic/tb/tb_dgrid_soc1_fw.vhd" \
     TOPLEVEL=tb_dgrid_soc1_fw COCOTB_TEST_MODULES=test_fw FAST_UART=1 SIM_BUILD=/tmp/sim_jtag
```
