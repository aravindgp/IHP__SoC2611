#!/usr/bin/env python3
"""Explainer video of 11 November 2026: what an antenna violation is (plain words, then engineering terms), why the
chip has about 6,100 of them, how they are repaired (a diode at the gate pin) and what happens if the chip is handed
in without the repair. Same renderer, captions and voice (en-GB-RyanNeural) as make_status_video.py, whose
helpers are imported; only the scenes are new.
Numbers: antenna report of the routed candidate (6,111 nets, 7,212 gate pins, worst factor 58.7; 2,397 nets >= 2x,
136 >= 10x), rule table of the technology LEF (cumulative metal / gate area <= 200; with diffusion the PWL
( 0.16 um2 3200 ) ( 100 um2 2000000 ), diode cell 2.0154 um2 -> about 40,000), median gate area of the cell library
0.24 um2, Metal3 width 0.20 um (0.24 * 200 / 0.20 = 240 um of wire).
usage: make_antenna_video.py <out_dir> [--preview] [--jobs N]     (writes <out_dir>/SoC2611_status.mp4)"""
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
SIL = mix(C_BLUE, BG, .72)


def card(d, box, a, outline=EDGE):
    rrect(d, box, 18, fill=rgba(CARD, 235 * a), outline=rgba(outline, 255 * a), width=2)


def plen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def along(pts, dist):
    """point at distance dist along the polyline, and whether its end is reached"""
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if dist <= L:
            return (a[0] + (b[0] - a[0]) * dist / L, a[1] + (b[1] - a[1]) * dist / L), False
        dist -= L
    return pts[-1], True


