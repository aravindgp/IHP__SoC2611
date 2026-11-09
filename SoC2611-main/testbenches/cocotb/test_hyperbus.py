"""cocotb unit test for the HyperBus (HyperRAM) controller.

DUT: HW/asic/tb/tb_hyperbus.vhd = hyperbus_axi (CS_COUNT=2, 128-byte chunks,
POWERUP_CYCLES=200) + two hyperram_model devices (8 MB each, tVCS scaled
down). A small self-contained AXI4 master drives the controller's slave
port; every access is scoreboarded against a Python shadow of the 16 MB
address space; the models' sticky error flags (tCSM / tVCS / tRP / protocol)
are checked after every test.

Run:  make -C HW/asic/cocotb -f Makefile.hyperbus
      knobs: HB_SEED, HB_BURSTS, HB_RREADY (rready probability), HB_WGAP (W bubble
      probability; >= 0.9 forces write chunks to be split on data underrun);
      SIM_ARGS="-gFIXED_LATENCY=false --ieee-asserts=disable" exercises the
      RWDS-sampled 1x/2x latency path.
"""
import os
import random

import cocotb
from cocotb.triggers import RisingEdge, Timer

MEM_BYTES = 2 * 8 * 1024 * 1024          # two devices
BEAT_BYTES = 16
POWERUP_CYCLES = 200
MAX_CS_BYTES = 128
SEED = int(os.environ.get("HB_SEED", "1"))
N_BURSTS = int(os.environ.get("HB_BURSTS", "200"))
RREADY_PROB = float(os.environ.get("HB_RREADY", "0.7"))   # R channel back-pressure
WGAP_PROB = float(os.environ.get("HB_WGAP", "0.2"))       # W channel bubbles (0.9+ forces chunk splits)

shadow = bytearray(MEM_BYTES)
stats = {"writes": 0, "reads": 0, "wbytes": 0, "rbytes": 0, "beats": 0}
_reset_done = False


def u(sig):
    """signal value as unsigned int (cocotb 2.x LogicArray / Logic)."""
    v = sig.value
    try:
        return v.to_unsigned()
    except AttributeError:
        return int(v)


def align(a, n):
    return a & ~(n - 1)


class AxiMaster:
    """Minimal AXI4 master: one write or read burst at a time, random R back-pressure."""

    def __init__(self, dut, rng, rready_prob=0.7, w_gap_prob=0.2):
        self.dut = dut
        self.rng = rng
        self.rready_prob = rready_prob
        self.w_gap_prob = w_gap_prob
        self.clk = dut.clk_out
        d = dut
        for s in (d.axi_arvalid_in, d.axi_awvalid_in, d.axi_wvalid_in,
                  d.axi_rready_in, d.axi_bready_in, d.axi_wlast_in):
            s.value = 0
        d.axi_araddr_in.value = 0
        d.axi_arlen_in.value = 0
        d.axi_arsize_in.value = 0
        d.axi_arburst_in.value = 1
        d.axi_awaddr_in.value = 0
        d.axi_awlen_in.value = 0
        d.axi_awsize_in.value = 0
        d.axi_awburst_in.value = 1
        d.axi_wdata_in.value = 0
        d.axi_wstrb_in.value = 0

    async def _edge(self):
        await RisingEdge(self.clk)

    async def write(self, addr, size, beats, timeout=20000):
        """beats: list of (data_int128, strb_int16). Returns after BVALID."""
        d = self.dut
        n = len(beats)
        d.axi_awaddr_in.value = addr
        d.axi_awlen_in.value = n - 1
        d.axi_awsize_in.value = size
        d.axi_awvalid_in.value = 1
        aw_done = False
        i = 0
        w_on = False
        cycles = 0
        while not (aw_done and i == n):
            if not w_on and i < n and self.rng.random() >= self.w_gap_prob:
                data, strb = beats[i]
                d.axi_wdata_in.value = data
                d.axi_wstrb_in.value = strb
                d.axi_wlast_in.value = 1 if i == n - 1 else 0
                d.axi_wvalid_in.value = 1
                w_on = True
            await self._edge()
            cycles += 1
            assert cycles < timeout, "write burst timeout (addr=0x%x)" % addr
            if not aw_done and u(d.axi_awready_out) == 1:
                aw_done = True
                d.axi_awvalid_in.value = 0
            if w_on and u(d.axi_wready_out) == 1:
                i += 1
                w_on = False
                d.axi_wvalid_in.value = 0
                d.axi_wlast_in.value = 0
        d.axi_bready_in.value = 1
        while True:
            await self._edge()
            cycles += 1
            assert cycles < timeout, "BVALID timeout (addr=0x%x)" % addr
            if u(d.axi_bvalid_out) == 1:
                assert u(d.axi_bresp_out) == 0, "BRESP != OKAY"
                break
        d.axi_bready_in.value = 0
        stats["writes"] += 1
        stats["beats"] += n

    async def read(self, addr, size, n, timeout=20000):
        """Returns the list of n 128-bit beats."""
        d = self.dut
        d.axi_araddr_in.value = addr
        d.axi_arlen_in.value = n - 1
        d.axi_arsize_in.value = size
        d.axi_arvalid_in.value = 1
        beats = []
        ar_done = False
        cycles = 0
        rready = 0
        while len(beats) < n:
            await self._edge()
            cycles += 1
            assert cycles < timeout, "read burst timeout (addr=0x%x)" % addr
            if not ar_done and u(d.axi_arready_out) == 1:
                ar_done = True
                d.axi_arvalid_in.value = 0
            if rready and u(d.axi_rvalid_out) == 1:
                beats.append(u(d.axi_rdata_out))
                assert u(d.axi_rresp_out) == 0, "RRESP != OKAY"
                last = u(d.axi_rlast_out)
                assert last == (1 if len(beats) == n else 0), \
                    "RLAST mismatch at beat %d of %d" % (len(beats), n)
            rready = 1 if self.rng.random() < self.rready_prob else 0
            d.axi_rready_in.value = rready
        d.axi_rready_in.value = 0
        stats["reads"] += 1
        stats["beats"] += n
        return beats


