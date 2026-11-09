"""cocotb firmware-level tests for dgrid_soc1_asic_top.

DUT: HW/asic/tb/tb_dgrid_soc1_fw.vhd (ASIC top + DDR model preloaded with
HW/asic/fw/<FW>.hex). The firmware prints one line per test over the UART:

    Tnn name PASS|FAIL key=value ...
    SUMMARY pass=<n> fail=<n>

This module drives reset / push-buttons / UART RX, decodes UART TX, watches
the LEDs, and turns the firmware's verdicts into cocotb assertions.

Run:  make -C HW/asic/cocotb           (see the Makefile for knobs)
"""
import os
import re

import cocotb
from cocotb.triggers import Timer, Edge, FallingEdge, First, with_timeout

# UART timing: BAUD 115200 (soc_base) at main_clock_c (HW/asic/rtl/config.vhd)
MAIN_CLOCK_HZ = int(os.environ.get("MAIN_CLOCK_HZ", "125000000"))
CLK_MAIN_NS = float(os.environ.get("CLK_MAIN_NS", "8"))        # 2 x CLK_X2_PERIOD
TICKS_PER_BIT = MAIN_CLOCK_HZ // 115200
BIT_NS = TICKS_PER_BIT * CLK_MAIN_NS
# ~300 UART characters at 86.8 us each + boot; FAST_UART=1 builds cut this 10x
SUITE_TIMEOUT_MS = float(os.environ.get("SUITE_TIMEOUT_MS", "120"))
DP_FIFO_MAX = int(os.environ.get("DP_FIFO_MAX", "127"))   # 2**dp_instr_fifo_depth_c-1 (63 ASIC lean); proves the host bus reaches the accelerator

RESULT_RE = re.compile(r"^(T\d\d) (\S+) (PASS|FAIL)(.*)$")


class UartRx:
    """8N1 receiver on dut.uart_tx_out; collects complete lines."""

    def __init__(self, dut):
        self.dut = dut
        self.lines = []
        self.partial = ""
        self.new_line = cocotb.triggers.Event()

    async def run(self):
        tx = self.dut.uart_tx_out
        while True:
            await FallingEdge(tx)                 # start bit
            await Timer(BIT_NS * 1.5, unit="ns")  # middle of bit 0
            v = 0
            for i in range(8):
                v |= (int(tx.value) & 1) << i
                await Timer(BIT_NS, unit="ns")
            # now in the stop bit
            c = chr(v)
            if c == "\n":
                line = self.partial.rstrip("\r")
                self.partial = ""
                if line:
                    self.lines.append(line)
                    self.dut._log.info("UART| %s", line)
                    self.new_line.set()
                    self.new_line.clear()
            else:
                self.partial += c

    async def wait_line(self, pattern, timeout_ms):
        """Return the first line matching `pattern` (regex), waiting up to timeout."""
        rx = re.compile(pattern)
        seen = 0
        async def waiter():
            nonlocal seen
            while True:
                for line in self.lines[seen:]:
                    seen += 1
                    if rx.search(line):
                        return line
                await self.new_line.wait()
        return await with_timeout(waiter(), timeout_ms, "ms")


async def uart_send(dut, byte: int):
    rx = dut.uart_rx_in
    rx.value = 0
    await Timer(BIT_NS, unit="ns")
    for i in range(8):
        rx.value = (byte >> i) & 1
        await Timer(BIT_NS, unit="ns")
    rx.value = 1
    await Timer(BIT_NS, unit="ns")


class LedMonitor:
    def __init__(self, dut):
        self.dut = dut
        self.seq = []

    async def run(self):
        while True:
            await Edge(self.dut.gpio_out)
            v = int(self.dut.gpio_out.value)
            if not self.seq or self.seq[-1] != v:
                self.seq.append(v)


async def reset(dut):
    dut.porst_n_in.value = 0
    dut.uart_rx_in.value = 1
    dut.gpio_in.value = 0x9
    await Timer(1, unit="us")
    dut.porst_n_in.value = 1
    dut._log.info("reset released (UART bit = %.0f ns, %d clk_main ticks)", BIT_NS, TICKS_PER_BIT)


@cocotb.test()
async def test_firmware_suite(dut):
    """Boot the firmware from the DDR model and check every Tnn verdict."""
    uart = UartRx(dut)
    leds = LedMonitor(dut)
    cocotb.start_soon(uart.run())
    cocotb.start_soon(leds.run())
    await reset(dut)

    banner = await uart.wait_line(r"DGRID-SOC1 FW", SUITE_TIMEOUT_MS)
    dut._log.info("boot banner received: %s", banner)

    # T05 handshake: firmware asks, we send 'K'
    async def responder():
        await uart.wait_line(r"^T05 uart_rx WAIT", SUITE_TIMEOUT_MS)
        await Timer(2 * BIT_NS, unit="ns")
        await uart_send(dut, ord("K"))
    cocotb.start_soon(responder())

    summary = await uart.wait_line(r"^SUMMARY", SUITE_TIMEOUT_MS)
    m = re.match(r"SUMMARY pass=(\d+) fail=(\d+)", summary)
    assert m, f"malformed summary: {summary}"
    npass, nfail = int(m.group(1)), int(m.group(2))

    results = {}
    for line in uart.lines:
        r = RESULT_RE.match(line)
        if r:
            kvs = dict(re.findall(r"(\w+)=(0x[0-9a-fA-F]+|\d+)", r.group(4)))
            results[r.group(1)] = (r.group(2), r.group(3), kvs)
            dut._log.info("%s %-10s %s %s", r.group(1), r.group(2), r.group(3), kvs)

    failures = [f"{k} {v[0]}" for k, v in results.items() if v[1] != "PASS"]
    assert len(results) == 6, f"expected 6 test lines, got {len(results)}: {sorted(results)}"
    assert not failures, f"firmware reported failures: {failures}"
    assert nfail == 0 and npass == 6, f"summary pass={npass} fail={nfail}"

    # cross-checks from the testbench side
    fifo = int(results["T01"][2]["fifo_avail"], 16)
    assert fifo == DP_FIFO_MAX, f"accelerator FIFO depth {fifo} != {DP_FIFO_MAX}"
    walk = [1, 2, 4, 8, 0xA]
    seq = leds.seq
    if seq and seq[0] == 0:
        seq = seq[1:]            # the reset value itself is also recorded as a change
    assert seq[:1] == [0x5], f"LED after boot should be 0x5, saw {seq[:3]}"
    idx = [seq.index(v) for v in walk if v in seq]
    assert len(idx) == len(walk) and idx == sorted(idx), f"LED walk {walk} not seen in order: {seq}"
    assert seq[-1] == 0x0, f"final LED value should be 0 (no failures), saw {seq[-1]:#x}"
    dut._log.info("firmware suite: %d/%d PASS, LED sequence %s", npass, npass + nfail,
                  [hex(v) for v in seq])
    # HyperRAM harness (tb_dgrid_soc1_hb): the device models latch any protocol/timing violation
    if hasattr(dut, "hb_error_out"):
        hb_err = int(dut.hb_error_out.value)
        assert hb_err == 0, f"HyperRAM device model flagged a protocol/timing error (hb_error_out={hb_err:#x}); see 'report error' lines"
        dut._log.info("HyperRAM device models: no protocol/timing error")
