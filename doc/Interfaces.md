# SoC2611 interfaces: pins, protocols, clocks, supplies

Pin numbers and pad cells per pin: `doc/Datasheet.md` (QFN64 table) and `SoC2611-main/constraints/bond_table.csv`.
Timing constraints: `SoC2611-main/constraints/design.sdc`, `chip_extra.sdc`. Top entity: `soc2611_chip_top`
(exported as `SoC2611`). All signal pads are 3.3 V `sg13cmos5l_io` cells; the core runs at 1.2 V.

## 1. Pin groups and protocols (48 signal pins)

| Group | Pins | Direction | Pad cell | Protocol / behaviour |
|---|---|---|---|---|
| `clk_x2_in` | 1 | in | IOPadIn | 100 MHz reference. No PLL: core clock `clk_main` = /2 (50 MHz), camera master clock = /4 (25 MHz), HyperBus CK = core/2 (25 MHz). |
| `porst_n_in` | 1 | in | IOPadIn | active-low power-on reset, synchronised on chip. |
| HyperBus `hb_ck_out`, `hb_csn_out[0]`, `hb_resetn_out` | 3 | out | Out16mA (CK), Out4mA | HyperBus (Cypress/Infineon HyperRAM, 3.0 V, single-ended clock), one 8 MB device; CS#1 not bonded. |
| HyperBus `hb_rwds`, `hb_dq[7:0]` | 9 | inout | IOPadInOut16mA | RWDS strobe and 8-bit DDR data; `_in/_out/_oe` triples at the core boundary; input capture on `hb_rwds_in` (25 MHz). |
| Camera `cam_pclk_in`, `cam_d_in[7:0]`, `cam_vs_in`, `cam_hs_in` | 11 | in | IOPadIn | parallel 8-bit DVP (OV7670 class), 24 MHz pixel clock, VSYNC/HREF framing, 640x480. |
| Camera `cam_mclk_out`, `cam_reset_out`, `cam_pwdn_out`, `cam_scl_out` | 4 | out | IOPadOut4mA | master clock 25 MHz, reset, power-down, I2C clock (SCCB). |
| Camera `cam_sda` | 1 | inout | IOPadInOut4mA | I2C/SCCB data, open drain (`cam_sda_out`/`cam_sda_oe_out`); sensor init table in the camera block. |
| UART `uart_tx_out`, `uart_rx_in` | 2 | out / in | Out4mA / In | 115200 8N1 console and firmware loader. |
| SPI `spi_sclk_out`, `spi_mosi_out`, `spi_csn_out`, `spi_miso_in` | 4 | out x3 / in | Out4mA / In | SPI master, mode 0, one chip select (flash or SD card). |
| GPIO `gpio_out[3:0]`, `gpio_in[3:0]` | 8 | out / in | Out4mA / In | LEDs and buttons of the firmware suite; **`gpio_in[3]` is the boot strap** (1 = run the image at `0x4000`, 0 = UART loader). |
| JTAG `jtag_tck_in`, `jtag_tms_in`, `jtag_tdi_in`, `jtag_tdo_out` | 4 | in x3 / out | In / Out4mA | VexRiscv debug TAP: 4-bit IR, IDCODE `0x10001FFF`, OpenOCD `vexriscv` target with `cpu0.yaml` (`SoC2611-main/docs/asic_jtag_README.md`). |

## 2. Supplies (16 pads)

| Domain | Pads | Voltage | Notes |
|---|---|---|---|
| VDD / VSS (core) | 4 + 4 | 1.2 V | one pair per side; core ring and Metal4 / TopMetal1 grid, SRAM macro grids on TopMetal1. |
| IOVDD / IOVSS (pads) | 4 + 4 | 3.3 V | one pair per side; pad ring supply. |

Budget: about 200 mW at 50 MHz across the 16 supply pads (`padlist_qfn64.md`); IR-drop analysis is part of the
final release. No other power domains, no power gating, clock gating by ICG cells on the main clock tree.

## 3. Clocks and timing constraints (from `design.sdc`)

| Clock | Period | Source | Constrained ports |
|---|---|---|---|
| `clk_x2` | 10.0 ns | `clk_x2_in` | internal; divides to `clk_main` (20 ns) and the camera master clock (40 ns) |
| `hb_ck` | 40.0 ns | generated | HyperBus outputs: output delay max 3.0 / min -1.0 ns |
| `hb_rwds` | 40.0 ns | `hb_rwds_in` | `hb_dq_in` input delay max 2.0 / min 0.5 ns |
| `cam_pclk` | 41.67 ns | `cam_pclk_in` | `cam_d_in`, `cam_vs_in`, `cam_hs_in` input delay 5.0 ns |
| `clk_main` | 20.0 ns | derived | GPIO, UART, SPI: input and output delay 2.0 ns |

Clock-domain crossings (camera pixel clock, HyperBus RWDS, JTAG TCK) go through the synchronisers and FIFOs described in
`SoC2611-main/docs/ASIC_PORT.md` section 5.

## 4. Reset and boot

`porst_n_in` low resets the whole chip. On release the boot ROM (in the 16 KiB TCM at address 0) runs; `gpio_in[3]`
selects UART loader or direct jump (section 1 of `doc/RegisterMap.md`). The JTAG TAP is live from reset and can halt
the CPU, load memory and resume (used by the `test_debug.py` cocotb test).

## 5. Memory BIST

195 of the 298 SRAM macros are `RM_IHPSG13_*_bm_bist` variants. The BIST is not used: every `A_/B_BIST_*` input is
tied to 0 and `A_DLY/B_DLY` to 1 in the macro wrappers (`HW/platform/ihp/ihp_sram_macro_sel.vhd`, visible in
`SoC2611-main/rtl/SoC2611.v` as `*_bist_*` ports driven by constants). No scan chains are inserted in this
revision; memory test is done by firmware over JTAG or UART.

## 6. Package

QFN64, 9 x 9 mm body, 0.5 mm pitch, die 6.6 x 6.6 mm, 16 pads per side, 70 x 70 um bond pads, seal ring and
registration label included in the GDS (`release/v.1.3.1/ReleaseNote.md`).