# ---------------------------------------------------------------------------
# scoreboard helpers
# ---------------------------------------------------------------------------

def beat_addr(addr, size, i):
    nb = 1 << size
    return addr if i == 0 else align(addr, nb) + i * nb


def valid_lanes(addr, size, i):
    """lane mask of the bytes an INCR beat may touch."""
    nb = 1 << size
    a = beat_addr(addr, size, i)
    lo = a % BEAT_BYTES
    hi = (align(a, nb) % BEAT_BYTES) + nb - 1
    m = 0
    for b in range(lo, hi + 1):
        m |= 1 << b
    return m


def gen_write(rng, addr, size, n, sparse=False):
    beats = []
    for i in range(n):
        data = rng.getrandbits(128)
        strb = valid_lanes(addr, size, i)
        if sparse:
            strb &= rng.getrandbits(16)
        beats.append((data, strb))
    return beats


def apply_write(addr, size, beats):
    for i, (data, strb) in enumerate(beats):
        base = align(beat_addr(addr, size, i), BEAT_BYTES) % MEM_BYTES
        for b in range(BEAT_BYTES):
            if strb >> b & 1:
                shadow[base + b] = (data >> (8 * b)) & 0xFF
                stats["wbytes"] += 1


def expect_read(addr, size, n):
    exp = []
    for i in range(n):
        base = align(beat_addr(addr, size, i), BEAT_BYTES) % MEM_BYTES
        exp.append(int.from_bytes(shadow[base:base + BEAT_BYTES], "little"))
    return exp


async def check_read(m, addr, size, n):
    got = await m.read(addr, size, n)
    exp = expect_read(addr, size, n)
    stats["rbytes"] += n * BEAT_BYTES
    for i, (g, e) in enumerate(zip(got, exp)):
        assert g == e, "read mismatch addr=0x%x size=%d beat %d/%d: got %032x exp %032x" % (
            addr, size, i, n, g, e)


async def check_models(dut):
    err = u(dut.model_error_out)
    assert err == 0, "hyperram_model error flag(s) set: 0b%02b" % err
    # GHDL 1.0 ignores vpiFinish when it is issued from a value-change
    # callback (a test ending on RisingEdge leaves the simulator running
    # forever); ending every test on a timer callback makes the exit work.
    await Timer(1, unit="ns")


async def setup(dut):
    """reset once, wait for the controller's power-up sequence."""
    global _reset_done
    rng = random.Random(SEED)
    m = AxiMaster(dut, rng, rready_prob=RREADY_PROB, w_gap_prob=WGAP_PROB)
    if not _reset_done:
        dut.reset_n_in.value = 0
        await Timer(100, unit="ns")
        dut.reset_n_in.value = 1
        # RESET# low for POWERUP_CYCLES/4, AXI accepted after POWERUP_CYCLES
        for _ in range(POWERUP_CYCLES + 20):
            await RisingEdge(dut.clk_out)
        assert u(dut.hb_resetn_out) == 1, "hb_resetn_out should be high after power-up"
        assert u(dut.hb_csn_out) == 3, "CS# must be idle high"
        _reset_done = True
    return m, rng


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

