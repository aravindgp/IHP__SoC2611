"""Debug probes for locating a firmware hang (not part of the regression).

    make -C HW/asic/cocotb FAST_UART=1 COCOTB_TEST_MODULES=test_debug SUITE_TIMEOUT_MS=5
"""
import cocotb
from cocotb.triggers import Timer, RisingEdge, FallingEdge, First
from cocotb.utils import get_sim_time
from test_fw import UartRx, reset, SUITE_TIMEOUT_MS, BIT_NS


def _v(sig):
    try:
        return f"{int(sig.value):#x}"
    except Exception:
        return str(sig.value)


@cocotb.test()
async def test_debug_uart_tx(dut):
    """After the banner: UART TX FIFO flags / head byte / TX state over time."""
    uart = UartRx(dut)
    cocotb.start_soon(uart.run())
    await reset(dut)
    soc = dut.dut.soc_i
    cpu = soc.cpu_inst.system_cpu
    # GHDL/VPI presents some instances oddly; find the UART by name and unwrap
    u = None
    for h in soc:
        if "uart" in h._name.lower():
            dut._log.info("child %s type %s", h._path, type(h).__name__)
            if type(h).__name__ == "HierarchyArrayObject":
                for sub in h:
                    dut._log.info("   sub %s type %s", sub._path, type(sub).__name__)
                    u = sub
            elif type(h).__name__ == "HierarchyObject":
                u = h
    assert u is not None, "UART instance not found"
    names = sorted(c._name for c in u)
    dut._log.info("UART children: %s", [n for n in names if "tx" in n.lower() or "fifo" in n.lower()][:30])
    await uart.wait_line(r"DGRID-SOC1 FW", SUITE_TIMEOUT_MS)

    def dump(tag):
        dut._log.info("%s @%.0f ns: tx=%s state=%s cnt=%s empty=%s full=%s wused=%s q=%s byte=%s | raddr_r=%s waddr_r=%s | pc=%s",
                      tag, get_sim_time("ns"), _v(dut.uart_tx_out), str(u.tx_state_r.value), _v(u.tx_clk_count_r),
                      _v(u.txfifo_empty), _v(u.txfifo_full), _v(u.txfifo_wused), _v(u.txfifo_q), _v(u.tx_byte_r),
                      _v(u.txfifo_i.raddr_r), _v(u.txfifo_i.waddr_r), _v(cpu.IBusCachedPlugin_fetchPc_pcReg))

    dump("banner")
    # independent bit-level decoder: log every byte for ~120 characters
    tx = dut.uart_tx_out
    chars = []
    for n in range(120):
        r = await First(FallingEdge(tx), Timer(40 * BIT_NS, unit="ns"))
        if isinstance(r, Timer) or r is None:
            dut._log.info("no start bit for 40 bit-times; stop")
            break
        t_start = get_sim_time("ns")
        await Timer(BIT_NS * 1.5, unit="ns")
        v = 0
        for i in range(8):
            v |= (int(tx.value) & 1) << i
            await Timer(BIT_NS, unit="ns")
        stop = int(tx.value)
        chars.append(chr(v) if 32 <= v < 127 else f"<{v:#04x}>")
        if n < 12 or stop != 1:
            dut._log.info("byte %d @%.0f ns = %#04x %r stop=%d  (monitor partial=%r)", n, t_start, v, chr(v), stop, uart.partial)
    dut._log.info("decoded: %s", "".join(chars))
    dump("end")
    dut._log.info("monitor lines: %s", uart.lines)
