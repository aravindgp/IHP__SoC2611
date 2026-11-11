#!/usr/bin/env python3
"""Explainer video of 11 November 2026: what the "pF" and "ns" of a wire mean (plain words, then engineering terms),
what the timing on the real routed wires found (detours, late clock, hold), how many violations are left and what is
being done. Same renderer, captions and voice (en-GB-RyanNeural) as make_status_video.py, whose helpers are
imported; only the scenes are new.
usage: make_wires_video_1111.py <out_dir> [--preview] [--jobs N]     (writes <out_dir>/SoC2611_status.mp4)"""
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


def plen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def draw_path(d, pts, frac, col, width=5):
    """draw the polyline up to frac of its length; returns the point reached"""
    tot = plen(pts) * max(0.0, min(1.0, frac)); cur = pts[0]
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L <= 0:
            continue
        if tot >= L:
            d.line([a, b], fill=col, width=width); tot -= L; cur = b
        else:
            cur = (a[0] + (b[0] - a[0]) * tot / L, a[1] + (b[1] - a[1]) * tot / L)
            d.line([a, cur], fill=col, width=width); break
    return cur


def node(d, x, y, label, col, a=1.0, w=120, h=70):
    rrect(d, (x - w / 2, y - h / 2, x + w / 2, y + h / 2), 14, fill=rgba(CARD, 255 * a), outline=rgba(col, 255 * a), width=3)
    text(d, (x, y), label, 24, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')


def card(d, box, a, outline=EDGE):
    rrect(d, box, 18, fill=rgba(CARD, 235 * a), outline=rgba(outline, 255 * a), width=2)


# ------------------------------------------------------------------ scenes
def s_title(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (big, sub, col) in enumerate((('pF', 'how much the wire holds', C_TEAL), ('ns', 'how late the signal arrives', C_AMBER))):
        a = seg(t, 0.5 + i * 0.8, 0.6)
        if a <= 0:
            continue
        x = 300 + i * 480; y = 430 + (1 - a) * 40
        rrect(d, (x - 190, y - 150, x + 190, y + 150), 26, fill=rgba(CARD, 240 * a), outline=rgba(col, 255 * a), width=3)
        text(d, (x, y - 30), big, 120, rgba(col, 255 * a), 'Bold', 'mm')
        text(d, (x, y + 90), sub, 24, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    b = seg(t, 2.6, 0.6)
    if b > 0:
        card(d, (140, 700, 940, 860), b)
        text(d, (540, 750), 'a net = one wire on the chip', 34, rgba(C_WHITE, 255 * b), 'Bold', 'mm')
        text(d, (540, 805), 'one output, the inputs it feeds, and the metal between them', 24, rgba(C_GREY, 255 * b), 'Medium', 'mm')
    c = seg(t, 4.2, 0.6)
    if c > 0:
        text(d, (540, 960), 'plain words first, then the engineering,', 26, rgba(C_GREY, 255 * c), 'Medium', 'mm')
        text(d, (540, 1000), 'then what we found and what we are doing', 26, rgba(C_GREY, 255 * c), 'Medium', 'mm')


def s_pipe(layer, t, dur):
    d = ImageDraw.Draw(layer)
    # short wire
    a = seg(t, 0.3, 0.5)
    y = 330
    node(d, 170, y, 'output', C_TEAL, a); node(d, 910, y, 'input', C_TEAL, a)
    d.line([(230, y), (850, y)], fill=rgba(C_DIM, 255 * a), width=6)
    ph = ((t - 1.0) % 2.2) / 0.5
    if t > 1.0 and ph <= 1.0:
        x = 230 + 620 * ph; d.ellipse((x - 13, y - 13, x + 13, y + 13), fill=rgba(C_GREEN))
    text(d, (540, y + 70), 'short wire: the signal is there at once', 26, rgba(C_GREEN, 255 * a), 'SemiBold', 'mm')
    # long wire
    b = seg(t, 3.2, 0.5)
    if b > 0:
        y2 = 640
        node(d, 170, y2, 'output', C_TEAL, b); node(d, 910, y2, 'input', C_TEAL, b)
        pts = [(230, y2)]
        for k in range(9):
            x = 290 + k * 62
            pts += [(x, y2), (x, y2 - 110 if k % 2 == 0 else y2 + 110), (x + 62, y2 - 110 if k % 2 == 0 else y2 + 110), (x + 62, y2)]
        pts.append((850, y2))
        d.line(pts, fill=rgba(C_DIM, 255 * b), width=6)
        ph2 = ((t - 4.0) % 5.0) / 4.0
        if t > 4.0 and ph2 <= 1.0:
            cur = draw_path(d, pts, ph2, rgba(C_AMBER, 230), 6)
            d.ellipse((cur[0] - 13, cur[1] - 13, cur[0] + 13, cur[1] + 13), fill=rgba(C_AMBER))
        text(d, (540, y2 + 170), 'long wire: it has to fill itself first, the signal is late', 26, rgba(C_AMBER, 255 * b), 'SemiBold', 'mm')
    c = seg(t, 7.0, 0.6)
    if c > 0:
        card(d, (110, 900, 970, 1060), c)
        text(d, (540, 950), 'like a pipe filling a bucket', 30, rgba(C_WHITE, 255 * c), 'Bold', 'mm')
        text(d, (540, 1005), 'pF = how much the pipe holds      ns = how late the water arrives', 24, rgba(C_GREY, 255 * c), 'Medium', 'mm')


FACTS = [('resistance', '0.44 ohm per micrometre of wire', C_BLUE),
         ('capacitance', '0.17 femtofarad per micrometre', C_TEAL),
         ('1 pF', 'is about 6 mm of wire', C_AMBER)]
BARS = [('0.2 mm', 0.0015, '0.002'), ('1 mm', 0.037, '0.04'), ('5 mm', 0.94, '0.9'), ('9 mm', 3.0, '3.0')]


def s_rc(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (k, v, col) in enumerate(FACTS):
        a = seg(t, 0.4 + i * 0.7, 0.5)
        if a <= 0:
            continue
        y = 215 + i * 92
        card(d, (90, y, 990, y + 76), a, col)
        text(d, (125, y + 38), k, 28, rgba(col, 255 * a), 'Bold', 'lm')
        text(d, (400, y + 38), v, 26, rgba(C_WHITE, 255 * a), 'Medium', 'lm')
    b = seg(t, 3.0, 0.5)
    if b > 0:
        text(d, (540, 540), 'delay of the wire alone, in ns', 26, rgba(C_GREY, 255 * b), 'SemiBold', 'mm')
        d.line([(150, 960), (930, 960)], fill=rgba(C_DIM, 255 * b), width=2)
        for i, (lab, v, num) in enumerate(BARS):
            a = seg(t, 3.6 + i * 0.7, 0.8)
            if a <= 0:
                continue
            x = 190 + i * 190; h = 330 * (v / 3.0) * a
            col = C_GREEN if v < 0.1 else (C_AMBER if v < 1.5 else C_RED)
            d.rectangle((x, 960 - max(h, 3), x + 120, 960), fill=rgba(col, 230))
            text(d, (x + 60, 960 - max(h, 3) - 26), num, 34, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
            text(d, (x + 60, 992), lab, 24, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    c = seg(t, 7.2, 0.6)
    if c > 0:
        text(d, (540, 1070), 'the delay grows with the SQUARE of the length', 28, rgba(C_AMBER, 255 * c), 'Bold', 'mm')


def s_found(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.3, 0.5)
    # a wide SRAM macro with a pin pair across it
    mx0, my0, mx1, my1 = 170, 470, 910, 560
    rrect(d, (mx0, my0, mx1, my1), 8, fill=rgba(mix(C_TEAL, BG, .55), 255 * a), outline=rgba(C_TEAL, 255 * a), width=2)
    text(d, (540, 515), 'SRAM macro: no way across on Metal2 or Metal4', 22, rgba(C_WHITE, 220 * a), 'SemiBold', 'mm')
    pa, pb = (520, 610), (520, 420)
    for p in (pa, pb):
        d.ellipse((p[0] - 12, p[1] - 12, p[0] + 12, p[1] + 12), fill=rgba(C_WHITE, 255 * a))
    b = seg(t, 1.6, 0.5)
    if b > 0:
        text(d, (300, 610), 'pins 180 um apart', 24, rgba(C_WHITE, 255 * b), 'SemiBold', 'mm')
        d.line([(520, 600), (520, 566)], fill=rgba(C_GREEN, 200 * b), width=3)
        d.line([(520, 464), (520, 432)], fill=rgba(C_GREEN, 200 * b), width=3)
    # the detour the router took (schematic)
    pts = [pa, (520, 660), (980, 660), (980, 1010), (110, 1010), (110, 250), (760, 250), (760, 330), (230, 330), (230, 390),
           (940, 390), (940, 300), (860, 300), (860, 420), (520, 420)]
    fr = seg(t, 3.0, 4.5)
    if fr > 0:
        cur = draw_path(d, pts, fr, rgba(C_RED, 235), 6)
        d.ellipse((cur[0] - 10, cur[1] - 10, cur[0] + 10, cur[1] + 10), fill=rgba(C_RED))
    c = seg(t, 7.0, 0.5)
    if c > 0:
        card(d, (150, 690, 930, 960), c, C_RED)
        text(d, (540, 735), 'the wire the router made: 9 mm', 30, rgba(C_RED, 255 * c), 'Bold', 'mm')
    for i, s in enumerate(('434 wires cost more than 1 ns each', 'the longest: 23 mm for pins 150 um apart', '16 clock wires cost more than 0.5 ns')):
        e = seg(t, 8.0 + i * 0.8, 0.5)
        if e > 0:
            text(d, (540, 795 + i * 52), s, 26, rgba(C_WHITE, 255 * e), 'Medium', 'mm')


def wave(d, x0, x1, y, xe, col, a, label, late=False):
    """a clock-like step: low until xe, high after"""
    text(d, (x0 - 14, y - 22), label, 22, rgba(C_GREY, 255 * a), 'Medium', 'rm')
    d.line([(x0, y), (xe, y), (xe, y - 48), (x1, y - 48)], fill=rgba(col, 255 * a), width=5)


def s_hold(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.3, 0.5)
    node(d, 280, 290, 'flip-flop A', C_TEAL, a, 200, 80); node(d, 800, 290, 'flip-flop B', C_TEAL, a, 200, 80)
    d.line([(380, 290), (700, 290)], fill=rgba(C_DIM, 255 * a), width=5)
    d.polygon([(700, 290), (682, 280), (682, 300)], fill=rgba(C_DIM, 255 * a))
    text(d, (540, 262), 'data', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    x0, x1 = 330, 960
    b = seg(t, 1.6, 0.5)
    if b > 0:
        wave(d, x0, x1, 520, 470, C_GREEN, b, 'beat at A')
    c = seg(t, 3.0, 0.5)
    if c > 0:
        text(d, (x0 - 14, 640 - 22), 'data at B', 22, rgba(C_GREY, 255 * c), 'Medium', 'rm')
        xe = 540
        d.line([(x0, 640), (xe - 14, 640), (xe + 14, 592), (x1, 592)], fill=rgba(C_WHITE, 255 * c), width=5)
        d.line([(x0, 592), (xe - 14, 592), (xe + 14, 640), (x1, 640)], fill=rgba(C_WHITE, 255 * c), width=5)
        text(d, (430, 616), 'old', 22, rgba(C_GREY, 255 * c), 'SemiBold', 'mm')
        text(d, (720, 616), 'new', 22, rgba(C_GREY, 255 * c), 'SemiBold', 'mm')
    e = seg(t, 4.6, 0.5)
    if e > 0:
        wave(d, x0, x1, 760, 470, C_DIM, e, 'beat at B, on time')
        d.line([(470, 500), (470, 772)], fill=rgba(C_GREEN, 110 * e), width=2)
        text(d, (470, 796), 'stores "old": correct', 20, rgba(C_GREEN, 255 * e), 'SemiBold', 'mm')
    f = seg(t, 6.4, 0.5)
    if f > 0:
        wave(d, x0, x1, 900, 660, C_RED, f, 'beat at B, late')
        d.line([(660, 580), (660, 912)], fill=rgba(C_RED, 140 * f), width=2)
        text(d, (660, 936), 'stores "new": one beat too early', 20, rgba(C_RED, 255 * f), 'SemiBold', 'mm')
    g = seg(t, 8.4, 0.6)
    if g > 0:
        card(d, (110, 980, 970, 1100), g, C_RED)
        text(d, (540, 1018), 'a hold violation: slowing the clock does not help', 26, rgba(C_WHITE, 255 * g), 'Bold', 'mm')
        text(d, (540, 1062), 'about 3,300 flip-flops hear the beat 0.5 to 2.8 ns late', 24, rgba(C_GREY, 255 * g), 'Medium', 'mm')


COUNTS = [('Routing shorts', '0', 'router, 0 violations', C_GREEN),
          ('Design rule check, no fill', '0', '23 of 23 rule tables', C_GREEN),
          ('Broken or shorted wires in the GDS', '0', 'all 334,548 wires traced', C_GREEN),
          ('Hold on the real wires, fast corner', '3,029', 'typical 1,503   slow 586', C_RED),
          ('Clock wires above 0.5 ns', '16', 'they make the beat late', C_RED),
          ('Wires above the antenna limit', '6,111', 'worst 2,397 in repair now', C_AMBER)]


def s_count(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (name, num, detail, col) in enumerate(COUNTS):
        a = seg(t, 0.4 + i * 0.9, 0.5)
        if a <= 0:
            continue
        y = 205 + i * 150; dx = (1 - a) * 50
        card(d, (70 + dx, y, 1010 + dx, y + 130), a, col)
        text(d, (105 + dx, y + 46), name, 28, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
        text(d, (105 + dx, y + 92), detail, 22, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        text(d, (975 + dx, y + 65), num, 58, rgba(col, 255 * a), 'Bold', 'rm')


PLAN = [('1', 'Short paths for the clock wires', 'long runs on the nearly empty top metal', 'RUNNING', C_BLUE),
        ('2', 'Hold repair on the real wires', 'small delay cells where data is too fast', 'TESTED', C_TEAL),
        ('3', 'Extract, time again, repeat', 'until the hold count is 0 at all three corners', 'NEXT', C_PURPLE),
        ('4', 'Antenna diodes at the gate pins', 'before the last, small hold fix', 'RUNNING', C_BLUE),
        ('5', 'Fill, design rule check, release', 'deadline 15 November, 23:59 CET', 'AFTER', C_GREY)]


def s_plan(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (n, k, v, st, col) in enumerate(PLAN):
        a = seg(t, 0.4 + i * 1.0, 0.5)
        if a <= 0:
            continue
        y = 210 + i * 172
        card(d, (70, y, 1010, y + 150), a, col)
        d.ellipse((96, y + 47, 152, y + 103), fill=rgba(col, 255 * a))
        text(d, (124, y + 75), n, 30, rgba(BG, 255 * a), 'Bold', 'mm')
        text(d, (180, y + 54), k, 28, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
        text(d, (180, y + 100), v, 22, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        pw = B.font(20).getlength(st) + 34
        rrect(d, (985 - pw, y + 16, 985, y + 48), 16, fill=rgba(col, 255 * a * .2))
        text(d, (985 - pw / 2, y + 32), st, 20, rgba(col, 255 * a), 'Bold', 'mm')


def s_end(layer, t, dur):
    fp = B.FP(340, 420, 400); B.draw_die(layer, fp, dim=True)
    d = ImageDraw.Draw(layer)
    text(d, (540, 900), 'SoC2611', 40, C_WHITE, 'Bold', 'mm')
    text(d, (540, 955), 'wires, clock and hold · 11 November 2026', 24, C_GREY, 'Medium', 'mm')


SCENES = [
    ('Picofarads and nanoseconds', s_title,
     'Two numbers came up today on {S o C twenty six eleven|SoC2611}: {picofarads|pF} and {nanoseconds|ns} on a wire. '
     'A net is simply one wire on the chip. It joins one output to the inputs it feeds. '
     'First in plain words, then the engineering, then what we found and what we are doing about it.'),
    ('In plain words', s_pipe,
     'Think of a wire as a pipe that fills a bucket. A short pipe fills at once, and the water is there. '
     'A long pipe has to fill itself first, so the water arrives late. '
     'The {picofarads|pF} say how much the pipe holds. The {nanoseconds|ns} say how late the water arrives.'),
    ('The engineering', s_rc,
     'In engineering terms, the wire has resistance and capacitance. On this chip, each micrometre of wire has about zero '
     'point four four ohms and zero point one seven femtofarads. So one picofarad is about six millimetres of wire. '
     'The delay grows with the square of the length. Two hundred micrometres cost almost nothing. '
     'Five millimetres cost nearly one nanosecond. Nine millimetres cost three.'),
    ('What we found', s_found,
     'Here is what we found. To remove the last routing shorts, the router took detours. '
     'These two pins are one hundred and eighty micrometres apart, on either side of a memory block that no wire can '
     'cross. The wire that joins them is nine millimetres long. '
     'Four hundred and thirty-four wires cost more than one nanosecond each. The longest is twenty-three millimetres. '
     'Sixteen of the slow wires carry the clock. We saw this only when we measured the real wires. '
     'Until this morning, the timing used estimates.'),
    ('Why a late clock matters', s_hold,
     'Why does that matter? The clock is the drum beat of the chip. On every beat, flip-flop A sends new data, and '
     'flip-flop B stores the old data. If B hears the beat on time, it stores the old value, which is correct. '
     'If B hears the beat late, the new data is already there, and B stores it one beat too early. '
     'That is a hold violation. Slowing the clock does not help. '
     'About three thousand three hundred flip-flops hear the beat late.'),
    ('The count today', s_count,
     'So where do we stand? Routing shorts: zero. Design rule violations: zero. '
     'Broken or shorted wires in the layout: zero, with every wire traced. '
     'Hold violations on the real wires: about three thousand at the fast corner. Those have to come down to zero. '
     'Sixteen clock wires are too slow, and they are the cause. '
     'And six thousand one hundred wires are above the antenna limit, with the worst in repair now.'),
    ('What we are doing', s_plan,
     'What we are doing. First, the slow clock wires get short paths, with the long runs on the top metal layer, which '
     'is nearly empty. Second, hold repair on the real wires: small delay cells where the data is too fast. '
     'Third, we extract and time again, and repeat until the count is zero at all three corners. '
     'The antenna diodes go in before the last, small hold fix. Then fill, design rule check and release. '
     'The deadline is the fifteenth of November.'),
    ('', s_end, ''),
]

if __name__ == '__main__':
    B.SCENES = SCENES
    B.main()
