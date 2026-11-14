#!/usr/bin/env python3
"""Video of 11 November 2026: HOW each problem was solved, WHY it existed and WHERE on the chip the fix sits.
Every topic has a map of the real chip with the real positions (the 42 clock wires that were re-laid, the 7,205
delay cells of the hold repair, the 7,213 antenna diodes and 1,315 buffers, the 50 wires that limit the speed) and,
below it, a small "why" and "how" animation.
Data (env SOC_VIDEO_DATA, default <this dir>/data_1111):
  eco_cells.txt    "H|D|B x y" in um (dump_eco_cells.tcl)
  CKG_guides.txt   "net layer x0 y0 x1 y1" in um, the direct guides of the clock wires (direct_guides.py)
  SPD_guides.txt   the same for the speed wires
Same renderer, captions and voice (en-GB-RyanNeural) as make_status_video.py.
usage: make_how_video.py <out_dir> [--preview] [--jobs N]     (writes <out_dir>/SoC2611_status.mp4)"""
import importlib.util
import math
import os
import random
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
DATA = os.environ.get('SOC_VIDEO_DATA', os.path.join(HERE, 'data_1111'))


def load_cells():
    out = {'H': [], 'D': [], 'B': []}
    f = os.path.join(DATA, 'eco_cells.txt')
    if os.path.exists(f):
        for l in open(f):
            p = l.split()
            if len(p) == 3 and p[0] in out:
                out[p[0]].append((float(p[1]), float(p[2])))
    rnd = random.Random(7)
    for k in out:
        rnd.shuffle(out[k])
    return out


def load_guides(name):
    nets = []; cur = None; boxes = None
    f = os.path.join(DATA, name)
    if os.path.exists(f):
        for l in open(f):
            p = l.split()
            if len(p) != 6:
                continue
            if p[0] != cur:
                cur = p[0]; boxes = []; nets.append(boxes)
            boxes.append((float(p[2]), float(p[3]), float(p[4]), float(p[5])))
    return nets


CELLS = load_cells()
CKG = load_guides('CKG_guides.txt')
SPD = load_guides('SPD_guides.txt')
MAP = B.FP(245, 190, 590)                      # the chip map of the topic scenes: 590 px, top of the content band


def card(d, box, a, outline=EDGE):
    rrect(d, box, 18, fill=rgba(CARD, 235 * a), outline=rgba(outline, 255 * a), width=2)


def dot(d, p, col, r=8, a=1.0):
    d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=rgba(col, 255 * a))


def chip(layer, fp, a=1.0):
    """die outline and the memory blocks, dimmed, so that the overlays stand out"""
    d = ImageDraw.Draw(layer)
    x0, y0 = fp.px(0, B.DIE); x1, y1 = fp.px(B.DIE, 0)
    d.rectangle((x0, y0, x1, y1), fill=rgba((14, 19, 30), 255 * a), outline=rgba((70, 80, 100), 255 * a), width=2)
    for m in B.MACS:
        d.rectangle(fp.box(m), fill=rgba(mix(C_TEAL, BG, .72), 255 * a), outline=rgba(mix(C_TEAL, BG, .45), 255 * a))
    return d


def points(d, fp, pts, frac, col, r=1):
    n = int(len(pts) * max(0.0, min(1.0, frac)))
    c = rgba(col)
    for x, y in pts[:n]:
        px, py = fp.px(x, y)
        d.rectangle((px - r, py - r, px + r, py + r), fill=c)


def wires(d, fp, nets, frac, col, w=2):
    n = int(math.ceil(len(nets) * max(0.0, min(1.0, frac))))
    c = rgba(col)
    for boxes in nets[:n]:
        for b in boxes:
            x0, y0, x1, y1 = fp.box(b)
            if x1 - x0 < w:
                m = (x0 + x1) / 2; x0, x1 = m - w / 2, m + w / 2
            if y1 - y0 < w:
                m = (y0 + y1) / 2; y0, y1 = m - w / 2, m + w / 2
            d.rectangle((x0, y0, x1, y1), fill=c)


def legend(d, y, items, a):
    """coloured squares with labels on one line, centred"""
    f = B.font(22, 'Medium')
    tot = sum(30 + f.getlength(s) + 36 for s, c in items) - 36
    x = 540 - tot / 2
    for s, c in items:
        d.rectangle((x, y - 9, x + 18, y + 9), fill=rgba(c, 255 * a))
        text(d, (x + 30, y), s, 22, rgba(C_WHITE, 255 * a), 'Medium', 'lm')
        x += 30 + f.getlength(s) + 36


