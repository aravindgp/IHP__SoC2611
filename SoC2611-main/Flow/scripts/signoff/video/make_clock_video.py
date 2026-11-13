#!/usr/bin/env python3
"""Video of 13 November 2026: the clocks and the speed of the chip in plain words.
What a clock is (a beat; the slowest path sets the fastest beat), why three speeds are quoted (fast, typical and
slow corner: 1.32 V at -40 C, 1.20 V at 25 C, 1.08 V at 125 C), the two clocks of this chip (the input clock at the
pad and the system clock, every second pulse of it, because most memory blocks do two accesses per system step),
how the input clock limits the speed (a path into a memory has one input tick, half a system step), and why a
system clock of 100 MHz is out of reach (it would need a 200 MHz input clock, 5 ns per tick, against 7.5 to 17 ns
for the path into a memory).
Numbers of candidate v.2.4.0 on the routed wires (13 Nov 2026): system clock 54.7 / 45.5 / 29.4 MHz; time needed
by the longest logic step 18.3 / 20.8 / 29.6 ns and by the path into a memory 7.5 / 11.0 / 17.0 ns (period minus
slack, clock pairs clk_main to clk_main and clk_main to core_clock). 252 memory clock pins are on the input clock,
87 on the system clock. Earlier releases: 15.0 / 12.7 / 10.0 (v.2.0.1), 45.7 / 30.0 / 18.9 (v.2.2.0),
54.2 / 44.3 / 28.7 (v.2.3.0).
Same renderer, captions and voice (en-GB-RyanNeural) as make_status_video.py.
usage: make_clock_video.py <out_dir> [--preview] [--jobs N]     (writes <out_dir>/SoC2611_status.mp4)"""
import importlib.util
import math
import os
import sys

from PIL import ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('svbase', os.path.join(HERE, 'make_status_video.py'))
B = importlib.util.module_from_spec(spec)
sys.modules['svbase'] = B          # the render pool pickles svbase.render_scene by name
spec.loader.exec_module(B)
text, rrect, seg, rgba, mix, lerp = B.text, B.rrect, B.seg, B.rgba, B.mix, B.lerp
C_WHITE, C_GREY, C_DIM, C_AMBER, C_TEAL, C_BLUE, C_GREEN, C_RED, C_PURPLE, BG = (
    B.C_WHITE, B.C_GREY, B.C_DIM, B.C_AMBER, B.C_TEAL, B.C_BLUE, B.C_GREEN, B.C_RED, B.C_PURPLE, B.BG)
CARD = (20, 26, 38); EDGE = (40, 48, 64)


def clamp(x): return max(0.0, min(1.0, x))


def card(d, box, a, outline=EDGE):
    rrect(d, box, 18, fill=rgba(CARD, 235 * a), outline=rgba(outline, 255 * a), width=2)


def pill(d, x0, y, s, col, a, size=20):
    pw = B.font(size).getlength(s) + 34
    rrect(d, (x0, y, x0 + pw, y + 34), 17, fill=rgba(col, 255 * a * .22))
    text(d, (x0 + pw / 2, y + 17), s, size, rgba(col, 255 * a), 'Bold', 'mm')
    return pw


def dot(d, p, col, r=8, a=1.0):
    d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=rgba(col, 255 * a))


