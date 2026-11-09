# Functional simulation results (RTL, typical case)

All runs: GHDL + cocotb on the design repository, 31 Oct 2026, with the IHP SRAM macro models and
the JTAG VexRiscv core, i.e. the configuration that was synthesised. Testbench sources: `../../testbenches/`.

| Log | Testbench | What it proves | Result |
|---|---|---|---|
| `cocotb_icg.log` | `tb_soc2611_hb` (chip top, HyperRAM model, ICG clock gating) | firmware suite T01-T06: CPU boots through the AXI fabric, main-memory path (LFSR word / half-word / byte writes), APB write and read (LEDs, buttons), timer, UART receive, accelerator status registers | **6/6 PASS**, 3.6 ms simulated |
| `cocotb_results.xml` | same | JUnit record of the suite | 1 test, 0 failures |
| `cocotb_bootldr.log` | `tb_soc2611_fw` | boot ROM from the TCM: `BOOT`, image received over UART, `GO`, application prints `HELLO`, LEDs 0xA | **PASS** |
| `hb_check2.log` | `tb_hyperbus` | HyperBus controller unit tests (single and burst read/write, RWDS latency, register access) | **6/6 PASS** |
| `tb_ihp_mem6.log` | `tb_ihp_mem_equiv` | every IHP SRAM macro wrapper against its behavioural reference model, including the dual-clock DPRAM | **37 pairs PASS** |

Pass criteria per test (from `SoC2611-main/docs/ASIC_PORT.md` section 7):

| ID | test | pass criterion |
|---|---|---|
| T01 | `ident` | accelerator instruction FIFO reports full (0x3f) and no indication pending |
| T02 | `ddr` | 0 mismatches on the external-memory pattern |
| T03 | `gpio` | LED walk 1, 2, 4, 8, 0xA observed; buttons read back 0x9 |
| T04 | `timer` | both timer words advance |
| T05 | `uart_rx` | the byte sent by the testbench (`'K'`) is received |
| T06 | `zta_status` | sync and log registers read 0 |

Not yet run: gate-level simulation of the post-route netlist, multi-corner STA, post-layout simulation. They are
part of the final release.
