# DGSL2611 (DGrid-SoC1) — Datasheet

> **Status: PRELIMINARY — not for fabrication.** Detailed routing has not converged and hold timing on
> CPU↔SRAM paths is open; DRC/LVS are not clean yet. A final release will replace this one.

## Supplies
VDD/VSS: 1.2 V core, IOVDD/IOVSS: 3.3 V IO (one pair of each per side).

## QFN64 pinout
Pin numbering counter-clockwise from top-left (west 1-16, south 17-32, east 33-48, north 49-64).

| Pin | Side | Signal | Pad cell |
|---:|---|---|---|
| 1 | west | IOVSS | IOPadIOVss |
| 2 | west | IOVDD | IOPadIOVdd |
| 3 | west | cam_reset | IOPadOut4mA |
| 4 | west | cam_pwdn | IOPadOut4mA |
| 5 | west | cam_scl | IOPadOut4mA |
| 6 | west | cam_sda | IOPadInOut4mA |
| 7 | west | VSS | IOPadVss |
| 8 | west | VDD | IOPadVdd |
| 9 | west | gpio_out0 | IOPadOut4mA |
| 10 | west | gpio_out1 | IOPadOut4mA |
| 11 | west | gpio_out2 | IOPadOut4mA |
| 12 | west | gpio_out3 | IOPadOut4mA |
| 13 | west | gpio_in0 | IOPadIn |
| 14 | west | gpio_in1 | IOPadIn |
| 15 | west | gpio_in2 | IOPadIn |
| 16 | west | gpio_in3 | IOPadIn |
| 17 | south | IOVSS | IOPadIOVss |
| 18 | south | IOVDD | IOPadIOVdd |
| 19 | south | hb_dq0 | IOPadInOut16mA |
| 20 | south | hb_dq1 | IOPadInOut16mA |
| 21 | south | hb_dq2 | IOPadInOut16mA |
| 22 | south | hb_dq3 | IOPadInOut16mA |
| 23 | south | VSS | IOPadVss |
| 24 | south | VDD | IOPadVdd |
| 25 | south | hb_rwds | IOPadInOut16mA |
| 26 | south | hb_ck | IOPadOut16mA |
| 27 | south | hb_dq4 | IOPadInOut16mA |
| 28 | south | hb_dq5 | IOPadInOut16mA |
| 29 | south | hb_dq6 | IOPadInOut16mA |
| 30 | south | hb_dq7 | IOPadInOut16mA |
| 31 | south | hb_csn0 | IOPadOut4mA |
| 32 | south | hb_resetn | IOPadOut4mA |
| 33 | east | IOVSS | IOPadIOVss |
| 34 | east | IOVDD | IOPadIOVdd |
| 35 | east | uart_tx | IOPadOut4mA |
| 36 | east | uart_rx | IOPadIn |
| 37 | east | spi_sclk | IOPadOut4mA |
| 38 | east | spi_mosi | IOPadOut4mA |
| 39 | east | VSS | IOPadVss |
| 40 | east | VDD | IOPadVdd |
| 41 | east | clk_x2 | IOPadIn |
| 42 | east | porst_n | IOPadIn |
| 43 | east | spi_miso | IOPadIn |
| 44 | east | spi_csn | IOPadOut4mA |
| 45 | east | jtag_tck | IOPadIn |
| 46 | east | jtag_tms | IOPadIn |
| 47 | east | jtag_tdi | IOPadIn |
| 48 | east | jtag_tdo | IOPadOut4mA |
| 49 | north | IOVSS | IOPadIOVss |
| 50 | north | IOVDD | IOPadIOVdd |
| 51 | north | cam_pclk | IOPadIn |
| 52 | north | cam_d0 | IOPadIn |
| 53 | north | cam_d1 | IOPadIn |
| 54 | north | cam_d2 | IOPadIn |
| 55 | north | VSS | IOPadVss |
| 56 | north | VDD | IOPadVdd |
| 57 | north | cam_d3 | IOPadIn |
| 58 | north | cam_d4 | IOPadIn |
| 59 | north | cam_d5 | IOPadIn |
| 60 | north | cam_d6 | IOPadIn |
| 61 | north | cam_d7 | IOPadIn |
| 62 | north | cam_vs | IOPadIn |
| 63 | north | cam_hs | IOPadIn |
| 64 | north | cam_mclk | IOPadOut4mA |