def gate_cell(d, x, y, a, ox_col, label='gate', w=64):
    """a transistor gate in cross-section; (x, y) = centre of the thin oxide"""
    rrect(d, (x - w, y - 68, x + w, y - 7), 6, fill=rgba(CARD, 255 * a), outline=rgba(C_WHITE, 255 * a), width=2)
    text(d, (x, y - 38), label, 24, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
    d.rectangle((x - w, y - 7, x + w, y + 7), fill=rgba(ox_col, 255 * a))


def silicon(d, x0, x1, y, a, h=84):
    rrect(d, (x0, y + 7, x1, y + 7 + h), 10, fill=rgba(SIL, 255 * a), outline=rgba(C_DIM, 255 * a), width=2)
    text(d, ((x0 + x1) / 2, y + 7 + h / 2), 'silicon', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')


def dot(d, p, col, r=8):
    d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=rgba(col))


def spark(d, x, y, a):
    pts = [(x - 6, y - 14), (x + 10, y - 2), (x - 8, y + 6), (x + 8, y + 22), (x - 4, y + 34)]
    d.line(pts, fill=rgba(C_RED, 255 * a), width=5)


def plasma_band(d, t, a, y0=205, y1=300):
    rrect(d, (130, y0, 950, y1), 20, fill=rgba(mix(C_PURPLE, BG, .78), 255 * a), outline=rgba(C_PURPLE, 160 * a), width=2)
    text(d, (540, (y0 + y1) / 2), 'plasma: a charged gas that cuts the metal', 24, rgba(C_WHITE, 230 * a), 'SemiBold', 'mm')


# charges of the two wire scenes: (start time step, x where it lands on the wire)
NCH = 30
LAND = [170 + (i * 97) % 560 for i in range(NCH)]


def charges(d, t, t0, dt, wire_y, path_from, col, y_top=300, fall=0.55, v=430.0):
    """rain NCH charges onto the wire; each then follows path_from(x_land) (a polyline); returns how many arrived"""
    done = 0
    for i in range(NCH):
        u = t - (t0 + i * dt)
        if u < 0:
            continue
        x0 = LAND[i]
        if u < fall:
            dot(d, (x0, y_top + (wire_y - y_top) * u / fall), col)
            continue
        p, end = along(path_from(x0), (u - fall) * v)
        if end:
            done += 1
        else:
            dot(d, p, col)
    return done


# ------------------------------------------------------------------ scenes
def s_title(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.5, 0.7)
    if a > 0:
        y = 330 + (1 - a) * 30
        rrect(d, (190, y - 130, 890, y + 150), 26, fill=rgba(CARD, 240 * a), outline=rgba(C_AMBER, 255 * a), width=3)
        text(d, (540, y - 20), '6,111', 130, rgba(C_AMBER, 255 * a), 'Bold', 'mm')
        text(d, (540, y + 95), 'wires above the antenna limit', 28, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    for i, (q, at) in enumerate((('What is an antenna violation?', 5.9), ('Why are there so many?', 8.3),
                                 ('What if we hand in the chip with them?', 10.8))):
        b = seg(t, at, 0.5)
        if b > 0:
            yy = 580 + i * 130
            card(d, (120 + (1 - b) * 40, yy, 960 + (1 - b) * 40, yy + 104), b)
            text(d, (540 + (1 - b) * 40, yy + 52), q, 32, rgba(C_WHITE, 255 * b), 'Bold', 'mm')
    c = seg(t, 14.3, 0.6)
    if c > 0:
        text(d, (540, 1020), 'plain words first, then the engineering', 26, rgba(C_GREY, 255 * c), 'Medium', 'mm')


def s_plain(layer, t, dur):
    d = ImageDraw.Draw(layer)
    wy, xg, yg = 470, 840, 690
    a = seg(t, 0.3, 0.5)
    silicon(d, 690, 990, yg, a)
    # the wire grows
    g = seg(t, 1.0, 2.0)
    x_left = 840 - 700 * g
    d.line([(x_left, wy), (xg, wy), (xg, yg - 68)], fill=rgba(C_WHITE, 230 * a), width=7)
    text(d, (160, wy + 40), 'a long metal wire', 24, rgba(C_GREY, 255 * g), 'Medium', 'lm')
    pa = seg(t, 3.6, 0.6)
    if pa > 0:
        plasma_band(d, t, pa)
    n = charges(d, t, 8.0, 0.6, wy, lambda x0: [(x0, wy), (xg, wy), (xg, yg - 60)], C_AMBER) if t > 8.0 else 0
    hot = min(1.0, n / 30.0)
    ox = mix(C_TEAL, C_RED, hot)
    gate_cell(d, xg, yg, a, ox)
    if n > 0:
        for k in range(min(n, 30)):                                                  # the charge piles up above the gate
            dot(d, (xg - 30 + (k % 4) * 20, yg - 82 - (k // 4) * 16), C_AMBER, 6)
    b = seg(t, 21.3, 0.5)
    if b > 0:
        text(d, (300, yg - 10), 'one way out:', 26, rgba(C_WHITE, 255 * b), 'Bold', 'mm')
        text(d, (300, yg + 28), 'through the gate', 26, rgba(C_WHITE, 255 * b), 'Bold', 'mm')
        d.line([(455, yg), (760, yg)], fill=rgba(C_AMBER, 255 * b), width=3)
        d.polygon([(772, yg), (754, yg - 10), (754, yg + 10)], fill=rgba(C_AMBER, 255 * b))
    c = seg(t, 24.5, 0.5)
    if c > 0:
        text(d, (540, 850), 'under the gate: glass a few nanometres thick', 26, rgba(C_TEAL, 255 * c), 'SemiBold', 'mm')
    e = seg(t, 28.9, 0.4)
    if e > 0:
        spark(d, xg + 44, yg - 10, e)
        card(d, (150, 920, 930, 1080), e, C_RED)
        text(d, (540, 970), 'too much charge punches through', 32, rgba(C_RED, 255 * e), 'Bold', 'mm')
        text(d, (540, 1028), 'the transistor is damaged before the chip is finished', 24, rgba(C_GREY, 255 * e), 'Medium', 'mm')


LAYERS = [('metal 4', 330), ('metal 3', 430), ('metal 2', 520), ('metal 1', 600)]


def s_eng(layer, t, dur):
    d = ImageDraw.Draw(layer)
    ys, xo, xg = 720, 250, 850
    a = seg(t, 0.3, 0.5)
    silicon(d, 100, 990, ys, a, 70)
    # output transistor (with its junction to the silicon) and the gate
    rrect(d, (xo - 80, ys - 68, xo + 80, ys - 7), 6, fill=rgba(CARD, 255 * a), outline=rgba(C_WHITE, 255 * a), width=2)
    text(d, (xo, ys - 38), 'output', 24, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
    alone = seg(t, 22.7, 0.6)
    w0 = seg(t, 1.5, 0.8) * (1 - seg(t, 10.6, 0.6))
    if w0 > 0:                                                                      # the finished wire: output to gate
        d.line([(xo, ys - 68), (xo, 560), (xg, 560), (xg, ys - 68)], fill=rgba(C_WHITE, 230 * w0), width=6)
        text(d, (550, 528), 'the finished wire', 22, rgba(C_GREY, 255 * w0), 'Medium', 'mm')
    gate_cell(d, xg, ys, a, mix(C_TEAL, C_RED, alone))
    j = seg(t, 5.2, 0.5)
    if j > 0:
        d.rectangle((xo - 80, ys - 7, xo + 80, ys + 7), fill=rgba(C_GREEN, 255 * j))
        text(d, (xo, ys + 108), 'junction to the silicon:', 22, rgba(C_GREEN, 255 * j), 'SemiBold', 'mm')
        text(d, (xo, ys + 138), 'charge leaks away safely', 22, rgba(C_GREEN, 255 * j), 'SemiBold', 'mm')
    b = seg(t, 10.8, 0.6)
    if b > 0:
        for name, y in LAYERS:
            d.line([(140, y), (960, y)], fill=rgba(EDGE, 255 * b), width=1)
            text(d, (128, y), name, 20, rgba(C_GREY, 255 * b), 'Medium', 'rm')
        d.line([(xo, ys - 68), (xo, 330)], fill=rgba(C_WHITE, 220 * b), width=6)       # output: via stack up to metal 4
        d.line([(xg, ys - 68), (xg, 430)], fill=rgba(C_WHITE, 220 * b), width=6)       # gate: via stack up to metal 3
    c = seg(t, 14.5, 2.5)
    if c > 0:
        x_end = xg - (xg - 380) * c
        d.line([(xg, 430), (x_end, 430)], fill=rgba(C_AMBER, 255), width=8)
        la = seg(t, 16.2, 0.5)
        text(d, (615, 396), 'long run on metal 3, tied to the gate', 22, rgba(C_AMBER, 255 * la), 'SemiBold', 'mm')
    if t > 18.0:
        for i in range(12):
            u = t - (18.0 + i * 0.4)
            if u < 0:
                continue
            p, end = along([(400 + (i % 10) * 40, 430), (xg, 430), (xg, ys - 60)], u * 300.0)
            if not end:
                dot(d, p, C_AMBER, 7)
    e = seg(t, 19.5, 0.6)
    if e > 0:
        for k in range(8):                                                          # the link made later: dashed
            x0 = xo + k * 17
            if k % 2 == 0:
                d.line([(x0, 330), (min(x0 + 17, 380), 330)], fill=rgba(C_GREY, 255 * e), width=6)
        for k in range(6):
            y0 = 330 + k * 17
            if k % 2 == 0:
                d.line([(380, y0), (380, min(y0 + 17, 430))], fill=rgba(C_GREY, 255 * e), width=6)
        text(d, (315, 262), 'link to the output:', 22, rgba(C_GREY, 255 * e), 'SemiBold', 'mm')
        text(d, (315, 292), 'made later, on metal 4', 22, rgba(C_GREY, 255 * e), 'SemiBold', 'mm')
    if alone > 0:
        text(d, (xg, ys + 108), 'until then: the gate is alone', 22, rgba(C_RED, 255 * alone), 'SemiBold', 'mm')
    f = seg(t, 26.0, 0.6)
    if f > 0:
        card(d, (90, 905, 990, 1110), f, C_AMBER)
        text(d, (540, 945), 'the antenna rule', 24, rgba(C_GREY, 255 * f), 'Medium', 'mm')
        text(d, (540, 995), 'metal tied to a gate  ÷  area of the gate  ≤  200', 30, rgba(C_WHITE, 255 * f), 'Bold', 'mm')
    h = seg(t, 33.0, 0.6)
    if h > 0:
        text(d, (540, 1060), 'with a diode on the wire: about 40,000', 28, rgba(C_GREEN, 255 * h), 'Bold', 'mm')


BARS = [('over the limit', 6111, '6,111', C_AMBER), ('over 2 times', 2397, '2,397', C_AMBER),
        ('over 10 times', 136, '136', C_RED), ('worst wire', 0, '59 x', C_RED)]


def s_why(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 4.0, 0.5)
    if a > 0:
        card(d, (90, 195, 990, 300), a, C_TEAL)
        text(d, (125, 247), 'a typical gate', 26, rgba(C_TEAL, 255 * a), 'Bold', 'lm')
        text(d, (955, 247), '0.24 square micrometres', 26, rgba(C_WHITE, 255 * a), 'Medium', 'rm')
    b = seg(t, 7.6, 0.5)
    if b > 0:
        # scale: the chip is 6.6 mm wide; the limit is reached after 0.24 mm of wire
        x0, x1, y = 140, 940, 395
        d.line([(x0, y), (x1, y)], fill=rgba(C_DIM, 255 * b), width=6)
        for x in (x0, x1):
            d.line([(x, y - 14), (x, y + 14)], fill=rgba(C_DIM, 255 * b), width=3)
        text(d, ((x0 + x1) / 2, y + 36), 'width of the chip: 6.6 mm', 22, rgba(C_GREY, 255 * seg(t, 12.0, 0.5)), 'Medium', 'mm')
        w = (x1 - x0) * 0.24 / 6.6
        d.line([(x0, y), (x0 + w * b, y)], fill=rgba(C_AMBER, 255), width=10)
        text(d, (x0, y - 36), '0.24 mm of wire is already too much', 24, rgba(C_AMBER, 255 * b), 'Bold', 'lm')
    c = seg(t, 15.2, 0.5)
    if c > 0:
        card(d, (90, 470, 990, 560), c)
        text(d, (540, 515), '298 memory blocks force long runs between them', 26, rgba(C_WHITE, 255 * c), 'SemiBold', 'mm')
    e = seg(t, 19.6, 0.5)
    if e > 0:
        card(d, (90, 580, 990, 670), e)
        text(d, (125, 625), '339,054 wires on the chip', 26, rgba(C_WHITE, 255 * e), 'SemiBold', 'lm')
        e2 = seg(t, 25.8, 0.5)
        text(d, (955, 625), 'over the limit: 1.8 %', 26, rgba(C_AMBER, 255 * e2), 'Bold', 'rm')
    base = 1075
    for i, (lab, v, num, col) in enumerate(BARS):
        g = seg(t, (22.5, 29.5, 33.6, 37.3)[i], 0.8)
        if g <= 0:
            continue
        if i == 0:
            d.line([(130, base), (950, base)], fill=rgba(C_DIM, 255 * g), width=2)
        x = 160 + i * 200
        h = 300 * (v / 6111.0) * g if v else 0
        if v:
            d.rectangle((x, base - max(h, 4), x + 130, base), fill=rgba(col, 230))
        text(d, (x + 65, base - max(h, 4) - 30), num, 36, rgba(C_WHITE if v else col, 255 * g), 'Bold', 'mm')
        text(d, (x + 65, base + 28), lab, 21, rgba(C_GREY, 255 * g), 'Medium', 'mm')


def diode_sym(d, x, y0, y1, a, col):
    """a diode from the wire (x, y0) down to the silicon (x, y1)"""
    ym = (y0 + y1) / 2
    d.line([(x, y0), (x, ym - 20)], fill=rgba(col, 255 * a), width=6)
    d.polygon([(x - 24, ym + 18), (x + 24, ym + 18), (x, ym - 20)], fill=rgba(col, 255 * a))
    d.line([(x - 26, ym - 22), (x + 26, ym - 22)], fill=rgba(col, 255 * a), width=6)
    d.line([(x, ym + 18), (x, y1)], fill=rgba(col, 255 * a), width=6)


FIX = [('7,212 gate pins get a diode', C_GREEN, 15.6), ('memory and pad pins: a small buffer at the pin', C_TEAL, 19.4),
       ('never on a clock pin', C_AMBER, 26.3), ('existing cells stay, only touched wires are re-routed', C_WHITE, 28.0)]


def s_fix(layer, t, dur):
    d = ImageDraw.Draw(layer)
    wy, xg, yg, xd = 420, 840, 620, 640
    a = seg(t, 0.3, 0.5)
    silicon(d, 520, 990, yg, a, 70)
    d.line([(140, wy), (xg, wy), (xg, yg - 68)], fill=rgba(C_WHITE, 230 * a), width=7)
    plasma_band(d, t, a, 205, 290)
    da = seg(t, 1.0, 0.7)
    if da > 0:
        diode_sym(d, xd, wy, yg + 7, da, C_GREEN)
        text(d, (xd - 44, (wy + yg) / 2), 'diode', 26, rgba(C_GREEN, 255 * da), 'Bold', 'rm')
    if t > 7.2:
        charges(d, t, 7.2, 0.36, wy, lambda x0: [(x0, wy), (xd, wy), (xd, yg + 40)], C_GREEN, y_top=290)
    gate_cell(d, xg, yg, a, C_TEAL)
    b = seg(t, 9.6, 0.5)
    if b > 0:
        text(d, (300, yg + 42), 'the charge drains into the silicon', 22, rgba(C_GREEN, 255 * b), 'SemiBold', 'mm')
        text(d, (xg, yg + 105), 'the gate stays safe', 22, rgba(C_TEAL, 255 * b), 'SemiBold', 'mm')
    nu = seg(t, 12.2, 0.5)
    if nu > 0:
        text(d, (300, yg + 105), 'in normal use: closed, does nothing', 22, rgba(C_GREY, 255 * nu), 'Medium', 'mm')
    for i, (s, col, at) in enumerate(FIX):
        e = seg(t, at, 0.5)
        if e > 0:
            y = 775 + i * 88
            card(d, (90 + (1 - e) * 40, y, 990 + (1 - e) * 40, y + 72), e, col)
            text(d, (540 + (1 - e) * 40, y + 36), s, 26, rgba(C_WHITE, 255 * e), 'SemiBold', 'mm')


RISK = [('The submission check', 'passes: antenna is not in the minimum rule set', 'PASS', C_GREEN, 2.6),
        ('Mild: up to 2 times the limit', '3,714 wires. Often survive. No promise', 'RISK', C_AMBER, 14.8),
        ('Strong: over 10 times the limit', '136 wires. Gate damage is likely', 'DAMAGE', C_RED, 20.5),
        ('On silicon', 'dead or leaking inputs, early failures, die to die', 'FAILS', C_RED, 23.9),
        ('After manufacturing', 'there is no repair', 'FINAL', C_RED, 35.8)]


def s_risk(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (k, v, st, col, at) in enumerate(RISK):
        a = seg(t, at, 0.5)
        if a <= 0:
            continue
        y = 200 + i * 182; dx = (1 - a) * 50
        card(d, (70 + dx, y, 1010 + dx, y + 158), a, col)
        text(d, (105 + dx, y + 56), k, 30, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
        text(d, (105 + dx, y + 108), v, 24, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        pw = B.font(20).getlength(st) + 34
        rrect(d, (985 + dx - pw, y + 18, 985 + dx, y + 50), 16, fill=rgba(col, 255 * a * .2))
        text(d, (985 + dx - pw / 2, y + 34), st, 20, rgba(col, 255 * a), 'Bold', 'mm')


PLAN = [('1', 'Hold repair on the real wires', 'the route is running', 'RUNNING', C_BLUE, 2.0),
        ('2', 'Antenna diodes on that same route', 'all 6,111 wires, so both close together', 'NEXT', C_TEAL, 4.4),
        ('3', 'A small final hold fix', 'the new routes move some wires', 'AFTER', C_PURPLE, 11.6),
        ('4', 'Fill, design rule check, release', 'deadline 15 November, 23:59 CET', 'AFTER', C_GREY, 17.0)]


def s_plan(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (n, k, v, st, col, at) in enumerate(PLAN):
        a = seg(t, at, 0.5)
        if a <= 0:
            continue
        y = 230 + i * 200
        card(d, (70, y, 1010, y + 170), a, col)
        d.ellipse((96, y + 57, 152, y + 113), fill=rgba(col, 255 * a))
        text(d, (124, y + 85), n, 30, rgba(BG, 255 * a), 'Bold', 'mm')
        text(d, (180, y + 62), k, 30, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
        text(d, (180, y + 112), v, 23, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        pw = B.font(20).getlength(st) + 34
        rrect(d, (985 - pw, y + 16, 985, y + 48), 16, fill=rgba(col, 255 * a * .2))
        text(d, (985 - pw / 2, y + 32), st, 20, rgba(col, 255 * a), 'Bold', 'mm')


def s_end(layer, t, dur):
    fp = B.FP(340, 420, 400); B.draw_die(layer, fp, dim=True)
    d = ImageDraw.Draw(layer)
    text(d, (540, 900), 'SoC2611', 40, C_WHITE, 'Bold', 'mm')
    text(d, (540, 955), 'antenna violations explained · 11 November 2026', 24, C_GREY, 'Medium', 'mm')


SCENES = [
    ('Antenna violations', s_title,
     'On {S o C twenty six eleven|SoC2611}, about six thousand one hundred wires are above the antenna limit. '
     'What is an antenna violation? Why are there so many? And what happens if we hand in the chip with them? '
     'First in plain words, then the engineering.'),
    ('In plain words', s_plain,
     'A chip is built layer by layer. Each metal layer is cut into wires with plasma, an electrically charged gas. '
     'While that happens, every piece of bare metal collects charge, the way a long rod collects it in a thunderstorm. '
     'The longer the wire, the more charge. If the wire ends on the gate of a transistor, the charge has one way out: '
     'through the gate. And the gate sits on a sheet of glass only a few nanometres thick. '
     'Too much charge punches through it.'),
    ('The engineering', s_eng,
     'The engineering. A wire normally joins an output to a gate. The output has a junction to the silicon, which lets '
     'charge leak away safely. But during manufacturing, the wire is not complete. On this chip, a long run on metal '
     'three is often already tied to the gate, while the link to the output is only made later, on a higher layer. '
     'Until then, the gate is alone. So the process sets a rule: the metal tied to a gate may be at most two hundred '
     'times the area of the gate. With a diode on the wire, the rule table allows about forty thousand.'),
    ('Why so many', s_why,
     'Why so many? The limit is strict. A typical gate here measures a quarter of a square micrometre. '
     'So a quarter of a millimetre of wire is already too much. The chip is six point six millimetres wide, and two '
     'hundred and ninety-eight memory blocks force long runs between them. Of three hundred and thirty-nine thousand '
     'wires, six thousand one hundred and eleven are over the limit. That is under two percent. Most are mild. '
     'Two thousand four hundred are more than twice the limit. One hundred and thirty-six are more than ten times. '
     'The worst is fifty-nine times.'),
    ('The repair: a diode', s_fix,
     'The repair is a diode. It is a tiny cell placed right beside the gate and tied to the same wire. '
     'During manufacturing, it gives the charge a safe path into the silicon. In normal use it stays closed and does '
     'nothing. About seven thousand two hundred gate pins get one. At a memory pin or a pad, we add a small buffer '
     'right at the pin, so the long wire ends on the buffer instead. Never on a clock pin. '
     'Every existing cell stays where it is, and only the touched wires are routed again.'),
    ('If we hand it in unrepaired', s_risk,
     'What if we hand in the chip without this repair? The submission check would pass. It runs the minimum rule set, '
     'and antenna is not part of it. So nobody would stop us. The risk shows up on silicon. '
     'A mild violation often survives, because the limit has margin, but there is no promise. '
     'A strong one is likely to damage its gate. A damaged gate means an input that is dead, or that leaks. '
     'The chip may fail at once, or work at first and fail early. And it differs from die to die. '
     'After manufacturing, there is no repair.'),
    ('The plan', s_plan,
     'So this is the plan. The hold repair is routing now. The antenna diodes go in on that same route, for all six '
     'thousand one hundred wires, so both close together. Then a small final hold fix, because the new routes move '
     'some wires. Then fill, the design rule check and the release. The deadline is the fifteenth of November.'),
    ('', s_end, ''),
]

if __name__ == '__main__':
    B.SCENES = SCENES
    B.main()
