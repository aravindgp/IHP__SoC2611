# SoC2611 lean test chip — QFN64 pad budget (draft 2026-10-30)

Package: IHP open-source MPW packaging service, **QFN64, 9 × 9 mm body, 0.5 mm
pitch, maximum die 6.6 × 6.6 mm**, 320 € bonding-diagram setup, 10 / 20 / 40
pieces 790 / 1 160 / 1 900 € (services page, Oct 2026). Pad cells:
`sg13cmos5l_io` (3.3 V IO / 1.2 V core): `IOPadIn`, `IOPadOut4mA/16mA/30mA`,
`IOPadTriOut*`, `IOPadInOut*`, `IOPadVdd/Vss` (core), `IOPadIOVdd/IOVss` (IO),
`Corner`, `Filler*`.

Decision context (updated): **video-camera product** — the camera input stays on
the chip, VGA does not (`camera_enabled_c = TRUE`, `vga_enabled_c = FALSE`),
**8 PCOREs**, no DDR (external HyperRAM is main memory), HyperBus controller on
the SoC's 128-bit AXI master.

| Group | Pins | Pad cell | Notes |
|---|---:|---|---|
| Clock in (`clk_x2_in`, 100 MHz) | 1 | IOPadIn | no PLL in the open PDK; core clock = /2, camera clock = /4 on chip |
| Power-on reset `porst_n_in` | 1 | IOPadIn | |
| **HyperBus** CK, CS#, RESET# | 3 | Out16mA / Out4mA ×2 | single-ended CK (3.0 V HyperRAM), CK = core/2; one 8 MB device |
| HyperBus RWDS, DQ[7:0] | 9 | IOPadInOut16mA | `_in/_out/_oe` triples at the core boundary |
| **Camera** PCLK, D[7:0], VSYNC, HREF | 11 | IOPadIn | parallel 8-bit DVP (OV7670 class) |
| Camera MCLK, RESET#, PWDN, SCL | 4 | IOPadOut4mA | MCLK = camera clock (25 MHz) |
| Camera SDA | 1 | IOPadInOut4mA | open drain from `cam_sda_out`/`cam_sda_oe_out` |
| UART TX / RX | 2 | IOPadOut4mA / IOPadIn | console + firmware loader |
| SPI SCLK, MOSI, MISO, CS# | 4 | Out4mA ×3 / In | flash or SD (`spi_csn_out`) |
| GPIO out[3:0] / in[3:0] | 8 | IOPadOut4mA / IOPadIn | LEDs / buttons of the firmware suite; **in[3] is the boot strap** (1 = run image at 0x4000, 0 = UART loader in the TCM boot ROM) |
| JTAG TCK, TMS, TDI / TDO | 4 | IOPadIn ×3 / IOPadOut4mA | VexRiscv debug TAP (`HW/riscv/asic_jtag`, openocd irlen 4, idcode 0x10001fff) |
| **Signal total** | **48** | | matches `soc2611_chip_top` |
| VDD core (1.2 V) / VSS | 4 + 4 | IOPadVdd / IOPadVss | one pair per side |
| VDDIO (3.3 V) / VSSIO | 4 + 4 | IOPadIOVdd / IOPadIOVss | one pair per side |
| **Supply total** | **16** | | one core and one IO pair per side; enough for ~200 mW at 50 MHz (to be checked by IR analysis) |
| **Used** | **64 / 64** | | no spare pin |

If pins get tight: fold the boot strap into a GPIO input, drop CS#1 (one 8/16 MB
HyperRAM), or use CK only (no CK# anyway). VGA (14 pins) and the second SPI
chip-selects do not fit and are out.

Pad-ring geometry: 64 pads around a ≈ 6.0 mm die edge = 16 per side at a
≈ 350 µm pad pitch — comfortable for the 3.3 V IO cells; fillers take up the
rest. The die-size limit 6.6 mm is the binding constraint, not pad count.

The chip top `HW/asic/rtl/soc2611_chip_top.vhd` exposes exactly this set:
`clk_x2_in`, `porst_n_in`, HyperBus (`hb_ck_out`, `hb_csn_out[1:0]`,
`hb_resetn_out`, `hb_rwds_in/out/oe_out`, `hb_dq_in/out/oe_out[7:0]`), camera
(`cam_pclk_in`, `cam_d_in[7:0]`, `cam_vs_in`, `cam_hs_in`, `cam_mclk_out`,
`cam_reset_out`, `cam_pwdn_out`, `cam_scl_out`, `cam_sda_out`/`cam_sda_oe_out`),
UART, SPI (1 CS), GPIO 4+4. JTAG (4 pins) is not in the pin set yet: adding it
costs 4 supply pins or the second HyperRAM CS# plus 3 GPIOs. Dropped: `clk_camera_in` (camera XCLK generated on chip from
`clk_x2`), `clk_vga_in`, `clk_ddr_in`, the AXI `ddr_*` port (internal to the
HyperBus controller), `apb_*`, VGA group. Bidirectional pads are instantiated in
the chip top from the `_i/_o/_oe` triples (the core RTL stays unidirectional).