@cocotb.test()
async def test_single_word(dut):
    """(a) one 16-byte write then read, device 0 and device 1."""
    m, rng = await setup(dut)
    for addr in (0x000100, 0x800100, 0x7FFFF0, 0xFFFFF0):
        beats = gen_write(rng, addr, 4, 1)
        await m.write(addr, 4, beats)
        apply_write(addr, 4, beats)
        await check_read(m, addr, 4, 1)
    await check_models(dut)


@cocotb.test()
async def test_narrow_writes(dut):
    """(b) sizes 0..3 with strobes (single beats and short bursts), read back."""
    m, rng = await setup(dut)
    for size in (0, 1, 2, 3):
        for _ in range(12):
            nb = 1 << size
            n = rng.randint(1, 8)
            addr = rng.randrange(0, MEM_BYTES)
            # no 4 KB crossing
            if (addr & 0xFFF) + n * nb > 0x1000:
                addr = align(addr, 0x1000)
            beats = gen_write(rng, addr, size, n, sparse=rng.random() < 0.5)
            await m.write(addr, size, beats)
            apply_write(addr, size, beats)
            await check_read(m, addr, size, n)
            # the neighbouring bytes must be intact: read the full words as size 4
            w0 = align(addr, BEAT_BYTES)
            await check_read(m, w0, 4, 2 if w0 + 32 <= MEM_BYTES else 1)
    await check_models(dut)


@cocotb.test()
async def test_back_to_back_64(dut):
    """(d) 64-beat write immediately followed by a 64-beat read at the same address."""
    m, rng = await setup(dut)
    for addr in (0x001000, 0x7FFC00, 0x9ABCD0):
        beats = gen_write(rng, addr, 4, 64)
        await m.write(addr, 4, beats)
        apply_write(addr, 4, beats)
        await check_read(m, addr, 4, 64)
    await check_models(dut)


@cocotb.test()
async def test_device_boundary(dut):
    """bursts crossing the 8 MB device boundary (chunks are 128-byte aligned, so each
    side goes to its own CS#) and the top-of-memory wrap."""
    m, rng = await setup(dut)
    for addr, n in ((0x7FFF00, 32), (0x7FFFF0, 2), (0x7FFE80, 64), (0xFFFF00, 16)):
        beats = gen_write(rng, addr, 4, n)
        await m.write(addr, 4, beats)
        apply_write(addr, 4, beats)
        await check_read(m, addr, 4, n)
    # words on both sides
    await check_read(m, 0x7FFE00, 4, 64)
    await check_models(dut)


@cocotb.test()
async def test_random_bursts(dut):
    """(c) HB_BURSTS random INCR bursts (1..64 beats, random size, random address in
    both devices, crossing MAX_CS_BYTES windows), read/write mix, scoreboarded."""
    m, rng = await setup(dut)
    hot = [rng.randrange(0, MEM_BYTES) for _ in range(8)]   # re-used regions -> read-after-write
    for k in range(N_BURSTS):
        size = rng.choice([4, 4, 4, 4, 2, 0, 1, 3])
        nb = 1 << size
        if size == 4:
            n = rng.choice([1, 2, 3, 7, 8, 9, 16, 17, 31, 32, 33, 63, 64, rng.randint(1, 64)])
        else:
            n = rng.randint(1, 8)
        if rng.random() < 0.6:
            addr = (rng.choice(hot) + rng.randrange(0, 2048)) % MEM_BYTES
        else:
            addr = rng.randrange(0, MEM_BYTES)
        if rng.random() < 0.3:
            addr = align(addr, MAX_CS_BYTES) - rng.choice([16, 32, 48])   # straddle a window
            addr %= MEM_BYTES
        if (addr & 0xFFF) + n * nb > 0x1000:
            addr = align(addr, 0x1000) + rng.randrange(0, 0x1000 - n * nb + 1)
            if size == 4:
                addr = align(addr, 16)
        addr %= MEM_BYTES
        if rng.random() < 0.5:
            beats = gen_write(rng, addr, size, n, sparse=rng.random() < 0.3)
            await m.write(addr, size, beats)
            apply_write(addr, size, beats)
        else:
            await check_read(m, addr, size, n)
        if k % 50 == 49:
            dut._log.info("random bursts: %d/%d done", k + 1, N_BURSTS)
    await check_models(dut)
    dut._log.info("STATS writes=%d reads=%d beats=%d wbytes=%d rbytes=%d",
                  stats["writes"], stats["reads"], stats["beats"], stats["wbytes"], stats["rbytes"])


@cocotb.test()
async def test_model_flags(dut):
    """(e) the models never flagged a tCSM/tVCS/tRP/protocol violation."""
    await setup(dut)
    for _ in range(10):
        await RisingEdge(dut.clk_out)
    await check_models(dut)
