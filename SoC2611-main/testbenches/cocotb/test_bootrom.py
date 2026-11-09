"""Boot ROM / UART loader test (ASIC build: reset vector 0 -> TCM boot ROM).
    make FAST_UART=1 COCOTB_TEST_MODULES=test_bootrom [CHIP=hb] [MEM=ihp]
Strap low (pushbutton bit 3 = 0): the ROM prints BOOT and waits for "DGB1" addr len data sum32;
we send HW/asic/fw/build/hello.bin to 0x4000, expect GO then HELLO from the payload and LEDs 0xA.
"""
import os
import cocotb
from cocotb.triggers import Timer, RisingEdge, First
from test_fw import UartRx, uart_send, BIT_NS

HELLO_BIN = os.path.join(os.path.dirname(__file__), "..", "fw", "build", "hello.bin")
LOAD_ADDR = 0x00004000
TIMEOUT_MS = int(os.environ.get("BOOT_TIMEOUT_MS", "40"))

async def wait_line(dut, uart, prefix, deadline_ns):
    while True:
        for l in uart.lines:
            if l.startswith(prefix): return l
        if cocotb.utils.get_sim_time("ns") > deadline_ns:
            raise AssertionError(f"no '{prefix}' line before {deadline_ns/1e6:.1f} ms; got {uart.lines}")
        await Timer(20 * BIT_NS, unit="ns")

async def send_bytes(dut, data):
    for b in data:
        await uart_send(dut, b)

@cocotb.test()
async def test_bootrom_uart_load(dut):
    uart = UartRx(dut); cocotb.start_soon(uart.run())
    dut.porst_n_in.value = 0
    dut.uart_rx_in.value = 1
    dut.gpio_in.value = 0x1            # strap bit 3 low -> UART loader
    await Timer(1000, unit="ns")
    dut.porst_n_in.value = 1
    dut._log.info("reset released, strap = loader")
    deadline = cocotb.utils.get_sim_time("ns") + TIMEOUT_MS * 1e6
    await wait_line(dut, uart, "BOOT", deadline)
    dut._log.info("boot ROM alive (BOOT)")
    img = open(HELLO_BIN, "rb").read()
    hdr = b"DGB1" + LOAD_ADDR.to_bytes(4, "little") + len(img).to_bytes(4, "little")
    await send_bytes(dut, hdr)
    await send_bytes(dut, img)
    await send_bytes(dut, (sum(img) & 0xffffffff).to_bytes(4, "little"))
    dut._log.info("sent %d bytes to %#x", len(img), LOAD_ADDR)
    await wait_line(dut, uart, "GO", deadline)
    await wait_line(dut, uart, "HELLO", deadline)
    # LEDs 0xA from the payload
    t_end = cocotb.utils.get_sim_time("ns") + 2000 * BIT_NS
    while int(dut.gpio_out.value) != 0xA:
        assert cocotb.utils.get_sim_time("ns") < t_end, f"LEDs {int(dut.gpio_out.value):#x} != 0xa after HELLO"
        await Timer(10 * BIT_NS, unit="ns")
    dut._log.info("boot ROM UART loader: BOOT -> GO -> HELLO, LEDs 0xA : PASS")
    if hasattr(dut, "hb_error_out"):
        assert int(dut.hb_error_out.value) == 0, "HyperRAM device model flagged an error"
