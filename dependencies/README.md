# Dependencies of SoC2611

Nothing in this folder is vendored; every dependency is identified by version or commit so the release can be
reproduced. See also `doc/info.json` ("dependencies", "tools").

## Process design kit

| Item | Version | Notes |
|---|---|---|
| IHP-Open-PDK | commit `dcb03b1e2d24250bccbb2e8783d55d2b4f734f14` (Merge PR #1311, 30 Oct 2026), unmodified | process `SG13CMOS5L` (`ihp-sg13cmos5l`) |
| Standard cells | `sg13cmos5l_stdcell` (typ/slow/fast Liberty, LEF, CDL, GDS from the PDK) | synthesis used the typ library |
| IO cells | `sg13cmos5l_io` (IOPadIn, IOPadOut4mA/16mA, IOPadInOut4mA/16mA, IOPadVdd/Vss, IOPadIOVdd/IOVss, Corner, Filler) | 3.3 V pads, 1.2 V core |
| SRAM macros | `RM_IHPSG13_1P_*` and `RM_IHPSG13_2P_*` (298 instances, 195 of them `_bm_bist` variants with BIST tied off), Liberty typ/slow/fast, LEF, CDL, GDS from the PDK | list by type in `SoC2611-main/synthesis/inventory.md` |
| DRC / LVS decks, fill recipes | the PDK's KLayout decks for `ihp-sg13cmos5l` at the same commit | run with KLayout 0.30.x |

## Design sources

| Item | Version | Notes |
|---|---|---|
| ztachip (AI accelerator, SoC fabric) | DGrid-SoC1 fork `aravindgp/DGrid-SoC1`, branch `worktree-asic-rtl-prep` | VHDL, Apache-2.0 |
| VexRiscv (RISC-V CPU) | VexRiscv commit `5ef1bc775fdbe942875dd7906f22aa98e6cffaaf`, generated with SpinalHDL v1.9.3 | JTAG debug TAP, reset vector 0, black-boxed cache memories |
| HyperBus controller, camera, UART, SPI, GPIO, timer, boot ROM | DGrid-SoC1 `HW/asic/rtl/`, `HW/src/soc/`, `HW/asic/fw/bootrom/` | |

## Tools

| Tool | Version | Used for |
|---|---|---|
| GHDL | 5.x with the synth export (`SoC2611-main/rtl/SoC2611.v`) and as cocotb simulator | RTL export, simulation |
| Yosys | 0.70+277 | synthesis (`SoC2611-main/synthesis/synth.ys`) |
| OpenROAD | `dcf36133` (build of 17 Feb 2026) | floorplan, placement, CTS, routing, ECO, parasitics |
| KLayout | 0.30.5 | stream, seal ring, fill, density, DRC, LVS |
| cocotb | 1.9 with the GHDL backend | firmware-level verification |
| SpinalHDL / sbt / OpenJDK | 1.9.3 / 1.9.9 / 11 | CPU generation |
| OpenOCD | with the `vexriscv` target | JTAG bring-up (`cpu0.yaml`) |
