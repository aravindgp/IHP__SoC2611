# SoC2611 memory map and register map

Sources of record in the design repository: `HW/src/ztachip_pkg.vhd` (APB offsets, accelerator
register numbers), `SW/src/soc.h` (APB word indices used by the firmware), `SW/base/zta.h` (accelerator host
registers), `HW/asic/fw/bootrom/boot.c` (boot ROM), `HW/asic/fw/smoke.c` (firmware suite). The firmware suite in
`SoC2611-main/verification/sim/cocotb_icg.log` exercises every register listed under "APB peripherals" and the
accelerator status registers (tests T01, T03, T04, T05, T06).

## 1. Address map (as seen by the RISC-V host, 32-bit)

| Base | Region | Notes |
|---|---|---|
| `0x0000_0000` | TCM, 4 KiB (one `RM_IHPSG13_2P_1024x32` macro, 1024 words of 32 bits) | Boot ROM image is copied into the TCM by hardware at power-up; reset vector `0x0000_0000`. Stack of the boot ROM. |
| `0x0000_4000` | Application entry (`APP_ENTRY`) in main memory | Main memory is the external HyperRAM behind the AXI HyperBus controller (one 8 MB device on CS#0). |
| `0x4000_0000` | Accelerator scratchpad SRAM, read port for the CPU data bus | Read only. A CPU write here is never accepted and stalls the CPU. Instruction fetches in this range go to main memory. |
| `0x8000_0000` | Accelerator (ztachip) host registers, `MEM_MAP` | Word addressed: register `(reg2 << 5) + reg`, see section 3. |
| `0xC000_0000` | APB peripherals | Byte offsets below, 8-bit APB address space (`apb_addr_len_c = 8`). |

Boot sequence: after `porst_n_in` releases, the CPU runs the boot ROM from the TCM. GPIO in[3] is the boot strap:
`1` = jump to the application image at `0x0000_4000` (already in HyperRAM, e.g. loaded by JTAG or a previous
session), `0` = UART loader (8N1 at the system clock divided by 1085, see section 2; prints `BOOT`, receives the
image, prints `GO`, jumps). The loader is verified in `verification/sim/cocotb_bootldr.log` (`BOOT -> GO -> HELLO`), a
run on the generic ASIC top with a DDR memory model, not on the chip top with the HyperBus controller.

Exceptions: the CPU's trap vector is a constant, `0x8000_0020`, which lies inside the accelerator register window,
and the CPU has no environment call (`ecall` does not trap). An illegal instruction, a misaligned access or any
other exception therefore jumps into the register window. The instruction bus has no route to addresses with bit 31
at 1, so that fetch is accepted but never answered and the CPU stalls; only reset or JTAG recovers. Firmware for this chip must
not raise exceptions and must not use `ecall`.

## 2. APB peripherals (base `0xC000_0000`, byte offset = 4 x firmware word index)

| Offset | Firmware name | R/W | Function |
|---|---|---|---|
| `0x00` | `APB_LED` | W | GPIO out: bits 3:0 LEDs, bit 4 `spi_csn`, bit 5 `spi_sclk`, bit 6 `spi_mosi` |
| `0x08` | `APB_PB` | R | GPIO in: bits 3:0 push buttons (bit 3 = boot strap), bit 4 `spi_miso` |
| `0x0C` | `APB_CAMERA_ENABLE` | W | camera write-DMA enable |
| `0x10` | `APB_CAMERA_CURR_FRAME` | R | index of the frame buffer being written |
| `0x14` .. `0x20` | `APB_CAMERA_BUFFER` + 0..3 | W | camera frame buffer addresses 0..3 |
| `0x24` | `APB_VIDEO_ENABLE` | W | video read-DMA enable; VGA output is disabled on this chip, so no slave answers `0x24` .. `0x38` and an access stalls the CPU |
| `0x28` | read-DMA current buffer | R | not present, see `0x24` |
| `0x2C` .. `0x38` | `APB_VIDEO_BUFFER` + 0..3 | W | not present, see `0x24` |
| `0x3C` | `APB_UART_READ` | R | UART receive data |
| `0x40` | `APB_UART_WRITE` | W | UART transmit data |
| `0x44` | `APB_UART_READ_AVAIL` | R | bit 0 = 1 when the receive FIFO is not empty |
| `0x48` | `APB_UART_WRITE_AVAIL` | R | bit 0 = 1 when the transmit FIFO is not full |
| `0x4C` | `APB_TIME_GET` | R | timer: counts once every 125,000 system clocks |
| `0x50` | `APB_TIME2_GET` | R | second counter: counts once every system clock |

Any offset not in this table, such as `0x04`, stalls the CPU: the APB bridge waits for a ready signal that no slave
gives.

UART: 8 data bits, no parity, 1 stop bit. The bit time is fixed at 1085 system clocks (the design constant assumes a
125 MHz system clock and 115,200 baud), so the bit rate is the system clock divided by 1085: 46,080 baud at a 50 MHz
system clock, about 27,100 baud at the slow-corner rating of 29.4 MHz. The timer counts once every 125,000 system
clocks, which is one millisecond only at 125 MHz (2.5 ms at 50 MHz). Firmware and host software must scale both to
the clock in use. There is no SPI controller in hardware: the firmware drives the SPI pins bit by bit through the
GPIO registers `APB_LED` and `APB_PB` (`soc.h`).

## 3. Accelerator host registers (base `0x8000_0000`)

Word address = `MEM_MAP + 4 x ((reg2 << 5) + reg)`, `reg2` = page, `reg` = register. The host side (`reg2 = 0`):

| reg | Name | R/W | Function |
|---|---|---|---|
| 0 | `REG_STATUS` | R | busy / sync flags |
| 1 | `REG_DDR_BAR` | W | main-memory base for accelerator transfers |
| 2 | `REG_READ_LOG` | R | log FIFO |
| 3 | `REG_READ_LOG_TIME` | R | log timestamp |
| 4 | `REG_LOOKUP_SET_COEF` | W | lookup-table coefficient |
| 5 | `REG_DP_RUN` | W | start a data-plane program |
| 6 | `REG_LOOKUP_SET_ADDR` | W | lookup-table address |
| 7 | `REG_LOOKUP_SET_VAL` | W | lookup-table value |
| 8 | `REG_DP_TEMPLATE` | W | data-plane template select |
| 10 | `REG_DP_READ_SYNC` | R | sync flag (test T06) |
| 11 | `REG_DP_READ_INDICATION` | R | indication FIFO |
| 12 | `REG_DP_READ_INDICATION_AVAIL` | R | indication FIFO level |
| 14 | `REG_DP_INSTRUCTION_FIFO_AVAIL` | R | instruction FIFO space (test T01 expects the full FIFO) |
| 15 | `REG_SOFT_RESET` | W | accelerator soft reset |
| 16 .. 19 | `REG_MSGQ_READ`, `_READ_AVAIL`, `_WRITE`, `_WRITE_AVAIL` | R/W | message queue to the PCORE programs |
| 20, 21 | `REG_SWDL_COMPLETE_READ`, `_CLEAR` | R/W | software download complete flag |
| 22 | `REG_DP_MAX_PCORE` | - | defined in `ztachip_pkg.vhd` and `zta.h`, not decoded by the hardware (the chip has 4 PCOREs); a read never returns and stalls the CPU (`SoC2611-main/docs/ASIC_PORT.md`) |
| 23 .. 25 | `REG_DP_INDICATION_PARM0/1`, `REG_DP_READ_INDICATION_PARM` | R | indication parameters |
| 26 .. 28, 31 | `REG_FPU_SET`, `REG_FPU_EXE`, `REG_FPU_GET_STATUS`, `REG_FPU_SET_MEM` | R/W | FP32 unit |

The data-plane control registers (`reg2 = 1, 2`: transfer base, stride, burst, fork count, buffer size, ...) are
listed with their numbers in `HW/src/ztachip_pkg.vhd` (`register_dp_*_c`, `register2_dp_*_c`) and are written only
by the accelerator runtime (`SW/base/`), not by application code.

## 4. Configuration of this chip

RV32IM VexRiscv (8 KiB I-cache 2-way, 8 KiB D-cache, JTAG debug TAP), ztachip with 1 cell x 4 PCOREs = 4 PCOREs,
16 threads per PCORE, 12-bit data path, camera input enabled, VGA output disabled, main memory HyperRAM, 298
RM_IHPSG13 SRAM macros (214 KiB). Generics: `SoC2611-main/docs/ASIC_PORT.md` section 4.