def arrow(d, p0, p1, col, width=5, head=14):
    d.line([p0, p1], fill=col, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (-1, 1):
        q = (p1[0] - head * math.cos(ang + s * 0.45), p1[1] - head * math.sin(ang + s * 0.45))
        d.line([p1, q], fill=col, width=width)


def sq_wave(d, x0, x1, y_lo, y_hi, period, high, phase, col, width=4):
    """square wave between x0 and x1; a pulse starts at x0 + phase + k * period and stays high for `high` px"""
    def level(x):
        return ((x - x0 - phase) % period) < high
    xs = {x0, x1}
    k0 = int(math.floor(-phase / period)) - 1
    for k in range(k0, k0 + int((x1 - x0) / period) + 4):
        for e in (x0 + phase + k * period, x0 + phase + k * period + high):
            if x0 < e < x1:
                xs.add(e)
    xs = sorted(xs); pts = []
    for a, b in zip(xs, xs[1:]):
        y = y_hi if level((a + b) / 2) else y_lo
        pts += [(a, y), (b, y)]
    d.line(pts, fill=col, width=width, joint='curve')


# ------------------------------------------------------------------ scene 0: title
T0 = dict(c1=4.8, c2=7.6, c3=12.2, c4=17.4)


def s_title(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    text(d, (540, 205), 'the beat of the chip, in plain words', 27, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    rows = [('1', 'What a clock is', 'a beat that every part of the chip follows', C_TEAL, T0['c1']),
            ('2', 'Fast, typical, slow', 'why one chip has three speeds', C_AMBER, T0['c2']),
            ('3', 'Input clock and system clock', 'the two clocks of this chip', C_BLUE, T0['c3']),
            ('4', 'Why not 100 MHz', 'the limit set by the input clock', C_RED, T0['c4'])]
    for i, (n, k, v, col, at) in enumerate(rows):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 270 + i * 215
        card(d, (70, y, 1010, y + 185), e, col)
        d.ellipse((100, y + 52, 180, y + 132), fill=rgba(col, 255 * e))
        text(d, (140, y + 92), n, 42, rgba(BG, 255 * e), 'Bold', 'mm')
        text(d, (215, y + 68), k, 37, rgba(C_WHITE, 255 * e), 'Bold', 'lm')
        text(d, (215, y + 122), v, 25, rgba(C_GREY, 255 * e), 'Medium', 'lm')


# ------------------------------------------------------------------ scene 1: the clock is a beat
T1 = dict(p1=5.8, a1=13.0, p2=22.8, a2=24.0, rule=33.0, mhz=37.5)
X_T0, X_ARR, X_END = 130, 760, 975


def beat_panel(d, y, t, t_show, t0, x_tick, label, ok):
    a = seg(t, t_show, 0.5)
    if a <= 0:
        return
    col_ok = C_GREEN if ok else C_RED
    card(d, (70, y, 1010, y + 385), a)
    text(d, (100, y + 38), label, 27, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
    # the path: flip-flop A, three gates, flip-flop B
    yy = y + 125
    d.line([(215, yy), (865, yy)], fill=rgba(C_DIM, 255 * a), width=5)
    for x0, s in ((100, 'A'), (865, 'B')):
        rrect(d, (x0, yy - 42, x0 + 115, yy + 42), 8, fill=rgba(CARD, 255 * a), outline=rgba(C_WHITE, 255 * a), width=3)
        text(d, (x0 + 57, yy - 8), s, 30, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
        text(d, (x0 + 57, yy + 22), 'flip-flop', 16, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    for gx in (300, 475, 650):
        rrect(d, (gx, yy - 28, gx + 100, yy + 28), 8, fill=rgba(mix(C_PURPLE, BG, .7), 255 * a), outline=rgba(C_PURPLE, 255 * a), width=2)
        text(d, (gx + 50, yy), 'gate', 19, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
    # the time line
    ya = y + 285
    d.line([(X_T0, ya), (X_END, ya)], fill=rgba(C_DIM, 255 * a), width=3)
    text(d, (X_END, ya + 28), 'time', 17, rgba(C_DIM, 255 * a), 'Medium', 'rm')
    d.line([(X_T0, ya - 46), (X_T0, ya + 16)], fill=rgba(C_WHITE, 255 * a), width=4)
    text(d, (X_T0, ya - 62), 'tick', 20, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
    p = clamp((t - t0) / 6.5)
    cur = X_T0 + p * (X_END - X_T0)
    late = (not ok) and cur >= x_tick
    sig_col = C_RED if late else C_TEAL
    d.rectangle((X_T0, ya - 14, min(cur, X_ARR), ya + 14), fill=rgba(sig_col, 220 * a))
    d.line([(X_ARR, ya - 26), (X_ARR, ya + 26)], fill=rgba(C_TEAL, 255 * a), width=3)
    text(d, (X_ARR, ya + 46), 'signal arrives', 19, rgba(C_TEAL, 255 * a), 'SemiBold', 'mm')
    flash = cur >= x_tick
    d.line([(x_tick, ya - 46), (x_tick, ya + 16)], fill=rgba(C_AMBER if flash else C_WHITE, 255 * a), width=6 if flash else 4)
    text(d, (x_tick, ya - 62), 'next tick', 20, rgba(C_AMBER if flash else C_WHITE, 255 * a), 'SemiBold', 'mm')
    frac = clamp((cur - X_T0) / (X_ARR - X_T0))
    if p > 0:
        dot(d, (215 + frac * 650, yy), sig_col, 13, a)
    if flash:
        e = seg(t, t0 + 6.5 * (x_tick - X_T0) / (X_END - X_T0), 0.4)
        s = 'arrived before the tick: correct value' if ok else 'still on its way: wrong value stored'
        pw = B.font(22).getlength(s) + 40
        rrect(d, (980 - pw, y + 20, 980, y + 58), 19, fill=rgba(col_ok, 60 * a * e))
        text(d, (980 - pw / 2, y + 39), s, 22, rgba(col_ok, 255 * a * e), 'Bold', 'mm')


def s_beat(layer, t, dur):
    d = ImageDraw.Draw(layer)
    beat_panel(d, 185, t, T1['p1'], T1['a1'], 930, 'a slow beat', True)
    beat_panel(d, 590, t, T1['p2'], T1['a2'], 560, 'a faster beat', False)
    z = seg(t, T1['rule'], 0.6)
    if z > 0:
        card(d, (70, 995, 1010, 1085), z, C_AMBER)
        text(d, (540, 1040), 'the slowest path sets the fastest beat', 30, rgba(C_WHITE, 255 * z), 'Bold', 'mm')
    q = seg(t, T1['mhz'], 0.6)
    if q > 0:
        text(d, (540, 1125), '1 MHz = one million ticks per second', 23, rgba(C_GREY, 255 * q), 'Medium', 'mm')


# ------------------------------------------------------------------ scene 2: fast, typical, slow
T2 = dict(fab=3.7, cond=9.5, hot=13.3, out=43.8, fast=19.6, typ=26.2, slow=31.9, run=38.4, speeds=45.0, rate=53.6)
CORNERS = [('FAST', 'strong transistors', '1.32 V · -40 °C', 18.3, 54.7, C_GREEN),
           ('TYPICAL', 'average transistors', '1.20 V · 25 °C', 20.8, 45.5, C_AMBER),
           ('SLOW', 'weak transistors', '1.08 V · 125 °C', 29.6, 29.4, C_RED)]


def s_corners(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a0 = seg(t, 0.5, 0.5)
    text(d, (540, 200), 'the same chip design, timed three times', 25, rgba(C_GREY, 255 * a0), 'Medium', 'mm')
    for i, (name, tr, cond, ns, mhz, col) in enumerate(CORNERS):
        e = seg(t, (T2['fast'], T2['typ'], T2['slow'])[i], 0.5)
        if e <= 0:
            continue
        y = 245 + i * 180
        card(d, (70, y, 1010, y + 160), e, col)
        text(d, (100, y + 42), name, 31, rgba(col, 255 * e), 'Bold', 'lm')
        text(d, (100, y + 86), tr, 21, rgba(C_WHITE, 255 * e), 'Medium', 'lm')
        text(d, (100, y + 122), cond, 21, rgba(C_GREY, 255 * e), 'Medium', 'lm')
        xa, xb, yy = 400, 850, y + 80
        d.line([(xa, yy), (xb, yy)], fill=rgba(C_DIM, 255 * e), width=5)
        d.line([(xb, yy - 30), (xb, yy + 30)], fill=rgba(C_WHITE, 255 * e), width=4)
        fr = clamp((t - T2['run']) / (ns * 0.19))
        if t > T2['run']:
            d.line([(xa, yy), (xa + fr * (xb - xa), yy)], fill=rgba(col, 255 * e), width=7)
        dot(d, (xa + fr * (xb - xa), yy), col, 14, e)
        if fr >= 1.0:
            text(d, (990, yy), f'{ns:.1f} ns', 27, rgba(C_WHITE, 255 * e), 'Bold', 'rm')
        text(d, (xa, yy + 44), 'the longest logic path', 17, rgba(C_DIM, 255 * e), 'Medium', 'lm')
    # before the lanes: why chips differ (shown in the lower part, gone before the speeds appear)
    out = 1.0 - seg(t, T2['out'], 0.6)
    fa = seg(t, T2['fab'], 0.5) * out
    if fa > 0:
        card(d, (70, 850, 520, 1090), fa)
        text(d, (295, 890), 'the factory', 25, rgba(C_WHITE, 255 * fa), 'Bold', 'mm')
        for k, strength in enumerate((0.45, 0.8, 1.0, 0.65, 0.3)):
            x = 110 + k * 78
            rrect(d, (x, 930, x + 58, 988), 8, fill=rgba(mix(C_TEAL, BG, 1.0 - strength), 255 * fa), outline=rgba(C_TEAL, 255 * fa), width=2)
        text(d, (295, 1022), 'some chips come out stronger,', 20, rgba(C_GREY, 255 * fa), 'Medium', 'mm')
        text(d, (295, 1052), 'some weaker', 20, rgba(C_GREY, 255 * fa), 'Medium', 'mm')
    co = seg(t, T2['cond'], 0.5) * out
    if co > 0:
        card(d, (560, 850, 1010, 1090), co)
        text(d, (785, 890), 'the conditions', 25, rgba(C_WHITE, 255 * co), 'Bold', 'mm')
        text(d, (590, 950), 'cold · high voltage', 23, rgba(C_TEAL, 255 * co), 'SemiBold', 'lm')
        text(d, (980, 950), 'faster', 23, rgba(C_GREEN, 255 * co), 'Bold', 'rm')
        ho = seg(t, T2['hot'], 0.5) * out
        text(d, (590, 1020), 'hot · low voltage', 23, rgba(C_AMBER, 255 * ho), 'SemiBold', 'lm')
        text(d, (980, 1020), 'slower', 23, rgba(C_RED, 255 * ho), 'Bold', 'rm')
    z = seg(t, T2['speeds'], 0.6)
    if z > 0:
        text(d, (540, 815), 'system clock of this chip', 25, rgba(C_GREY, 255 * z), 'Medium', 'mm')
        for i, (name, tr, cond, ns, mhz, col) in enumerate(CORNERS):
            x0 = 70 + i * 320
            hl = seg(t, T2['rate'], 0.5) if i == 2 else 0.0
            card(d, (x0, 850, x0 + 300, 1090), z, col if (i < 2 or hl <= 0) else C_WHITE)
            text(d, (x0 + 150, 890), name.lower(), 23, rgba(col, 255 * z), 'Bold', 'mm')
            text(d, (x0 + 150, 960), f'{mhz:.1f}', 64, rgba(C_WHITE, 255 * z), 'Bold', 'mm')
            text(d, (x0 + 150, 1020), 'MHz', 25, rgba(C_GREY, 255 * z), 'Medium', 'mm')
            if hl > 0:
                pw = B.font(19).getlength('THE RATING') + 34
                pill(d, x0 + 150 - pw / 2, 1044, 'THE RATING', C_WHITE, hl, 19)
    q = seg(t, T2['rate'] + 1.0, 0.6)
    if q > 0:
        text(d, (540, 1130), 'every chip must work, also the weakest one on a hot day', 22, rgba(C_GREY, 255 * q), 'Medium', 'mm')


# ------------------------------------------------------------------ scene 3: input clock and system clock
T3 = dict(inp=2.2, gate=7.1, sys=11.4, logic=16.6, mem=20.3, why=26.3, why2=33.8, twice=40.3)
P = 96.0          # one input clock period in px
X0W, X1W = 250, 1010


def s_two(layer, t, dur):
    d = ImageDraw.Draw(layer)
    phase = -(t * 26.0) % (2 * P)
    a = seg(t, T3['inp'], 0.5)
    if a > 0:
        rrect(d, (70, 225, 225, 305), 10, fill=rgba(CARD, 255 * a), outline=rgba(C_BLUE, 255 * a), width=3)
        text(d, (147, 252), 'clock pad', 21, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
        text(d, (147, 281), 'from the board', 16, rgba(C_GREY, 255 * a), 'Medium', 'mm')
        sq_wave(d, X0W, X1W, 300, 235, P, P / 2, phase, rgba(C_BLUE, 255 * a), 5)
        text(d, (X0W, 205), 'INPUT CLOCK', 22, rgba(C_BLUE, 255 * a), 'Bold', 'lm')
    g = seg(t, T3['gate'], 0.5)
    if g > 0:
        arrow(d, (147, 305), (147, 392), rgba(C_BLUE, 255 * g), 4)
        rrect(d, (70, 395, 225, 490), 10, fill=rgba(CARD, 255 * g), outline=rgba(C_AMBER, 255 * g), width=3)
        text(d, (147, 425), 'clock gate', 21, rgba(C_WHITE, 255 * g), 'Bold', 'mm')
        text(d, (147, 458), 'every 2nd pulse', 16, rgba(C_GREY, 255 * g), 'Medium', 'mm')
    s = seg(t, T3['sys'], 0.5)
    if s > 0:
        sq_wave(d, X0W, X1W, 480, 415, 2 * P, P / 2, phase, rgba(C_AMBER, 255 * s), 5)
        text(d, (X0W, 385), 'SYSTEM CLOCK · half the rate', 22, rgba(C_AMBER, 255 * s), 'Bold', 'lm')
        # one system step = two input ticks: dashed guides at the pulse starts
        k0 = int(math.floor(-phase / (2 * P))) - 1
        for k in range(k0, k0 + 6):
            x = X0W + phase + k * 2 * P
            if X0W < x < X1W:
                for yy in range(225, 495, 14):
                    d.line([(x, yy), (x, yy + 6)], fill=rgba(C_DIM, 200 * s), width=2)
    # where "now" is inside the system step
    xn = 640.0
    pos = (xn - X0W - phase) % (2 * P)
    first = pos < P
    lg = seg(t, T3['logic'], 0.5)
    if lg > 0:
        card(d, (560, 560, 1010, 850), lg, C_AMBER)
        text(d, (785, 605), 'processor and logic', 28, rgba(C_WHITE, 255 * lg), 'Bold', 'mm')
        text(d, (785, 648), 'run on the system clock', 21, rgba(C_AMBER, 255 * lg), 'SemiBold', 'mm')
        on = pos < P / 2
        dot(d, (785, 735), C_AMBER if on else mix(C_AMBER, BG, .78), 34, lg)
        text(d, (785, 805), 'one step', 22, rgba(C_GREY, 255 * lg), 'Medium', 'mm')
    m = seg(t, T3['mem'], 0.5)
    if m > 0:
        card(d, (70, 560, 520, 850), m, C_BLUE)
        text(d, (295, 605), 'memory blocks', 28, rgba(C_WHITE, 255 * m), 'Bold', 'mm')
        text(d, (295, 648), 'most run on the input clock', 21, rgba(C_BLUE, 255 * m), 'SemiBold', 'mm')
        for j, (cx, lab) in enumerate(((200, 'access 1'), (390, 'access 2'))):
            on = (pos % P) < P / 2 and (first if j == 0 else not first)
            dot(d, (cx, 735), C_BLUE if on else mix(C_BLUE, BG, .78), 34, m)
            text(d, (cx, 805), lab, 22, rgba(C_GREY, 255 * m), 'Medium', 'mm')
    w = seg(t, T3['why'], 0.6)
    if w > 0:
        card(d, (70, 880, 1010, 1000), w)
        text(d, (540, 918), 'a memory block has one port: one read or one write per tick', 24, rgba(C_WHITE, 255 * w), 'SemiBold', 'mm')
        text(d, (540, 962), 'the design needs two per step', 24, rgba(C_AMBER, 255 * w * seg(t, T3['why2'], 0.5)), 'SemiBold', 'mm')
    z = seg(t, T3['twice'], 0.6)
    if z > 0:
        card(d, (70, 1025, 1010, 1115), z, C_AMBER)
        text(d, (540, 1070), 'system clock = input clock ÷ 2', 32, rgba(C_WHITE, 255 * z), 'Bold', 'mm')


# ------------------------------------------------------------------ scene 4: the input clock sets the limit
T4 = dict(step=2.6, full=6.7, half=10.4, tab=18.6, r1=20.5, r2=24.4, r3=26.3, dbl=28.3, res=33.0, fast=37.8)
ROWS = [('fast', 7.5, 18.3, 54.7, C_GREEN, 'logic'), ('typical', 11.0, 20.8, 45.5, C_AMBER, 'mem'),
        ('slow', 17.0, 29.6, 29.4, C_RED, 'mem')]


def s_limit(layer, t, dur):
    d = ImageDraw.Draw(layer)
    xa, xm, xb = 110, 540, 970
    a = seg(t, T4['step'], 0.5)
    if a > 0:
        for x, s in ((xa, 'input tick'), (xm, 'input tick'), (xb, 'input tick')):
            d.line([(x, 250), (x, 520)], fill=rgba(C_BLUE, 255 * a), width=4)
            text(d, (x, 228), s, 19, rgba(C_BLUE, 255 * a), 'SemiBold', 'mm')
        d.line([(xa, 300), (xb, 300)], fill=rgba(C_AMBER, 255 * a), width=4)
        for x in (xa, xb):
            d.line([(x, 288), (x, 312)], fill=rgba(C_AMBER, 255 * a), width=4)
        rrect(d, (400, 280, 680, 320), 8, fill=rgba(BG, 255 * a))
        text(d, (540, 300), 'one system step', 23, rgba(C_AMBER, 255 * a), 'Bold', 'mm')
    f = seg(t, T4['full'], 0.8)
    if f > 0:
        text(d, (xa + 14, 362), 'flip-flop to flip-flop: the whole step', 22, rgba(C_WHITE, 255 * f), 'SemiBold', 'lm')
        arrow(d, (xa, 400), (xa + f * (xb - xa - 4), 400), rgba(C_TEAL, 255 * f), 7, 18)
    h = seg(t, T4['half'], 0.8)
    if h > 0:
        text(d, (xa + 14, 442), 'flip-flop to memory: one input tick', 22, rgba(C_WHITE, 255 * h), 'SemiBold', 'lm')
        arrow(d, (xa, 480), (xa + h * (xm - xa - 4), 480), rgba(C_RED, 255 * h), 7, 18)
        if h >= 1.0:
            rrect(d, (xm + 12, 458, xm + 150, 502), 8, fill=rgba(mix(C_BLUE, BG, .6), 255), outline=rgba(C_BLUE, 255), width=2)
            text(d, (xm + 81, 480), 'memory', 20, rgba(C_WHITE, 255), 'SemiBold', 'mm')
            text(d, (xb - 6, 480), 'half a step', 21, rgba(C_RED, 255), 'Bold', 'rm')
    tb = seg(t, T4['tab'], 0.5)
    if tb > 0:
        card(d, (70, 560, 1010, 1010), tb)
        for x, s1, s2 in ((390, 'into a memory', 'one input tick'), (640, 'logic step', 'one system step'), (880, 'system clock', 'the result')):
            text(d, (x, 598), s1, 22, rgba(C_WHITE, 255 * tb), 'Bold', 'mm')
            text(d, (x, 628), s2, 17, rgba(C_GREY, 255 * tb), 'Medium', 'mm')
        d.line([(95, 652), (985, 652)], fill=rgba(EDGE, 255 * tb), width=2)
        for i, (name, mem, lg, mhz, col, lim) in enumerate(ROWS):
            e = seg(t, (T4['r1'], T4['r2'], T4['r3'])[i], 0.5)
            if e <= 0:
                continue
            y = 715 + i * 105
            text(d, (105, y), name, 29, rgba(col, 255 * e), 'Bold', 'lm')
            dbl = seg(t, T4['dbl'], 0.5) if lim == 'mem' else 0.0
            fst = seg(t, T4['fast'], 0.5) if lim == 'logic' else 0.0
            if dbl > 0:
                rrect(d, (285, y - 38, 495, y + 38), 12, outline=rgba(col, 255 * dbl), width=3)
            if fst > 0:
                rrect(d, (545, y - 38, 735, y + 38), 12, outline=rgba(col, 255 * fst), width=3)
            text(d, (390, y - (10 if dbl > 0 else 0)), f'{mem:.1f} ns', 30, rgba(C_WHITE, 255 * e), 'Bold', 'mm')
            if dbl > 0:
                text(d, (390, y + 22), f'x 2 = {2 * mem:.0f} ns', 18, rgba(col, 255 * dbl), 'SemiBold', 'mm')
            text(d, (640, y), f'{lg:.1f} ns', 30, rgba(C_WHITE, 255 * seg(t, T4['fast'] - 1.0, 0.5)), 'Bold', 'mm')
            text(d, (880, y), f'{mhz:.1f} MHz', 32, rgba(col, 255 * seg(t, T4['res'], 0.5)), 'Bold', 'mm')
    z = seg(t, T4['fast'] + 1.5, 0.6)
    if z > 0:
        text(d, (540, 1060), 'two input ticks or one logic step: the longer one sets the system step', 23, rgba(C_GREY, 255 * z), 'Medium', 'mm')
        text(d, (540, 1100), 'time needed on the routed wires of candidate v.2.4.0', 18, rgba(C_DIM, 255 * z), 'Medium', 'mm')


# ------------------------------------------------------------------ scene 5: why not 100 MHz
T5 = dict(c1=5.7, v1=10.7, v2=14.5, v3=17.0, c2=19.0, line=24.6, b1=27.6, b2=32.4, b3=34.2, gap=36.3, no=40.0)


def s_hundred(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, T5['c1'], 0.5)
    if a > 0:
        card(d, (70, 190, 1010, 470), a, C_BLUE)
        text(d, (100, 232), '100 MHz as INPUT clock', 30, rgba(C_BLUE, 255 * a), 'Bold', 'lm')
        text(d, (100, 276), 'what the chip was designed for · one tick = 10 ns', 21, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        for i, (name, mhz, col) in enumerate((('fast', 109, C_GREEN), ('typical', 91, C_AMBER), ('slow', 59, C_RED))):
            v = seg(t, (T5['v1'], T5['v2'], T5['v3'])[i], 0.6)
            x0 = 100 + i * 300
            text(d, (x0, 335), name, 22, rgba(col, 255 * v), 'Bold', 'lm')
            w = 270 * mhz / 120.0 * v
            d.rectangle((x0, 360, x0 + w, 392), fill=rgba(col, 230 * v))
            text(d, (x0, 425), f'{mhz} MHz', 30, rgba(C_WHITE, 255 * v), 'Bold', 'lm')
            xl = x0 + 270 * 100 / 120.0
            d.line([(xl, 350), (xl, 402)], fill=rgba(C_WHITE, 255 * v), width=3)
            if i == 0 and v > 0:
                text(d, (xl, 338), '100', 16, rgba(C_WHITE, 255 * v), 'SemiBold', 'mm')
    b = seg(t, T5['c2'], 0.5)
    if b > 0:
        card(d, (70, 500, 1010, 1000), b, C_RED)
        text(d, (100, 542), '100 MHz as SYSTEM clock', 30, rgba(C_RED, 255 * b), 'Bold', 'lm')
        text(d, (100, 586), 'needs a 200 MHz input clock · one tick = 5 ns', 21, rgba(C_GREY, 255 * b), 'Medium', 'lm')
        ln = seg(t, T5['line'], 0.5)
        x0, sc = 330, 32.0                     # px per ns
        if ln > 0:
            xl = x0 + 5 * sc
            d.line([(xl, 630), (xl, 905)], fill=rgba(C_WHITE, 255 * ln), width=4)
            text(d, (xl, 925), 'allowed: 5 ns', 21, rgba(C_WHITE, 255 * ln), 'Bold', 'mm')
            text(d, (100, 640), 'path into a memory', 21, rgba(C_GREY, 255 * ln), 'Medium', 'lm')
        for i, (name, ns, col, at) in enumerate((('fast', 7.5, C_GREEN, T5['b1']), ('typical', 11.0, C_AMBER, T5['b2']),
                                                 ('slow', 17.0, C_RED, T5['b3']))):
            e = seg(t, at, 0.8)
            if e <= 0:
                continue
            y = 690 + i * 75
            text(d, (100, y + 22), name, 26, rgba(col, 255), 'Bold', 'lm')
            w = ns * sc * e
            d.rectangle((x0, y, x0 + min(w, 5 * sc), y + 44), fill=rgba(mix(col, BG, .55), 255))
            if w > 5 * sc:
                d.rectangle((x0 + 5 * sc, y, x0 + w, y + 44), fill=rgba(col, 255))
            text(d, (x0 + ns * sc + 16, y + 22), f'{ns:.1f} ns', 26, rgba(C_WHITE, 255 * e), 'Bold', 'lm')
        gp = seg(t, T5['gap'], 0.6)
        if gp > 0:
            text(d, (540, 968), '1.5 to 3.4 times too slow', 28, rgba(C_WHITE, 255 * gp), 'Bold', 'mm')
    z = seg(t, T5['no'], 0.6)
    if z > 0:
        card(d, (70, 1030, 1010, 1120), z, C_AMBER)
        text(d, (540, 1075), 'no buffer and no better wire closes such a gap', 28, rgba(C_WHITE, 255 * z), 'Bold', 'mm')


# ------------------------------------------------------------------ scene 6: what the wires gave
T6 = dict(v1=3.3, v2=9.8, v3=11.0, v4=12.3, card=19.8, a=24.3, b=29.5)
HIST = [('v.2.0.1', 'first clean chip', (15.0, 12.7, 10.0)), ('v.2.2.0', 'straight routes', (45.7, 30.0, 18.9)),
        ('v.2.3.0', 'strong buffers', (54.2, 44.3, 28.7)), ('v.2.4.0', 'clock generator', (54.7, 45.5, 29.4))]


def s_hist(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.5, 0.5)
    text(d, (540, 200), 'system clock in MHz: fast, typical, slow', 25, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    base, top, vmax = 760, 290, 60.0
    d.line([(85, base), (995, base)], fill=rgba(C_DIM, 255 * a), width=2)
    for i, (ver, what, vals) in enumerate(HIST):
        e = seg(t, (T6['v1'], T6['v2'], T6['v3'], T6['v4'])[i], 0.9)
        if e <= 0:
            continue
        gx = 105 + i * 225
        for j, (v, col) in enumerate(zip(vals, (C_GREEN, C_AMBER, C_RED))):
            h = (base - top) * v / vmax * e
            x = gx + j * 62
            d.rectangle((x, base - h, x + 54, base), fill=rgba(col, 235))
            text(d, (x + 27, base - h - 18), f'{v:.1f}', 19, rgba(C_WHITE, 255 * e), 'Bold', 'mm')
        text(d, (gx + 89, base + 30), ver, 24, rgba(C_WHITE, 255 * e), 'Bold', 'mm')
        text(d, (gx + 89, base + 62), what, 17, rgba(C_GREY, 255 * e), 'Medium', 'mm')
    z = seg(t, T6['card'], 0.6)
    if z > 0:
        card(d, (70, 870, 1010, 1120), z, C_PURPLE)
        text(d, (100, 912), 'beyond this: a change of the design, not of the wires', 25, rgba(C_WHITE, 255 * z), 'Bold', 'lm')
    for at, y, s in ((T6['a'], 972, 'memories with two ports: the double-rate clock disappears'),
                     (T6['b'], 1030, 'shorter logic steps')):
        e = seg(t, at, 0.5)
        if e > 0:
            dot(d, (118, y), C_PURPLE, 8, e)
            text(d, (145, y), s, 24, rgba(C_WHITE, 255 * e), 'Medium', 'lm')
    q = seg(t, T6['b'] + 1.8, 0.5)
    if q > 0:
        text(d, (145, 1084), 'that is for a later chip', 21, rgba(C_GREY, 255 * q), 'Medium', 'lm')


# ------------------------------------------------------------------ scene 7: summary
T7 = dict(a=1.0, b=6.2, c=13.5, d=18.0, e=20.8)


def s_sum(layer, t, dur):
    d = ImageDraw.Draw(layer)
    rows = [(T7['a'], C_BLUE, 'the board sets the speed', 'input clock at the pad · the system runs at half of it', ''),
            (T7['b'], C_RED, 'every chip', 'slow corner, by our timing analysis', '29.4 MHz'),
            (T7['c'], C_AMBER, 'a typical chip at room temperature', 'typical corner', '45.5 MHz'),
            (T7['d'], C_GREEN, 'the best chips', 'fast corner', '54.7 MHz')]
    for i, (at, col, k, v, num) in enumerate(rows):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 200 + i * 185
        card(d, (70, y, 1010, y + 160), e, col)
        text(d, (105, y + 58), k, 30, rgba(C_WHITE, 255 * e), 'Bold', 'lm')
        text(d, (105, y + 108), v, 21, rgba(C_GREY, 255 * e), 'Medium', 'lm')
        if num:
            text(d, (975, y + 62), num, 40, rgba(col, 255 * e), 'Bold', 'rm')
            text(d, (975, y + 112), f'input {2 * float(num.split()[0]):.1f} MHz', 20, rgba(C_GREY, 255 * e), 'Medium', 'rm')
    z = seg(t, T7['e'], 0.6)
    if z > 0:
        card(d, (70, 950, 1010, 1110), z, C_WHITE)
        text(d, (540, 1005), '100 MHz as a system clock', 30, rgba(C_WHITE, 255 * z), 'Bold', 'mm')
        text(d, (540, 1058), 'not possible on this chip', 30, rgba(C_RED, 255 * z), 'Bold', 'mm')


def s_end(layer, t, dur):
    fp = B.FP(340, 420, 400); B.draw_die(layer, fp, dim=True)
    d = ImageDraw.Draw(layer)
    text(d, (540, 900), 'SoC2611', 40, C_WHITE, 'Bold', 'mm')
    text(d, (540, 955), 'clocks and speed explained · 13 November 2026', 24, C_GREY, 'Medium', 'mm')


SCENES = [
    ('Clocks and speed', s_title,
     'This film explains the clock of {S o C twenty six eleven|SoC2611}, in plain words. First, what a clock is. '
     'Then, why we quote three speeds: fast, typical and slow. Then, the two clocks of this chip, the input clock and '
     'the system clock. And last, why {one hundred megahertz|100 MHz} is out of reach.'),
    ('The clock is a beat', s_beat,
     'A chip works to a beat, like a band to a metronome. That beat is the clock. On every tick, a flip-flop, which is '
     'a store for one bit, passes its value on. The signal then travels through logic gates and wires to the next '
     'flip-flop. It must arrive before the next tick. With a slow beat, it arrives in time. '
     'Now we speed the beat up. The next tick comes while the signal is still on its way. The flip-flop stores a wrong '
     'value, and the chip makes a mistake. '
     'So the slowest path on the chip sets the fastest beat. '
     'The beat is counted in megahertz: one megahertz is one million ticks per second.'),
    ('Fast, typical, slow', s_corners,
     'Why three speeds? Because no two chips are the same. The factory makes some chips with stronger transistors and '
     'some with weaker ones. And every chip is faster when it is cold and its supply voltage is high, and slower when '
     'it is hot and the voltage is low. So we time the same design three times. '
     'Fast: strong transistors, {one point three two|1.32} volts, {minus forty|-40} degrees. '
     'Typical: average transistors, {one point two|1.2} volts, room temperature. '
     'Slow: weak transistors, {one point zero eight|1.08} volts, {one hundred and twenty-five|125} degrees. '
     'The same path takes {eighteen|18} nanoseconds in the fast corner, and {thirty|30} in the slow one. '
     'For this chip, that gives a system clock of {fifty-four point seven|54.7} megahertz fast, '
     '{forty-five point five|45.5} typical, and {twenty-nine point four|29.4} slow. '
     'The slow number is the rating, because every chip must work, also the weakest one on a hot day.'),
    ('Input clock and system clock', s_two,
     'This chip has two clocks. The board sends one clock into a pad. That is the input clock. '
     'Inside, a small gate lets only every second pulse through. '
     'That is the system clock. It runs at half the rate. '
     'The processor and the logic run on the system clock. '
     'Most of the memory blocks run on the input clock. '
     'The reason is the memory itself. A memory block has a single port. It can do one thing per tick: one read, or '
     'one write. But the design needs two per step. '
     'So the memories tick twice, while the logic ticks once. The system clock is always the input clock, divided by two.'),
    ('The input clock sets the limit', s_limit,
     'Here is how the input clock limits the speed. One system step is two input ticks. '
     'A signal from one flip-flop to the next may use the whole step. '
     'But a signal that goes into a memory must arrive within one input tick. That is half a step, because the memory '
     'ticks at the double rate. '
     'On this chip, that path needs {seven and a half|7.5} nanoseconds in the fast corner, '
     '{eleven|11} in the typical corner, '
     'and {seventeen|17} in the slow corner. '
     'Double it, and you have the shortest system step: {thirty-four|34} nanoseconds in the slow corner. That is '
     '{twenty-nine point four|29.4} megahertz. '
     'In the fast corner, a long logic path limits first, at {eighteen|18} nanoseconds for a whole step.'),
    ('Why not 100 MHz?', s_hundred,
     'So why not {one hundred megahertz|100 MHz}? There are two different {one hundred megahertz|100 MHz}. '
     'As an input clock, {one hundred megahertz|100 MHz} is what this chip was designed for. '
     'The best chips reach it, at {one hundred and nine|109}. A typical chip reaches {ninety-one|91}, and the weakest '
     '{fifty-nine|59}. '
     'As a system clock, {one hundred megahertz|100 MHz} would need an input clock of {two hundred|200}. '
     'One tick would be {five|5} nanoseconds. '
     'But the path into a memory needs {seven and a half|7.5} nanoseconds even on the best chip, '
     '{eleven|11} on a typical one, and {seventeen|17} on the weakest. '
     'That is one and a half to three and a half times too slow. '
     'No buffer, and no better wire, closes such a gap.'),
    ('What the wires gave us', s_hist,
     'What better wires and buffers can give, they have given. The first clean chip ran at {fifteen|15} megahertz in '
     'the fast corner, and {ten|10} in the slow one. Straight routes, strong buffers, and a fix of the clock generator '
     'brought it to {fifty-four point seven|54.7} fast, {forty-five point five|45.5} typical, and '
     '{twenty-nine point four|29.4} slow. '
     'Going beyond that needs a change of the design, not of the wires. '
     'Memories with two ports, so that the double-rate clock disappears. And shorter logic steps. That is for a later chip.'),
    ('In short', s_sum,
     'In short. The board sets the speed with the input clock, and the system runs at half of it. '
     'By our timing analysis, every chip works with a system clock of {twenty-nine|29} megahertz, which is an input '
     'clock of {fifty-eight|58}. '
     'A typical chip at room temperature reaches {forty-five|45}. '
     'The best chips reach {fifty-four|54}. '
     'A system clock of {one hundred megahertz|100 MHz} is not possible on this chip.'),
    ('', s_end, ''),
]

if __name__ == '__main__':
    B.SCENES = SCENES
    B.main()
