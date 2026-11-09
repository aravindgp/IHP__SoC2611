#!/usr/bin/env python3
"""Explainer of the whole chip: SoC2611 / SoC2611 blocks, data flow, memory, pins, numbers, boot.
Facts from doc/Specification.md and doc/Datasheet.md of the IHP repo.  Reuses make_status_video.py.
usage: make_chip_video.py <out_dir> [--preview]"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_status_video as V
from PIL import ImageDraw

C_WHITE, C_GREY, C_DIM, C_AMBER, C_TEAL, C_BLUE, C_GREEN, C_RED, C_PURPLE = (
    V.C_WHITE, V.C_GREY, V.C_DIM, V.C_AMBER, V.C_TEAL, V.C_BLUE, V.C_GREEN, V.C_RED, V.C_PURPLE)
text, rrect, seg, lerp, mix, rgba, glow = V.text, V.rrect, V.seg, V.lerp, V.mix, V.rgba, V.glow

def block(d, box, title, sub, col, a, tsize=26):
    rrect(d, box, 16, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 220 * a), width=2)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    text(d, (cx, cy - 12), title, tsize, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
    text(d, (cx, cy + 20), sub, 18, rgba(C_GREY, 255 * a), 'Medium', 'mm')

def s_intro(layer, t, dur):
    fp = V.FP(190, 230, 700)
    V.draw_die(layer, fp, macs_frac=seg(t, 0.3, 2.0))
    d = ImageDraw.Draw(layer)
    a = seg(t, 2.4, 0.6)
    if a > 0:
        for (x, y, lab, col) in ((870, 300, 'SRAM: 298 macros', C_TEAL), (870, 600, 'accelerator rows', C_PURPLE), (330, 980, 'pad ring: 64 pads', C_GREY)):
            pass
        text(d, (540, 975), '6.6 × 6.6 mm  ·  IHP SG13CMOS5L  ·  QFN64', 26, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 1018), 'RISC-V CPU + ztachip AI accelerator + 214 KiB SRAM', 24, rgba(C_GREY, 255 * a), 'Medium', 'mm')
        text(d, (540, 1060), 'camera in, HyperBus memory out, UART / SPI / GPIO / JTAG', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')

DOES = [('sees', 'camera frames on the 8-bit port, written to memory as they arrive', C_AMBER),
        ('thinks', 'neural-network inference and vision kernels on the 4 PCOREs: classify, detect, filter, resize, convert', C_PURPLE),
        ('tells', 'results over UART or SPI, GPIO lines for triggers, a host reads them', C_TEAL)]
USES = ['edge AI camera: recognise what is in front of it without a cloud', 'machine vision in low-power devices: sorting, inspection, presence',
        'first silicon of the SoC2611 architecture: measure, learn, scale']

def s_does(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (k, v, col) in enumerate(DOES):
        a = seg(t, 0.3 + i * 0.8, 0.5)
        if a <= 0: continue
        y = 240 + i * 170
        rrect(d, (70, y, 1010, y + 140), 18, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 220 * a), width=2)
        text(d, (100, y + 44), k, 34, rgba(col, 255 * a), 'Bold', 'lm')
        words = v.split(); half = len(words) // 2 + 1
        text(d, (100, y + 90), ' '.join(words[:half]), 21, rgba(C_WHITE, 255 * a), 'Medium', 'lm')
        text(d, (100, y + 120), ' '.join(words[half:]), 21, rgba(C_WHITE, 255 * a), 'Medium', 'lm')
    b = seg(t, 2.8, 0.5)
    if b > 0:
        text(d, (80, 780), 'what it is for', 24, rgba(C_GREY, 255 * b), 'SemiBold', 'lm')
        for k, u in enumerate(USES):
            c = seg(t, 3.0 + k * 0.4, 0.4)
            if c > 0:
                d.ellipse((90, 820 + k * 56, 106, 836 + k * 56), fill=rgba(C_GREEN, 255 * c))
                text(d, (126, 828 + k * 56), u, 21, rgba(C_WHITE, 255 * c), 'Medium', 'lm')
        text(d, (540, 1030), 'limits: 214 KiB on chip plus HyperRAM, so small models and tiled frames, not large networks', 19, rgba(C_DIM, 255 * b), 'Medium', 'mm')

BLOCKS = [((80, 260, 500, 400), 'VexRiscv CPU', 'RV32IM, I/D caches, JTAG debug', C_BLUE, 0.3),
          ((580, 260, 1000, 400), 'SoC2611 accelerator', '4 PCOREs, data path, scratchpad', C_PURPLE, 0.8),
          ((80, 470, 1000, 560), 'AXI interconnect', 'lean split / merge, APB bridge', C_TEAL, 1.3),
          ((80, 630, 380, 760), 'HyperBus', 'HyperRAM / HyperFlash, 8-bit', C_AMBER, 1.8),
          ((400, 630, 700, 760), 'Camera in', '8-bit DVP + video stream writer', C_AMBER, 2.1),
          ((720, 630, 1000, 760), 'Peripherals', 'UART, SPI, timer, GPIO', C_AMBER, 2.4),
          ((80, 830, 1000, 930), 'On-chip SRAM', '298 macros, 214 KiB: caches, scratchpad, FIFOs', C_TEAL, 2.9)]

def s_blocks(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for box, title, sub, col, t0 in BLOCKS:
        a = seg(t, t0, 0.5)
        if a > 0: block(d, box, title, sub, col, a)
    b = seg(t, 1.5, 0.5)
    if b > 0:
        for x in (290, 790): d.line([(x, 400), (x, 470)], fill=rgba(C_TEAL, 200 * b), width=4)
        for x in (230, 550, 860): d.line([(x, 560), (x, 630)], fill=rgba(C_TEAL, 200 * b), width=4)
    c = seg(t, 3.4, 0.5)
    if c > 0:
        text(d, (540, 1000), 'one main clock with integrated clock gating · 1.2 V core · 3.3 V IO', 22, rgba(C_GREY, 255 * c), 'Medium', 'mm')

FLOW = [('camera', 110), ('stream writer', 310), ('HyperRAM', 510), ('accelerator', 710), ('CPU / UART', 910)]

def s_flow(layer, t, dur):
    d = ImageDraw.Draw(layer)
    y = 520
    for i, (nm, x) in enumerate(FLOW):
        a = seg(t, 0.3 + i * 0.4, 0.4)
        if a <= 0: continue
        col = (C_AMBER, C_TEAL, C_AMBER, C_PURPLE, C_BLUE)[i]
        rrect(d, (x - 85, y - 50, x + 85, y + 50), 16, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 220 * a), width=2)
        text(d, (x, y), nm, 21, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
        if i > 0:
            px = FLOW[i - 1][1] + 85
            d.line([(px, y), (x - 85, y)], fill=rgba(C_GREY, 200 * a), width=3)
    b = seg(t, 2.4, 0.5)
    if b > 0:
        ph = (t * 0.5) % 1.0
        for k in range(5):
            xx = lerp(110, 910, (k / 5 + ph) % 1.0)
            def dot(dd, xx=xx): dd.ellipse((xx - 7, y - 7, xx + 7, y + 7), fill=rgba(C_TEAL))
            glow(layer, dot, radius=8, alpha=.8)
        d = ImageDraw.Draw(layer)
        notes = ['frames arrive on the 8-bit camera port', 'the stream writer lands them in HyperRAM over AXI',
                 'the accelerator pulls tiles into its scratchpad, 4 PCOREs run the kernels', 'results go back to memory; the CPU reads them, reports over UART']
        for k, n in enumerate(notes):
            c = seg(t, 2.6 + k * 0.6, 0.4)
            if c > 0: text(d, (540, 680 + k * 48), n, 21, rgba(C_GREY if k < 3 else C_WHITE, 255 * c), 'Medium', 'mm')

def s_memory(layer, t, dur):
    fp = V.FP(140, 215, 560)
    V.draw_die(layer, fp, macs_frac=seg(t, 0.2, 1.6))
    d = ImageDraw.Draw(layer)
    a = seg(t, 1.2, 0.6)
    if a > 0:
        for i, (big, small) in enumerate([('298', 'SRAM macros'), ('214 KiB', 'on-chip memory'), ('12.9 mm²', 'of 43.6 mm² die'), ('M1–M4', 'blocked inside each macro')]):
            y = 240 + i * 135
            rrect(d, (740, y, 1010, y + 110), 16, fill=rgba((20, 26, 38), 240 * a), outline=rgba(C_TEAL, 160 * a))
            text(d, (875, y + 40), big, 32, rgba(C_TEAL, 255 * a), 'Bold', 'mm')
            text(d, (875, y + 82), small, 18, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    b = seg(t, 2.6, 0.6)
    if b > 0:
        text(d, (540, 850), 'what the SRAM holds', 24, rgba(C_WHITE, 255 * b), 'SemiBold', 'mm')
        text(d, (540, 895), 'CPU instruction and data caches · boot TCM', 21, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        text(d, (540, 932), 'accelerator scratchpad and register files · stream FIFOs', 21, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        text(d, (540, 985), 'the macros set the floorplan: pins on one edge, no routing over them', 20, rgba(C_DIM, 255 * b), 'Medium', 'mm')

SIDES = [('west', 'camera control, GPIO 4 in / 4 out', (120, 300, 190, 1000), C_AMBER),
         ('south', 'HyperBus: 8 DQ, RWDS, CK, CS, reset', (120, 1000, 960, 1070), C_AMBER),
         ('east', 'UART, SPI, clock, reset, JTAG', (890, 300, 960, 1000), C_BLUE),
         ('north', 'camera data: 8 bits, VS, HS, PCLK, MCLK', (120, 230, 960, 300), C_PURPLE)]

def s_pins(layer, t, dur):
    d = ImageDraw.Draw(layer)
    d.rectangle((190, 300, 890, 1000), fill=rgba((14, 19, 30)), outline=rgba((60, 70, 90)), width=2)
    text(d, (540, 650), 'SoC2611', 40, C_WHITE, 'Bold', 'mm')
    text(d, (540, 700), 'QFN64 · 48 signal + 16 supply pads', 20, C_GREY, 'Medium', 'mm')
    for i, (side, what, box, col) in enumerate(SIDES):
        a = seg(t, 0.3 + i * 0.7, 0.5)
        if a <= 0: continue
        rrect(d, box, 8, fill=rgba(col, 60 * a), outline=rgba(col, 200 * a))
        n = 16
        for k in range(n):
            if side in ('west', 'east'):
                y = lerp(box[1] + 20, box[3] - 20, k / (n - 1)); x = (box[0] + box[2]) / 2
            else:
                x = lerp(box[0] + 20, box[2] - 20, k / (n - 1)); y = (box[1] + box[3]) / 2
            d.rectangle((x - 9, y - 9, x + 9, y + 9), fill=rgba(col if k not in (0, 1, 6, 7) else C_GREY, 230 * a))
        lab = f'{side}: {what}'
        pos = {'west': (540, 790), 'south': (540, 830), 'east': (540, 870), 'north': (540, 910)}[side]
        text(d, pos, lab, 20, rgba(C_WHITE, 255 * a), 'Medium', 'mm')
    b = seg(t, 3.3, 0.5)
    if b > 0: text(d, (540, 1110), 'grey pads: a VDD/VSS and an IOVDD/IOVSS pair on every side', 19, rgba(C_GREY, 255 * b), 'Medium', 'mm')

NUMS = [('process', 'IHP SG13CMOS5L, 130 nm CMOS, 5 metals'), ('die / core', '6.6 × 6.6 mm / 5.92 × 5.92 mm'),
        ('standard cells', '~290k after synthesis, ~335k after P&R'), ('SRAM', '298 macros, 214 KiB, 12.9 mm²'),
        ('supplies', '1.2 V core, 3.3 V IO'), ('package', 'QFN64, 70 × 70 µm bondpads'),
        ('CPU', 'VexRiscv RV32IM, caches, JTAG'), ('accelerator', '4 PCOREs, scratchpad, AXI-lite control')]

def s_numbers(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (k, v) in enumerate(NUMS):
        a = seg(t, 0.3 + i * 0.35, 0.4)
        if a <= 0: continue
        y = 250 + i * 100
        rrect(d, (70, y, 1010, y + 82), 14, fill=rgba((20, 26, 38), 240 * a), outline=rgba((40, 48, 64), 255 * a))
        text(d, (100, y + 41), k, 24, rgba(C_TEAL, 255 * a), 'Bold', 'lm')
        text(d, (980, y + 41), v, 22, rgba(C_WHITE, 255 * a), 'Medium', 'rm')

BOOT = [('power-on reset', 'porst_n low, clk_x2 running', C_GREY), ('boot ROM', 'copied into the tightly coupled memory', C_BLUE),
        ('UART loader', 'the first program arrives over the serial port', C_TEAL), ('JTAG', 'debug access to the CPU at any time', C_PURPLE),
        ('run', 'CPU configures the accelerator, camera frames flow', C_GREEN)]

def s_boot(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (k, v, col) in enumerate(BOOT):
        a = seg(t, 0.3 + i * 0.7, 0.5)
        if a <= 0: continue
        y = 260 + i * 150
        if i > 0:
            d.line([(140, y - 30), (140, y + 2)], fill=rgba(C_DIM, 255 * a), width=3)
            d.polygon([(132, y - 2), (148, y - 2), (140, y + 8)], fill=rgba(C_DIM, 255 * a))
        rrect(d, (70, y + 8, 1010, y + 118), 16, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 200 * a))
        d.ellipse((108, y + 43, 148, y + 83), fill=rgba(col, 255 * a))
        text(d, (180, y + 46), k, 28, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
        text(d, (180, y + 86), v, 21, rgba(C_GREY, 255 * a), 'Medium', 'lm')

def s_status(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.3, 0.7)
    rrect(d, (90, 380, 990, 700), 26, fill=rgba((20, 26, 38), 240 * a), outline=rgba(C_BLUE, 200 * a), width=2)
    text(d, (540, 440), 'where it stands today', 26, rgba(C_BLUE, 255 * a), 'Bold', 'mm')
    text(d, (540, 510), 'placed and routed at 6.6 mm', 32, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
    text(d, (540, 565), 'routing closure in progress: shorts inside the SRAM macros', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    text(d, (540, 605), 'then antenna, DRC, LVS, timing, release', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    text(d, (540, 660), 'preliminary release v1.1.0 on GitHub', 20, rgba(C_TEAL, 255 * a), 'Medium', 'mm')
    b = seg(t, 2.2, 0.6)
    if b > 0:
        text(d, (540, 820), 'next generation (March 2027): no x2 clock, dual-port SRAM,', 21, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        text(d, (540, 858), 'HyperFlash, SPI master, 4-bit camera port, smaller configuration', 21, rgba(C_GREY, 255 * b), 'Medium', 'mm')

V.SCENES = [
    ('SoC2611 in one picture', s_intro,
     'This is SoC2611 {S o C one|SoC1}, taped out as {S o C twenty six eleven|SoC2611}: a RISC-V system on chip with the '
     'ztachip AI accelerator, on IHP\'s one hundred and thirty nanometre CMOS process. Six point six millimetres a side, '
     'in a sixty-four pin QFN. Here is what is inside.'),
    ('What it does', s_does,
     'What does it do? It sees: camera frames come in on the eight-bit port and are written to memory as they arrive. It '
     'thinks: the four processing cores run neural-network inference and classical vision kernels, classify, detect, filter, '
     'resize, convert. And it tells: results go out over UART or SPI, with GPIO lines for triggers. It is an edge AI camera '
     'chip, for machine vision in low-power devices, and the first silicon of the SoC2611 architecture. Its limits are '
     'honest: two hundred and fourteen kilobytes on chip plus HyperRAM, so small models and tiled frames, not large networks.'),
    ('The blocks', s_blocks,
     'A VexRiscv CPU, thirty-two bit with caches and JTAG debug. The SoC2611 accelerator: four processing cores with a '
     'data path and a scratchpad. A lean AXI interconnect joins them to a HyperBus memory port, a camera input with a video '
     'stream writer, and the peripherals: UART, SPI, timer and GPIO. All of it on one main clock with clock gating.'),
    ('How data flows', s_flow,
     'Frames arrive on the eight-bit camera port. The stream writer lands them in HyperRAM over AXI. The accelerator pulls '
     'tiles into its scratchpad, and the four cores run the kernels. Results go back to memory, where the CPU reads them '
     'and reports over the UART.'),
    ('Memory on chip', s_memory,
     'Two hundred and ninety-eight SRAM macros hold two hundred and fourteen kilobytes: the CPU caches and boot memory, '
     'the accelerator scratchpad and register files, and the stream FIFOs. They cover thirteen of the forty-four square '
     'millimetres, and they set the floorplan: pins on one edge, no routing over them.'),
    ('Sixty-four pins', s_pins,
     'West: camera control and four GPIO in and out. South: the HyperBus, eight data lines with strobe, clock, select '
     'and reset. East: UART, SPI, the clock input, reset and JTAG. North: the eight camera data bits with sync and pixel '
     'clock. Every side carries a core and an IO supply pair.'),
    ('The numbers', s_numbers,
     'Around two hundred and ninety thousand standard cells after synthesis, three hundred and thirty-five thousand after '
     'place and route. One point two volt core, three point three volt IO. Five metal layers: four thin, one thick.'),
    ('Boot and bring-up', s_boot,
     'At power-on the boot ROM is copied into the tightly coupled memory and the UART loader waits for the first program. '
     'JTAG gives debug access to the CPU at any time. Then the CPU configures the accelerator and camera frames flow.'),
    ('Where it stands', s_status,
     'The chip is placed and routed at six point six millimetres. Routing closure is in progress on the shorts inside the '
     'SRAM macros; antenna, DRC, LVS and timing follow. A preliminary release is on GitHub, and the next generation for '
     'March is already defined.'),
    ('', V.s_end, ''),
]

if __name__ == '__main__':
    V.main()
