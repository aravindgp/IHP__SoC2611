# Testbenches

Copied from the design repository (DGrid-SoC1, `HW/asic/tb`, `HW/asic/cocotb`, `HW/asic/scripts`). They run on
the RTL in the design repository (VHDL sources plus the generated VexRiscv core); this folder documents what was
run and how. Results: `../verification/sim/`.

## VHDL testbenches (`vhdl/`)

| File | Device under test | Purpose |
|---|---|---|
| `tb_dgrid_soc1_hb.vhd` | `dgrid_soc1_chip_top` (= SoC2611) | chip top with the HyperRAM model (`hyperram_model.vhd`); firmware suite and boot loader run on it |
| `tb_dgrid_soc1_fw.vhd` | `dgrid_soc1_asic_top` | ASIC top with a DDR model; earlier firmware-suite runs |
| `tb_hyperbus.vhd` | HyperBus controller | AXI to HyperBus unit tests |
| `tb_ihp_mem_equiv.vhd` | IHP SRAM macro wrappers | each wrapper against its reference model (`run.log`: pairs PASS) |
| `tb_ramw_equiv.vhd` | memory wrapper | wrapper equivalence |
| `tb_fp32.vhd` + `vectors/fp32_vectors.txt` | FP32 unit | 134,937 vectors |
| `tb_ihp_plan.vhd`, `tb_speed.vhd` | memory plan, speed path | planning / timing checks |
| `config_sim.vhd` | | simulation configuration |

## cocotb drivers (`cocotb/`)

| File | Test | Expected output |
|---|---|---|
| `test_fw.py` | firmware suite T01-T06 on the chip top | `firmware suite: 6/6 PASS`, LED sequence 0x5, 0x1, 0x2, 0x4, 0x8, 0xA, 0 |
| `test_bootrom.py` | boot ROM UART loader | `BOOT -> GO -> HELLO, LEDs 0xA : PASS` |
| `test_hyperbus.py` | HyperBus controller | `TESTS=6 PASS=6` |
| `test_debug.py` | JTAG debug TAP: halt, memory access, resume | pass |
| `test_speed.py` | speed path | pass |

## How to run (design repository root)

```sh
# firmware suite on the chip top with HyperRAM and IHP macro models (the result in verification/sim/cocotb_icg.log)
make -C HW/asic/cocotb CHIP=hb MEM=ihp FAST_UART=1
# boot ROM UART loader
make -C HW/asic/cocotb -f Makefile TEST=test_bootrom
# HyperBus controller unit tests
make -C HW/asic/cocotb -f Makefile.hyperbus
# IHP SRAM wrapper equivalence, memory wrapper, FP32
HW/asic/scripts/run_tb_ihp_mem.sh ; HW/asic/scripts/run_tb_ramw.sh ; HW/asic/scripts/run_tb_fp32.sh
# GHDL analyse / elaborate gate for the whole ASIC RTL
HW/asic/scripts/analyze.sh
```

Requirements: GHDL with the mcode or LLVM backend, cocotb 1.9, Python 3.10+, RISC-V GCC for the firmware
(`HW/asic/fw/`). Each run prints a one-line PASS/FAIL summary and writes `results.xml`.