def why_how(d, t, t_why, t_how, why_cap, how_cap):
    """the two cards below the map; returns (a_why, a_how, origin of the why graphic, origin of the how graphic)"""
    aw = seg(t, t_why, 0.5); ah = seg(t, t_how, 0.5)
    if aw > 0:
        card(d, (70, 842, 530, 1118), aw, C_AMBER)
        text(d, (96, 870), 'WHY', 22, rgba(C_AMBER, 255 * aw), 'Bold', 'lm')
        text(d, (300, 1092), why_cap, 21, rgba(C_WHITE, 255 * aw), 'SemiBold', 'mm')
    if ah > 0:
        card(d, (550, 842, 1010, 1118), ah, C_GREEN)
        text(d, (576, 870), 'HOW', 22, rgba(C_GREEN, 255 * ah), 'Bold', 'lm')
        text(d, (780, 1092), how_cap, 21, rgba(C_WHITE, 255 * ah), 'SemiBold', 'mm')
    return aw, ah, (90, 885), (570, 885)


def path_len(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def draw_path(d, pts, frac, col, width=5):
    tot = path_len(pts) * max(0.0, min(1.0, frac)); cur = pts[0]
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


def result(d, t, at, s, col=C_GREEN):
    a = seg(t, at, 0.5)
    if a > 0:
        rrect(d, (245, 786, 835, 830), 14, fill=rgba(col, 46 * a), outline=rgba(col, 255 * a), width=2)
        text(d, (540, 808), s, 23, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')


# ------------------------------------------------------------------ scenes
def s_map(layer, t, dur):
    fp = B.FP(170, 200, 740)
    a = seg(t, 0.3, 0.6)
    d = ImageDraw.Draw(layer)
    x0, y0 = fp.px(0, B.DIE); x1, y1 = fp.px(B.DIE, 0)
    d.rectangle((x0, y0, x1, y1), fill=rgba((14, 19, 30), 255 * a), outline=rgba((70, 80, 100), 255 * a), width=2)
    n = int(len(B.MACS) * min(1.0, max(0.0, (t - 2.0) / 4.5)))
    for m in B.MACS[:n]:
        d.rectangle(fp.box(m), fill=rgba(mix(C_TEAL, BG, .5)), outline=rgba(mix(C_TEAL, C_WHITE, .2)))
    b = seg(t, 4.6, 0.5)
    if b > 0:
        d.line([(x0, y1 + 22), (x1, y1 + 22)], fill=rgba(C_GREY, 255 * b), width=2)
        for x in (x0, x1):
            d.line([(x, y1 + 12), (x, y1 + 32)], fill=rgba(C_GREY, 255 * b), width=2)
        text(d, (540, y1 + 50), '6.6 mm', 26, rgba(C_WHITE, 255 * b), 'Bold', 'mm')
    c = seg(t, 7.2, 0.5)
    if c > 0:
        text(d, (540, 1040), '298 memory blocks', 28, rgba(C_TEAL, 255 * c), 'Bold', 'mm')
    e = seg(t, 10.8, 0.5)
    if e > 0:
        text(d, (540, 1084), 'logic cells and most wires share the channels between them', 23, rgba(C_GREY, 255 * e), 'Medium', 'mm')


def g_block(d, o, a, col=C_TEAL, lx=210):
    x, y = o
    rrect(d, (x + 110, y + 50, x + 310, y + 120), 6, fill=rgba(mix(col, BG, .6), 255 * a), outline=rgba(col, 255 * a), width=2)
    text(d, (x + lx, y + 85), 'memory', 20, rgba(C_WHITE, 220 * a), 'SemiBold', 'mm')
    for p in ((x + 210, y + 146), (x + 210, y + 24)):
        dot(d, p, C_WHITE, 7, a)


def s_clock(layer, t, dur):
    d = chip(layer, MAP)
    fr = min(1.0, max(0.0, (t - 2.5) / 4.0))
    wires(d, MAP, CKG, fr, C_AMBER if t < 24.3 else C_GREEN, 3)
    legend(d, 808, [('the 42 clock wires we laid again', C_AMBER if t < 24.3 else C_GREEN)], seg(t, 2.5, 0.5) * (1 - seg(t, 36.4, 0.4)))
    aw, ah, ow, oh = why_how(d, t, 7.0, 24.3, 'a detour: the clock arrives late', 'a direct path on the top metal')
    if aw > 0:
        g_block(d, ow, aw)
        x, y = ow
        det = [(x + 210, y + 146), (x + 210, y + 168), (x + 395, y + 168), (x + 395, y + 4), (x + 30, y + 4), (x + 30, y + 150),
               (x + 80, y + 150), (x + 80, y + 36), (x + 210, y + 36), (x + 210, y + 24)]
        draw_path(d, det, (t - 11.0) / 5.0, rgba(C_RED, 255 * aw), 5)
    if ah > 0:
        g_block(d, oh, ah, lx=160)
        x, y = oh
        draw_path(d, [(x + 210, y + 146), (x + 210, y + 24)], (t - 27.6) / 1.5, rgba(C_GREEN, 255 * ah), 7)
    result(d, t, 36.9, 'slow clock wires: from 16 down to 2')


def g_ff(d, o, a, delay=0.0):
    x, y = o
    for cx, lab in ((x + 60, 'A'), (x + 360, 'B')):
        rrect(d, (cx - 42, y + 50, cx + 42, y + 120), 10, fill=rgba(CARD, 255 * a), outline=rgba(C_TEAL, 255 * a), width=3)
        text(d, (cx, y + 85), lab, 28, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
    d.line([(x + 102, y + 85), (x + 318, y + 85)], fill=rgba(C_DIM, 255 * a), width=5)
    if delay > 0:
        rrect(d, (x + 160, y + 60, x + 260, y + 110), 8, fill=rgba(CARD, 255 * delay), outline=rgba(C_GREEN, 255 * delay), width=3)
        text(d, (x + 210, y + 85), 'delay', 20, rgba(C_WHITE, 255 * delay), 'SemiBold', 'mm')


def s_hold(layer, t, dur):
    d = chip(layer, MAP)
    points(d, MAP, CELLS['H'], (t - 2.2) / 5.0, C_AMBER)
    legend(d, 808, [('7,205 delay cells of the hold repair', C_AMBER)], seg(t, 2.2, 0.5) * (1 - seg(t, 33.0, 0.4)))
    aw, ah, ow, oh = why_how(d, t, 10.4, 25.3, 'new data is there before the late clock', 'a delay cell on every fast path')
    if aw > 0:
        g_ff(d, ow, aw)
        x, y = ow
        ph = ((t - 11.4) % 2.4) / 0.7                                     # the data runs fast, the clock mark at B comes later
        if t > 11.4 and ph <= 1.0:
            dot(d, (x + 102 + 216 * ph, y + 85), C_RED, 9, aw)
        text(d, (x + 360, y + 30), 'clock: late', 19, rgba(C_RED, 255 * aw), 'SemiBold', 'mm')
        text(d, (x + 210, y + 150), 'data: too early', 19, rgba(C_RED, 255 * aw), 'SemiBold', 'mm')
    if ah > 0:
        g_ff(d, oh, ah, ah)
        x, y = oh
        ph = ((t - 26.3) % 3.0) / 1.9
        if t > 26.3 and ph <= 1.0:
            dot(d, (x + 102 + 216 * ph, y + 85), C_GREEN, 9, ah)
        text(d, (x + 210, y + 150), 'data arrives after the beat', 19, rgba(C_GREEN, 255 * ah), 'SemiBold', 'mm')
    result(d, t, 33.5, 'failing inputs: 1,771 down to 1 inside the chip')


def g_gate(d, o, a, ox_col):
    x, y = o
    d.line([(x + 20, y + 40), (x + 330, y + 40), (x + 330, y + 78)], fill=rgba(C_WHITE, 230 * a), width=6)
    rrect(d, (x + 280, y + 78, x + 380, y + 122), 6, fill=rgba(CARD, 255 * a), outline=rgba(C_WHITE, 255 * a), width=2)
    text(d, (x + 330, y + 100), 'gate', 20, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
    d.rectangle((x + 280, y + 122, x + 380, y + 132), fill=rgba(ox_col, 255 * a))
    rrect(d, (x + 200, y + 132, x + 400, y + 166), 6, fill=rgba(mix(C_BLUE, BG, .72), 255 * a), outline=rgba(C_DIM, 255 * a), width=1)
    text(d, (x + 300, y + 149), 'silicon', 17, rgba(C_GREY, 255 * a), 'Medium', 'mm')


def s_ant(layer, t, dur):
    d = chip(layer, MAP)
    points(d, MAP, CELLS['D'], (t - 2.2) / 4.5, C_GREEN)
    points(d, MAP, CELLS['B'], (t - 6.8) / 3.0, C_BLUE)
    legend(d, 808, [('7,213 diodes', C_GREEN), ('1,315 buffers', C_BLUE)], seg(t, 2.2, 0.5) * (1 - seg(t, 33.0, 0.4)))
    aw, ah, ow, oh = why_how(d, t, 13.3, 24.7, 'charge on a long wire hits the gate', 'a diode drains it, the wire keeps its path')
    if aw > 0:
        x, y = ow
        hot = min(1.0, max(0.0, (t - 15.0) / 8.0))
        g_gate(d, ow, aw, mix(C_TEAL, C_RED, hot))
        for k in range(9):
            ph = ((t - 14.3) * 0.5 + k / 9.0) % 1.0
            if t > 14.3:
                p = (x + 20 + 310 * ph, y + 40) if ph < 0.9 else (x + 330, y + 40 + 380 * (ph - 0.9))
                dot(d, p, C_AMBER, 6, aw)
    if ah > 0:
        x, y = oh
        g_gate(d, oh, ah, C_TEAL)
        # the diode beside the gate: a short link from the wire down to the silicon
        d.line([(x + 240, y + 40), (x + 240, y + 76)], fill=rgba(C_GREEN, 255 * ah), width=5)
        d.polygon([(x + 224, y + 100), (x + 256, y + 100), (x + 240, y + 76)], fill=rgba(C_GREEN, 255 * ah))
        d.line([(x + 222, y + 74), (x + 258, y + 74)], fill=rgba(C_GREEN, 255 * ah), width=5)
        d.line([(x + 240, y + 100), (x + 240, y + 132)], fill=rgba(C_GREEN, 255 * ah), width=5)
        for k in range(7):
            ph = ((t - 25.7) * 0.5 + k / 7.0) % 1.0
            if t > 25.7:
                p = (x + 20 + 220 * ph / 0.75, y + 40) if ph < 0.75 else (x + 240, y + 40 + 92 * (ph - 0.75) / 0.25)
                dot(d, p, C_GREEN, 6, ah)
    result(d, t, 33.5, 'route: 203,334 conflicts, now about 1,500', C_BLUE)


def s_fill(layer, t, dur):
    d = chip(layer, MAP)
    # the rows between the memories fill up, from the bottom
    fr = min(1.0, max(0.0, (t - 2.4) / 4.0))
    if fr > 0:
        x0, y0 = MAP.px(300, 6300); x1, y1 = MAP.px(6300, 300)
        ys = y1 - (y1 - y0) * fr
        d.rectangle((x0, ys, x1, y1), fill=rgba(C_GREEN, 110))
        for m in B.MACS:
            bx = MAP.box(m)
            if bx[3] > ys:
                d.rectangle(bx, fill=rgba(mix(C_TEAL, BG, .72)), outline=rgba(mix(C_TEAL, BG, .45)))
    legend(d, 808, [('every cell row between the memories', C_GREEN)], seg(t, 2.4, 0.5) * (1 - seg(t, 17.8, 0.4)))
    aw, ah, ow, oh = why_how(d, t, 6.4, 13.3, 'gaps break the wells underneath', '1,080,061 filler cells close them')
    cells = [(20, 110), (170, 80), (300, 100)]
    gaps = [(130, 40), (250, 50)]
    for a_, o, filled in ((aw, ow, False), (ah, oh, True)):
        if a_ <= 0:
            continue
        x, y = o
        d.rectangle((x + 20, y + 122, x + 400, y + 132), fill=rgba(C_DIM, 255 * a_))
        for cx, w in cells:
            rrect(d, (x + cx, y + 40, x + cx + w, y + 120), 5, fill=rgba(CARD, 255 * a_), outline=rgba(C_TEAL, 255 * a_), width=2)
        for cx, w in gaps:
            if filled:
                g = seg(t, 14.3, 1.0)
                yy = y + 40 - (1 - g) * 40
                rrect(d, (x + cx + 2, yy, x + cx + w - 2, yy + 80), 5, fill=rgba(mix(C_GREEN, BG, .55), 255 * g), outline=rgba(C_GREEN, 255 * g), width=2)
            else:
                d.rectangle((x + cx + 5, y + 62, x + cx + w - 5, y + 98), outline=rgba(C_RED, 255 * a_), width=2)
    result(d, t, 18.2, 'density check with them: 0 violations')


def s_speed(layer, t, dur):
    d = chip(layer, MAP)
    fr = min(1.0, max(0.0, (t - 5.4) / 3.5))
    wires(d, MAP, SPD, fr, C_PURPLE, 3)
    legend(d, 808, [('the 50 wires that limit the clock', C_PURPLE)], seg(t, 5.4, 0.5) * (1 - seg(t, 31.0, 0.4)))
    aw, ah, ow, oh = why_how(d, t, 9.1, 22.1, 'half a cycle to reach a memory pin', 'a direct path for each of the 50')
    if aw > 0:
        x, y = ow
        # one clock cycle with the half-cycle window
        pts = [(x + 30, y + 80), (x + 30, y + 40), (x + 120, y + 40), (x + 120, y + 80), (x + 210, y + 80), (x + 210, y + 40),
               (x + 300, y + 40), (x + 300, y + 80), (x + 390, y + 80)]
        d.line(pts, fill=rgba(C_WHITE, 220 * aw), width=4)
        d.line([(x + 30, y + 104), (x + 120, y + 104)], fill=rgba(C_RED, 255 * aw), width=5)
        text(d, (x + 75, y + 126), 'half', 19, rgba(C_RED, 255 * aw), 'SemiBold', 'mm')
        d.line([(x + 30, y + 150), (x + 210, y + 150)], fill=rgba(C_GREY, 255 * aw), width=3)
        text(d, (x + 300, y + 150), 'one cycle', 19, rgba(C_GREY, 255 * aw), 'Medium', 'mm')
        text(d, (x + 300, y + 112), '10 MHz today', 24, rgba(C_RED, 255 * aw), 'Bold', 'mm')
    if ah > 0:
        x, y = oh
        for i, (lab, mhz, col, at) in enumerate((('today', 10.0, C_RED, 22.4), ('1 wire', 15.0, C_AMBER, 27.6), ('50 wires', 26.9, C_GREEN, 30.4))):
            g = seg(t, at, 0.8)
            if g <= 0:
                continue
            bx = x + 50 + i * 125
            h = 110 * mhz / 27.0 * g
            d.rectangle((bx, y + 150 - h, bx + 70, y + 150), fill=rgba(col, 230))
            text(d, (bx + 35, y + 150 - h - 16), ('%.0f' % mhz) if i < 2 else '27', 24, rgba(C_WHITE, 255 * g), 'Bold', 'mm')
            text(d, (bx + 35, y + 168), lab, 18, rgba(C_GREY, 255 * g), 'Medium', 'mm')
    result(d, t, 31.4, 'being routed tonight, on a separate line', C_PURPLE)


ROWS = [('Clock wires', 'detours', 'direct paths', 'DONE', C_GREEN, 2.3),
        ('Hold', 'data too early', '7,205 delay cells', 'DONE', C_GREEN, 7.5),
        ('Antenna', 'charge on long wires', '7,213 diodes', 'ROUTING', C_BLUE, 15.7),
        ('Empty places', 'gaps, uneven layers', 'filler cells, fill', 'DONE', C_GREEN, 22.1),
        ('Speed', '50 slow wires', 'direct paths', 'TONIGHT', C_PURPLE, 27.3)]


def s_sum(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    for x, s in ((105, 'problem'), (400, 'cause'), (670, 'cure')):
        text(d, (x, 215), s, 22, rgba(C_GREY, 255 * a), 'Medium', 'lm')
    for i, (k, why, how, st, col, at) in enumerate(ROWS):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 245 + i * 150; dx = (1 - e) * 50
        card(d, (70 + dx, y, 1010 + dx, y + 130), e, col)
        text(d, (105 + dx, y + 50), k, 28, rgba(C_WHITE, 255 * e), 'Bold', 'lm')
        pw = B.font(19).getlength(st) + 28
        rrect(d, (105 + dx, y + 80, 105 + dx + pw, y + 110), 15, fill=rgba(col, 255 * e * .22))
        text(d, (105 + dx + pw / 2, y + 95), st, 19, rgba(col, 255 * e), 'Bold', 'mm')
        text(d, (400 + dx, y + 65), why, 23, rgba(C_AMBER, 255 * e), 'Medium', 'lm')
        text(d, (670 + dx, y + 65), how, 23, rgba(C_GREEN, 255 * e), 'SemiBold', 'lm')
    z = seg(t, 32.6, 0.6)
    if z > 0:
        card(d, (70, 1010, 1010, 1112), z, C_TEAL)
        text(d, (540, 1061), 'one cause behind all of it: wires forced around the memory blocks', 24, rgba(C_WHITE, 255 * z), 'SemiBold', 'mm')


def s_end(layer, t, dur):
    fp = B.FP(340, 420, 400); B.draw_die(layer, fp, dim=True)
    d = ImageDraw.Draw(layer)
    text(d, (540, 900), 'SoC2611', 40, C_WHITE, 'Bold', 'mm')
    text(d, (540, 955), 'how, why and where · 11 November 2026', 24, C_GREY, 'Medium', 'mm')


SCENES = [
    ('The chip, from above', s_map,
     'To show how each problem was solved, here is the chip from above. It is six point six millimetres wide. '
     'The blocks are two hundred and ninety-eight memories. The logic cells sit in the channels between them, and so do '
     'most of the wires. That is the root of everything that follows: wires that have to go around memory blocks.'),
    ('Clock wires', s_clock,
     'First, the clock. Where: these are the forty-two clock wires we laid again, drawn on the real chip. '
     'Why: to clear the last routing conflicts, the router had pushed them onto detours around the memories. '
     'One went nine millimetres to join two pins one hundred and eighty micrometres apart. A long wire is a slow wire, '
     'so some flip-flops heard the clock late. How: we gave each of these wires an explicit short path. '
     'The long stretches run on the top metal layer, which is nearly empty, and may cross a memory block. '
     'The router had to follow that path, and moved the neighbours instead.'),
    ('Hold', s_hold,
     'Second, hold. Where: every dot is one of the seven thousand two hundred and five delay cells we added. '
     'They are spread over all the logic. Why: on every clock beat, one flip-flop sends new data, and the next one must '
     'still store the old data. Where the clock arrived late, the new data was there first, and the wrong value was '
     'stored. No clock speed fixes that. How: we measured the real wires, and put a small delay cell on every data path '
     'that was too fast. Every existing cell stayed in its place.'),
    ('Antenna', s_ant,
     'Third, antenna. Where: the green dots are seven thousand two hundred and thirteen diodes. The blue ones are one '
     'thousand three hundred and fifteen buffers, at memory and pad pins. Why: while a metal layer is cut with plasma, '
     'a long wire collects charge. If it ends on a transistor gate, the charge can punch through the thin glass under '
     'the gate. How: a diode beside each gate drains that charge into the silicon. And we route it gently: each wire '
     'keeps the path it had, and only the short link to its diode is new.'),
    ('Empty places', s_fill,
     'Fourth, the empty places. Where: everywhere between the memories, in every row of cells. '
     'Why: a gap between two cells breaks the wells underneath, and the factory needs every layer evenly filled. '
     'How: one million and eighty thousand filler cells close the gaps, and metal fill evens out the layers.'),
    ('Speed', s_speed,
     'Last, speed. This one is found, and is being solved tonight. Where: these are the fifty wires that limit the '
     'clock. Why: they also sit on long detours, and many of them feed memory pins, where a signal has only half a '
     'clock cycle to arrive. Today that holds the chip at ten megahertz at the slow corner. How: the same cure as for '
     'the clock wires, a short direct path. One wire alone gives fifteen megahertz. All fifty give about twenty-seven.'),
    ('In one table', s_sum,
     'So, in one table. Clock wires: detours, cured by direct paths. Done. Hold: data too early, cured by delay cells. '
     'Done, with one cell left for the final touch. Antenna: charge on long wires, cured by diodes. Placed, and routing. '
     'Empty places: cured by filler cells. Done. Speed: fifty slow wires, direct paths, tonight. '
     'One cause runs through all of it: wires forced around the memory blocks.'),
    ('', s_end, ''),
]

if __name__ == '__main__':
    B.SCENES = SCENES
    B.main()
