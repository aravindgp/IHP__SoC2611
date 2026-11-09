# SoC2611 memory map and register map

Sources of record in the design repository: `HW/src/ztachip_pkg.vhd` (APB offsets, accelerator
register numbers), `SW/src/soc.h` (APB word indices used by the firmware), `SW/base/zta.h` (accelerator host
registers), `HW/asic/fw/bootrom/boot.c` (boot ROM), `HW/asic/fw/smoke.c` (firmware suite). The firmware suite in
`SoC2611-main/verification/sim/cocotb_icg.log` exercises every register listed under "APB peripherals" and the
accelerator status registers (tests T01, T03, T04, T05, T06).

## 1. Address map (as seen by the RISC-V host, 32-bit)

| Base | Region | Notes |
|---|---|---|
| `0x0000_0000` | TCM, 16 KiB (`DPRAM 32x4096`) | Boot ROM image is copied into the TCM by hardware at power-up; reset vector `0x0000_0000`. Stack of the boot ROM. |
| `0x0000_4000` | Application entry (`APP_ENTRY`) in main memory | Main memory is the external HyperRAM behind the AXI HyperBus controller (one 8 MB device on CS#0). |
| `0x8000_0000` | Accelerator (ztachip) host registers, `MEM_MAP` | Word addressed: register `(reg2 << 5) + reg`, see section 3. |
| `0xC000_0000` | APB peripherals | Byte offsets below, 8-bit APB address space (`apb_addr_len_c = 8`). |

Boot sequence: after `porst_n_in` releases, the CPU runs the boot ROM from the TCM. GPIO in[3] is the boot strap:
`1` = jump to the application image at `0x0000_4000` (already in HyperRAM, e.g. loaded by JTAG or a previous
session), `0` = UART loader (115200 8N1, prints `BOOT`, receives the image, prints `GO`, jumps). The loader is
verified in `verification/sim/cocotb_bootldr.log` (`BOOT -> GO -> HELLO`).

## 2. APB peripherals (base `0xC000_0000`, byte offset = 4 x firmware word index)

| Offset | Firmware name | R/W | Function |
|---|---|---|---|
| `0x00` | `APB_LED` | W | GPIO out[3:0] (LEDs) |
| `0x08` | `APB_PB` | R | GPIO in[3:0] (push buttons; bit 3 = boot strap) |
| `0x0C` | `APB_CAMERA_ENABLE` | W | camera write-DMA enable |
| `0x10` | `APB_CAMERA_CURR_FRAME` | R | index of the frame buffer being written |
| `0x14` .. `0x20` | `APB_CAMERA_BUFFER` + 0..3 | W | camera frame buffer addresses 0..3 |
| `0x24` | `APB_VIDEO_ENABLE` | W | video read-DMA enable (VGA output not bonded on this chip) |
| `0x28` | read-DMA current buffer | R | |
| `0x2C` .. `0x38` | `APB_VIDEO_BUFFER` + 0..3 | W | video buffer addresses 0..3 |
| `0x3C` | `APB_UART_READ` | R | UART receive data |
| `0x40` | `APB_UART_WRITE` | W | UART transmit data |
| `0x44` | `APB_UART_READ_AVAIL` | R | receive bytes available |
| `0x48` | `APB_UART_WRITE_AVAIL` | R | transmit space available |
| `0x4C` | `APB_TIME_GET` | R | timer, low word |
| `0x50` | `APB_TIME2_GET` | R | timer, high word |

UART: fixed 115200 baud, 8 data bits, no parity, 1 stop bit, from the 50 MHz core clock. The SPI master and the
remaining GPIO are driven by the firmware through the same APB slave (`soc.h`).

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
| 22 | `REG_DP_MAX_PCORE` | R | number of PCOREs (8 in this configuration) |
| 23 .. 25 | `REG_DP_INDICATION_PARM0/1`, `REG_DP_READ_INDICATION_PARM` | R | indication parameters |
| 26 .. 28, 31 | `REG_FPU_SET`, `REG_FPU_EXE`, `REG_FPU_GET_STATUS`, `REG_FPU_SET_MEM` | R/W | FP32 unit |

The data-plane control registers (`reg2 = 1, 2`: transfer base, stride, burst, fork count, buffer size, ...) are
listed with their numbers in `HW/src/ztachip_pkg.vhd` (`register_dp_*_c`, `register2_dp_*_c`) and are written only
by the accelerator runtime (`SW/base/`), not by application code.

## 4. Configuration of this chip

RV32IM VexRiscv (8 KiB I-cache 2-way, 8 KiB D-cache, JTAG debug TAP), ztachip with 2 cells x 4 PCOREs = 8 PCOREs,
16 threads per PCORE, 12-bit data path, camera input enabled, VGA output disabled, main memory HyperRAM, 298
RM_IHPSG13 SRAM macros (214 KiB). Generics: `SoC2611-main/docs/ASIC_PORT.md` section 4.
