"""Harness speed probe (not part of the regression): how fast does the SoC simulate under cocotb?
    make FAST_UART=1 COCOTB_TEST_MODULES=test_speed [SPEED_MONITORS=1] [SPEED_US=100]
Phase A: reset, then a pure Timer wait (no value-change callbacks).
Phase B (SPEED_MONITORS=1): the same wait with the UART/LED monitors of test_fw running.
Prints simulated-us per wall-second for each phase.
"""
import os, time
import cocotb
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time
from test_fw import UartRx, LedMonitor, reset

SPEED_US = int(os.environ.get("SPEED_US", "100"))

@cocotb.test()
async def test_speed(dut):
    await reset(dut)
    t0 = time.time(); s0 = get_sim_time("us")
    await Timer(SPEED_US, unit="us")
    w = time.time() - t0
    dut._log.info("phase A (no monitors): %.0f us simulated in %.1f s wall = %.2f us/s", get_sim_time("us") - s0, w, (get_sim_time("us") - s0) / max(w, 1e-9))
    dut._log.info("uart_tx_out=%s gpio_out=%s", str(dut.uart_tx_out.value), str(dut.gpio_out.value))
    if os.environ.get("SPEED_MONITORS", "0") == "1":
        uart = UartRx(dut); cocotb.start_soon(uart.run())
        leds = LedMonitor(dut); cocotb.start_soon(leds.run())
        t0 = time.time(); s0 = get_sim_time("us")
        await Timer(SPEED_US, unit="us")
        w = time.time() - t0
        dut._log.info("phase B (with monitors): %.0f us simulated in %.1f s wall = %.2f us/s; uart lines=%s leds=%s",
                      get_sim_time("us") - s0, w, (get_sim_time("us") - s0) / max(w, 1e-9), uart.lines[:3], getattr(leds, "seq", None))
