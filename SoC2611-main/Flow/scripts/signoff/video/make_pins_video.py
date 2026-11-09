#!/usr/bin/env python3
"""Pinout explainer: the QFN64 of SoC2611 side by side, each pin named as the narration reaches it.
Pins are read from the IHP repo datasheet table.  Reuses make_status_video.py.
usage: make_pins_video.py <out_dir> [--preview]"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_status_video as V
from PIL import ImageDraw

C_WHITE, C_GREY, C_DIM, C_AMBER, C_TEAL, C_BLUE, C_GREEN, C_RED, C_PURPLE = (
    V.C_WHITE, V.C_GREY, V.C_DIM, V.C_AMBER, V.C_TEAL, V.C_BLUE, V.C_GREEN, V.C_RED, V.C_PURPLE)
text, rrect, seg, lerp, mix, rgba = V.text, V.rrect, V.seg, V.lerp, V.mix, V.rgba

DS = os.environ.get('DATASHEET', '/workspace/ihp_ip_repo/IHP__DSOC2610/doc/Datasheet.md')
PINS = []
for ln in open(DS, errors='replace'):
    m = re.match(r'\|\s*(\d+)\s*\|\s*(\w+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|', ln)
    if m: PINS.append((int(m.group(1)), m.group(2), m.group(3), m.group(4)))
assert len(PINS) == 64, len(PINS)

def kind(cell, name):
    if cell.startswith('IOPadIOV') or cell in ('IOPadVdd', 'IOPadVss'): return 'supply', C_GREY
    if 'InOut' in cell: return 'in / out', C_GREEN
    if cell == 'IOPadIn': return 'input', C_BLUE
    return 'output', C_AMBER

def side_pins(side): return [p for p in PINS if p[1] == side]

# groups per side: (pin numbers, spoken words) -- the highlight follows the narration proportionally
GROUPS = {
    'west': [((1, 2), 'IOVSS and IOVDD, the IO supply pair'), ((3, 4), 'camera reset and power-down'), ((5, 6), 'the I2C clock and data for the sensor'),
             ((7, 8), 'VSS and VDD, the core supply'), ((9, 10, 11, 12), 'four GPIO outputs'), ((13, 14, 15, 16), 'four GPIO inputs')],
    'south': [((17, 18), 'IO supply'), ((19, 20, 21, 22), 'HyperBus data zero to three'), ((23, 24), 'core supply'), ((25,), 'RWDS, the read-write data strobe'),
              ((26,), 'the HyperBus clock'), ((27, 28, 29, 30), 'data four to seven'), ((31,), 'chip select'), ((32,), 'the memory reset')],
    'east': [((33, 34), 'IO supply'), ((35, 36), 'UART transmit and receive'), ((37, 38), 'SPI clock and MOSI'), ((39, 40), 'core supply'),
             ((41,), 'the clock input, clock times two'), ((42,), 'power-on reset, active low'), ((43, 44), 'SPI MISO and chip select'),
             ((45, 46, 47, 48), 'JTAG: TCK, TMS, TDI, TDO')],
    'north': [((49, 50), 'IO supply'), ((51,), 'the camera pixel clock'), ((52, 53, 54), 'camera data zero to two'), ((55, 56), 'core supply'),
              ((57, 58, 59, 60, 61), 'camera data three to seven'), ((62, 63), 'vertical and horizontal sync'), ((64,), 'the master clock out to the sensor')],
}

def draw_chip(d, cx, cy, size, hl_side=None, a=1.0):
    x0, y0, x1, y1 = cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2
    d.rectangle((x0, y0, x1, y1), fill=rgba((14, 19, 30), 255 * a), outline=rgba((60, 70, 90), 255 * a), width=2)
    for side, box in (('west', (x0 - 26, y0 + 20, x0 - 6, y1 - 20)), ('east', (x1 + 6, y0 + 20, x1 + 26, y1 - 20)),
                      ('south', (x0 + 20, y1 + 6, x1 - 20, y1 + 26)), ('north', (x0 + 20, y0 - 26, x1 - 20, y0 - 6))):
        col = C_TEAL if side == hl_side else (50, 58, 74)
        rrect(d, box, 5, fill=rgba(col, 255 * a))
        lx, ly_ = {'west': (x0 - 60, cy), 'east': (x1 + 60, cy), 'south': (cx, y1 + 52), 'north': (cx, y0 - 52)}[side]
        text(d, (lx, ly_), side, 18, rgba(C_TEAL if side == hl_side else C_DIM, 255 * a), 'SemiBold', 'mm')
    text(d, (x0 + 14, y0 + 14), '1', 16, rgba(C_WHITE, 255 * a), 'Bold', 'lt')
    d.ellipse((x0 + 34, y0 + 10, x0 + 44, y0 + 20), fill=rgba(C_WHITE, 255 * a))

def s_overview(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.2, 0.8)
    draw_chip(d, 540, 560, 520, None, a)
    text(d, (540, 540), 'SoC2611', 44, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
    text(d, (540, 595), 'QFN64 · 48 signal + 16 supply', 20, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    b = seg(t, 1.6, 0.6)
    if b > 0:
        # counter-clockwise arrow hint
        for (x, y, lab) in ((150, 520, '1–16'), (540, 900, '17–32'), (930, 520, '33–48'), (540, 220, '49–64')):
            text(d, (x, y), lab, 22, rgba(C_TEAL, 255 * b), 'Bold', 'mm')
        text(d, (540, 975), 'pin 1 at the top-left corner, numbered counter-clockwise', 22, rgba(C_WHITE, 255 * b), 'SemiBold', 'mm')
        text(d, (540, 1015), 'west, south, east, north: sixteen pads a side', 21, rgba(C_GREY, 255 * b), 'Medium', 'mm')
    c = seg(t, 3.2, 0.5)
    if c > 0:
        for i, (lab, col) in enumerate((('supply', C_GREY), ('input', C_BLUE), ('output', C_AMBER), ('in / out', C_GREEN))):
            x = 180 + i * 220
            d.rectangle((x, 1065, x + 22, 1087), fill=rgba(col, 255 * c))
            text(d, (x + 34, 1076), lab, 19, rgba(C_WHITE, 255 * c), 'Medium', 'lm')

def draw_side(side, layer, t, dur):
    pins = side_pins(side); groups = GROUPS[side]
    total_chars = sum(len(g[1]) + 12 for g in groups)
    if True:
        d = ImageDraw.Draw(layer)
        draw_chip(d, 190, 330, 180, side, 1.0)
        # which group is current, by narration proportion
        audio = max(dur - 0.9, 1.0); frac = min(1.0, t / audio)
        acc, cur, done = 0.0, -1, set()
        for gi, g in enumerate(groups):
            w = (len(g[1]) + 12) / total_chars
            if frac >= acc + w: done.update(g[0])
            elif frac >= acc and cur < 0: cur = gi
            acc += w
        cur_pins = set(groups[cur][0]) if cur >= 0 else set()
        # zoomed pad strip with numbers (left to right = pin order along the side)
        sx0, sx1, sy = 70, 1010, 540
        for i, (n, s, name, cell) in enumerate(pins):
            x = lerp(sx0 + 30, sx1 - 30, i / 15)
            k, col = kind(cell, name)
            hot = n in cur_pins; past = n in done
            al = 255 if (hot or past) else 90
            sz = 22 if hot else 16
            d.rectangle((x - sz, sy - sz, x + sz, sy + sz), fill=rgba(col, al), outline=rgba(C_WHITE, 255 if hot else 0), width=3)
            text(d, (x, sy + 44), str(n), 16, rgba(C_WHITE if (hot or past) else C_DIM, 255), 'Bold' if hot else 'Medium', 'mm')
        d.rectangle((sx0, sy - 36, sx1, sy + 36), outline=rgba((60, 70, 90)), width=1)
        text(d, (540, 460), f'{side} side, pins {pins[0][0]} to {pins[-1][0]}', 24, C_TEAL, 'SemiBold', 'mm')
        # table of the 16 pins, two columns, current group highlighted
        for i, (n, s, name, cell) in enumerate(pins):
            c, r = divmod(i, 8)
            x0 = 70 + c * 480; y = 640 + r * 54
            k, col = kind(cell, name)
            hot = n in cur_pins; past = n in done
            if hot: rrect(d, (x0 - 8, y - 22, x0 + 452, y + 22), 10, fill=rgba(col, 60), outline=rgba(col, 220))
            al = 255 if (hot or past) else 110
            text(d, (x0 + 6, y), f'{n}', 20, rgba(C_WHITE, al), 'Bold', 'lm')
            text(d, (x0 + 50, y), name, 21, rgba(C_WHITE if hot else C_GREY, al), 'Bold' if hot else 'Medium', 'lm')
            text(d, (x0 + 440, y), k, 17, rgba(col, al), 'Medium', 'rm')
        if cur >= 0:
            text(d, (540, 1105), groups[cur][1], 22, C_WHITE, 'SemiBold', 'mm')

def s_west(layer, t, dur): draw_side('west', layer, t, dur)
def s_south(layer, t, dur): draw_side('south', layer, t, dur)
def s_east(layer, t, dur): draw_side('east', layer, t, dur)
def s_north(layer, t, dur): draw_side('north', layer, t, dur)

def s_summary(layer, t, dur):
    d = ImageDraw.Draw(layer)
    rows = [('camera', '8 data + PCLK, VS, HS, MCLK, reset, power-down, I2C', 16, C_PURPLE), ('HyperBus memory', '8 DQ, RWDS, CK, CS, reset', 12, C_AMBER),
            ('UART / SPI', 'TX, RX, SCLK, MOSI, MISO, CSn', 6, C_TEAL), ('GPIO', '4 in, 4 out', 8, C_BLUE), ('clock, reset, JTAG', 'clk_x2, porst_n, TCK, TMS, TDI, TDO', 6, C_GREEN),
            ('supplies', 'VDD/VSS and IOVDD/IOVSS on every side', 16, C_GREY)]
    for i, (k, v, n, col) in enumerate(rows):
        a = seg(t, 0.3 + i * 0.45, 0.4)
        if a <= 0: continue
        y = 250 + i * 118
        rrect(d, (70, y, 1010, y + 96), 16, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 180 * a))
        text(d, (100, y + 32), k, 26, rgba(col, 255 * a), 'Bold', 'lm')
        text(d, (100, y + 68), v, 20, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        text(d, (980, y + 48), f'{n}', 36, rgba(C_WHITE, 255 * a), 'Bold', 'rm')
    b = seg(t, 3.2, 0.5)
    if b > 0: text(d, (540, 1010), 'all 64 pins of the QFN64 in use', 22, rgba(C_WHITE, 255 * b), 'SemiBold', 'mm')

V.SCENES = [
    ('The sixty-four pins', s_overview,
     'SoC2611 comes in a sixty-four pin QFN. Pin one is at the top-left corner and the numbers run counter-clockwise: '
     'west one to sixteen, south seventeen to thirty-two, east thirty-three to forty-eight, north forty-nine to sixty-four. '
     'Grey pads are supplies, blue inputs, amber outputs, green bidirectional. Let us walk round.'),
    ('West: camera control and GPIO', s_west,
     'West, pins one to sixteen. One and two: IOVSS and IOVDD, the IO supply pair. Three and four: camera reset and '
     'power-down. Five and six: the I2C clock and data for the sensor. Seven and eight: VSS and VDD, the core supply. '
     'Nine to twelve: four GPIO outputs. Thirteen to sixteen: four GPIO inputs.'),
    ('South: the HyperBus memory port', s_south,
     'South, pins seventeen to thirty-two, the HyperBus memory port. Seventeen and eighteen: IO supply. Nineteen to '
     'twenty-two: data zero to three. Twenty-three and twenty-four: core supply. Twenty-five: RWDS, the read-write data '
     'strobe. Twenty-six: the HyperBus clock. Twenty-seven to thirty: data four to seven. Thirty-one: chip select. '
     'Thirty-two: the memory reset. The data pads are sixteen milliamp drivers.'),
    ('East: UART, SPI, clock, JTAG', s_east,
     'East, pins thirty-three to forty-eight. Thirty-three and thirty-four: IO supply. Thirty-five and thirty-six: UART '
     'transmit and receive. Thirty-seven and thirty-eight: SPI clock and MOSI. Thirty-nine and forty: core supply. '
     'Forty-one: the clock input, clock times two. Forty-two: power-on reset, active low. Forty-three and forty-four: '
     'SPI MISO and chip select. Forty-five to forty-eight: JTAG, TCK, TMS, TDI and TDO.'),
    ('North: camera data', s_north,
     'North, pins forty-nine to sixty-four, the camera data. Forty-nine and fifty: IO supply. Fifty-one: the camera pixel '
     'clock. Fifty-two to fifty-four: camera data zero to two. Fifty-five and fifty-six: core supply. Fifty-seven to '
     'sixty-one: camera data three to seven. Sixty-two and sixty-three: vertical and horizontal sync. Sixty-four: the '
     'master clock out to the sensor.'),
    ('In groups', s_summary,
     'In groups: sixteen pins for the camera, twelve for the HyperBus memory, six for UART and SPI, eight GPIO, six for '
     'clock, reset and JTAG, and sixteen supply pads, a core pair and an IO pair on every side. All sixty-four in use.'),
    ('', V.s_end, ''),
]

if __name__ == '__main__':
    V.main()
