#!/usr/bin/env python3
"""Video of the evening of 11 November 2026 (19:15 IST): the three runs on the machine. For each run a simple
PROBLEM and SOLUTION animation, then its numbers and how many more hours it needs.
Run 1, the local antenna route (main line): charge on a long wire damages a gate; a diode drains it; 203,334
violations down to 783 after pass 13 of 16, then the closure to zero.
Run 2, the fallback closure of the hold-repaired chip without antenna cells (safety net): wires that touch are laid
again; 288, 149, 30, round 3 running.
Run 3, the data wire experiment: detours make signals late; 160 wires pinned to direct paths; finished at 1,207
after 7 hours, not continued, replaced by the 50 wires that limit the clock.
Same renderer, captions and voice (en-GB-RyanNeural) as make_status_video.py.
usage: make_three_runs_video.py <out_dir> [--preview] [--jobs N]     (writes <out_dir>/SoC2611_status.mp4)"""
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


def card(d, box, a, outline=EDGE):
    rrect(d, box, 18, fill=rgba(CARD, 235 * a), outline=rgba(outline, 255 * a), width=2)


def pill(d, x0, y, s, col, a, size=20):
    pw = B.font(size).getlength(s) + 34
    rrect(d, (x0, y, x0 + pw, y + 34), 17, fill=rgba(col, 255 * a * .22))
    text(d, (x0 + pw / 2, y + 17), s, size, rgba(col, 255 * a), 'Bold', 'mm')
    return pw


def dot(d, p, col, r=8, a=1.0):
    d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=rgba(col, 255 * a))


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


def panels(d, t, t_prob, t_sol, prob_cap, sol_cap):
    """PROBLEM and SOLUTION cards at the top of a run scene; returns (a_problem, a_solution, origin_p, origin_s)"""
    ap = seg(t, t_prob, 0.5); as_ = seg(t, t_sol, 0.5)
    if ap > 0:
        card(d, (70, 195, 530, 480), ap, C_RED)
        text(d, (96, 223), 'PROBLEM', 22, rgba(C_RED, 255 * ap), 'Bold', 'lm')
        text(d, (300, 452), prob_cap, 21, rgba(C_WHITE, 255 * ap), 'SemiBold', 'mm')
    if as_ > 0:
        card(d, (550, 195, 1010, 480), as_, C_GREEN)
        text(d, (576, 223), 'SOLUTION', 22, rgba(C_GREEN, 255 * as_), 'Bold', 'lm')
        text(d, (780, 452), sol_cap, 21, rgba(C_WHITE, 255 * as_), 'SemiBold', 'mm')
    return ap, as_, (90, 245), (570, 245)


def bars(d, vals, t, t0, dur, box, lo, hi, labels=(), show=(), col_fn=None, a=1.0):
    """log-scale bars inside box = (x0, y_top, x1, y_base); bars appear one after another from t0 over dur seconds"""
    x0, top, x1, base = box
    d.line([(x0 - 15, base), (x1 + 15, base)], fill=rgba(C_DIM, 255 * a), width=2)
    n = len(vals); w = (x1 - x0) / n
    n_show = n * min(1.0, max(0.0, (t - t0) / dur))
    for i, v in enumerate(vals):
        if i >= n_show:
            break
        h = (base - top) * (math.log10(max(v, lo)) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
        col = col_fn(v) if col_fn else C_AMBER
        d.rectangle((x0 + i * w + 3, base - max(h, 4), x0 + (i + 1) * w - 3, base), fill=rgba(col, 230))
        if i in show:
            text(d, (x0 + (i + 0.5) * w, base - max(h, 4) - 18), f'{v:,}', 22, rgba(C_WHITE), 'Bold', 'mm')
    for i, s in labels:
        text(d, (x0 + (i + 0.5) * w, base + 22), s, 19, rgba(C_GREY, 255 * a), 'Medium', 'mm')


def fact(d, y, k, v, col, a):
    card(d, (70, y, 1010, y + 84), a, col)
    text(d, (105, y + 42), k, 25, rgba(C_WHITE, 255 * a), 'SemiBold', 'lm')
    text(d, (975, y + 42), v, 28, rgba(col, 255 * a), 'Bold', 'rm')


# ------------------------------------------------------------------ scenes
RUNS = [('1', 'Local antenna route', 'wires the 7,213 diodes to their gates', 'MAIN LINE', C_BLUE, 8.9),
        ('2', 'Fallback closure', 'the same chip without the diodes, as a spare', 'SAFETY NET', C_AMBER, 11.2),
        ('3', 'Data wire experiment', 'tested short paths for 160 slow wires', 'EXPERIMENT', C_PURPLE, 13.4)]


def s_title(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    text(d, (540, 215), 'what each one is, what it fixes, how many more hours', 25, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    for i, (n, k, v, tag, col, at) in enumerate(RUNS):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 270 + i * 270
        card(d, (70, y, 1010, y + 235), e, col)
        d.ellipse((100, y + 30, 170, y + 100), fill=rgba(col, 255 * e))
        text(d, (135, y + 65), n, 38, rgba(BG, 255 * e), 'Bold', 'mm')
        text(d, (200, y + 65), k, 36, rgba(C_WHITE, 255 * e), 'Bold', 'lm')
        text(d, (105, y + 140), v, 26, rgba(C_GREY, 255 * e), 'Medium', 'lm')
        pill(d, 105, y + 180, tag, col, e)


def g_gate(d, o, a, ox_col):
    x, y = o
    d.line([(x + 20, y + 30), (x + 330, y + 30), (x + 330, y + 68)], fill=rgba(C_WHITE, 230 * a), width=6)
    rrect(d, (x + 280, y + 68, x + 380, y + 112), 6, fill=rgba(CARD, 255 * a), outline=rgba(C_WHITE, 255 * a), width=2)
    text(d, (x + 330, y + 90), 'gate', 20, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
    d.rectangle((x + 280, y + 112, x + 380, y + 122), fill=rgba(ox_col, 255 * a))
    rrect(d, (x + 200, y + 122, x + 400, y + 156), 6, fill=rgba(mix(C_BLUE, BG, .72), 255 * a), outline=rgba(C_DIM, 255 * a), width=1)
    text(d, (x + 300, y + 139), 'silicon', 17, rgba(C_GREY, 255 * a), 'Medium', 'mm')


ANL = [203334, 21429, 16292, 3469, 2416, 2023, 1858, 1642, 1575, 1521, 1073, 942, 862, 783]
T2 = dict(prob=4.6, sol=13.3, link=26.8, bars=31.0, f1=39.3, f2=42.5, f3=45.8)


def s_local(layer, t, dur):
    d = ImageDraw.Draw(layer)
    ap, as_, op, os_ = panels(d, t, T2['prob'], T2['sol'], 'charge on a long wire hits the gate', 'a diode drains the charge away')
    if ap > 0:
        x, y = op
        hot = min(1.0, max(0.0, (t - T2['prob'] - 1.5) / 6.0))
        g_gate(d, op, ap, mix(C_TEAL, C_RED, hot))
        for k in range(9):
            ph = ((t - T2['prob'] - 0.8) * 0.5 + k / 9.0) % 1.0
            if t > T2['prob'] + 0.8:
                p = (x + 20 + 310 * ph / 0.9, y + 30) if ph < 0.9 else (x + 330, y + 30 + 380 * (ph - 0.9))
                dot(d, p, C_AMBER, 6, ap)
    if as_ > 0:
        x, y = os_
        g_gate(d, os_, as_, C_TEAL)
        lk = seg(t, T2['link'], 0.6)
        col = mix(C_GREEN, C_WHITE, 0.0)
        d.line([(x + 240, y + 30), (x + 240, y + 66)], fill=rgba(col, 255 * as_), width=5 + int(3 * lk))
        d.polygon([(x + 224, y + 90), (x + 256, y + 90), (x + 240, y + 66)], fill=rgba(C_GREEN, 255 * as_))
        d.line([(x + 222, y + 64), (x + 258, y + 64)], fill=rgba(C_GREEN, 255 * as_), width=5)
        d.line([(x + 240, y + 90), (x + 240, y + 122)], fill=rgba(C_GREEN, 255 * as_), width=5)
        text(d, (x + 150, y + 78), 'diode', 20, rgba(C_GREEN, 255 * as_), 'Bold', 'mm')
        if lk > 0:
            text(d, (x + 120, y + 4), 'old path kept', 18, rgba(C_GREY, 255 * lk), 'Medium', 'mm')
            text(d, (x + 150, y + 104), 'new link', 18, rgba(C_GREEN, 255 * lk), 'SemiBold', 'mm')
        for k in range(7):
            ph = ((t - T2['sol'] - 0.8) * 0.5 + k / 7.0) % 1.0
            if t > T2['sol'] + 0.8:
                p = (x + 20 + 220 * ph / 0.75, y + 30) if ph < 0.75 else (x + 240, y + 30 + 92 * (ph - 0.75) / 0.25)
                dot(d, p, C_GREEN, 6, as_)
    b = seg(t, T2['bars'], 0.5)
    if b > 0:
        text(d, (540, 512), 'conflicts after each pass (logarithmic scale)', 20, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        bars(d, ANL, t, T2['bars'] + 0.5, 6.0, (120, 550, 960, 745), 300, 250000, labels=((0, 'start'), (13, 'pass 13')), show=(0, 3, 13),
             col_fn=lambda v: C_RED if v > 10000 else (C_AMBER if v > 2500 else C_GREEN), a=b)
    for i, (kk, v, col, key) in enumerate((('passes left', '3 of 16, about 40 minutes', C_BLUE, 'f1'),
                                           ('then: closure to zero', '3 to 8 hours', C_AMBER, 'f2'),
                                           ('clean, antenna-repaired chip', '23:30 to 04:00', C_GREEN, 'f3'))):
        e = seg(t, T2[key], 0.5)
        if e > 0:
            fact(d, 808 + i * 100, kk, v, col, e)


T3 = dict(prob=9.6, sol=18.1, bars=23.6, r0=26.2, r1=27.9, r2=29.6, r3=30.9, f1=33.2, f2=4.5, f3=37.0)


def s_fallback(layer, t, dur):
    d = ImageDraw.Draw(layer)
    ap, as_, op, os_ = panels(d, t, T3['prob'], T3['sol'], 'two wires touch: a short circuit', 'the touching wire takes a new path')
    if ap > 0:
        x, y = op
        d.line([(x + 40, y + 90), (x + 300, y + 90)], fill=rgba(C_WHITE, 230 * ap), width=8)
        g = min(1.0, max(0.0, (t - T3['prob'] - 0.6) / 1.6))
        d.line([(x + 200, y + 10), (x + 200, y + 10 + 140 * g)], fill=rgba(C_AMBER, 255 * ap), width=8)
        if g >= 0.6:
            z = seg(t, T3['prob'] + 1.8, 0.4)
            d.ellipse((x + 172, y + 62, x + 228, y + 118), outline=rgba(C_RED, 255 * z), width=5)
            text(d, (x + 290, y + 130), 'short', 22, rgba(C_RED, 255 * z), 'Bold', 'mm')
    if as_ > 0:
        x, y = os_
        d.line([(x + 40, y + 90), (x + 300, y + 90)], fill=rgba(C_WHITE, 230 * as_), width=8)
        new = [(x + 200, y + 10), (x + 200, y + 46), (x + 350, y + 46), (x + 350, y + 134), (x + 200, y + 134), (x + 200, y + 156)]
        draw_path(d, new, (t - T3['sol'] - 0.8) / 2.5, rgba(C_GREEN, 255 * as_), 8)
        nt = seg(t, T3['sol'] + 3.4, 0.4)
        if nt > 0:
            text(d, (x + 110, y + 134), 'no touch', 20, rgba(C_GREEN, 255 * nt), 'Bold', 'mm')
    b = seg(t, T3['bars'], 0.5)
    if b > 0:
        text(d, (540, 512), 'wires still touching, after each closure round', 21, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        base = 745
        d.line([(160, base), (920, base)], fill=rgba(C_DIM, 255 * b), width=2)
        for i, (lab, v, key) in enumerate((('start', 288, 'r0'), ('round 1', 149, 'r1'), ('round 2', 30, 'r2'))):
            g = seg(t, T3[key], 0.8)
            if g <= 0:
                continue
            xx = 200 + i * 180
            h = 170 * v / 288.0 * g
            d.rectangle((xx, base - max(h, 4), xx + 120, base), fill=rgba(C_AMBER if v > 50 else C_GREEN, 230))
            text(d, (xx + 60, base - max(h, 4) - 20), str(v), 30, rgba(C_WHITE, 255 * g), 'Bold', 'mm')
            text(d, (xx + 60, base + 24), lab, 21, rgba(C_GREY, 255 * g), 'Medium', 'mm')
        g = seg(t, T3['r3'], 0.6)
        if g > 0:
            xx = 200 + 3 * 180
            rrect(d, (xx, base - 100, xx + 120, base), 8, outline=rgba(C_BLUE, 255 * g), width=3)
            text(d, (xx + 60, base - 50), 'running', 21, rgba(C_BLUE, 255 * g), 'Bold', 'mm')
            text(d, (xx + 60, base + 24), 'round 3', 21, rgba(C_BLUE, 255 * g), 'SemiBold', 'mm')
    for i, (kk, v, col, key) in enumerate((('what it is', 'the chip without diodes, a spare', C_AMBER, 'f2'),
                                           ('more time needed', '1 to 2.5 hours', C_BLUE, 'f1'),
                                           ('if the main line fails', 'this chip can be handed in', C_GREEN, 'f3'))):
        e = seg(t, T3[key], 0.5)
        if e > 0:
            fact(d, 808 + i * 100, kk, v, col, e)


def g_block(d, o, a, lx=210):
    x, y = o
    rrect(d, (x + 110, y + 45, x + 310, y + 115), 6, fill=rgba(mix(C_TEAL, BG, .6), 255 * a), outline=rgba(C_TEAL, 255 * a), width=2)
    text(d, (x + lx, y + 80), 'memory', 20, rgba(C_WHITE, 220 * a), 'SemiBold', 'mm')
    for p in ((x + 210, y + 141), (x + 210, y + 19)):
        dot(d, p, C_WHITE, 7, a)


DG = [30969, 7644, 6113, 4263, 3724, 3499, 3167, 3041, 2922, 2803, 2185, 1997, 1510, 1423, 1395, 1356, 1207]
T4 = dict(prob=3.7, sol=11.5, bars=18.3, f1=21.0, f2=29.2, f3=32.9)


def s_data(layer, t, dur):
    d = ImageDraw.Draw(layer)
    ap, as_, op, os_ = panels(d, t, T4['prob'], T4['sol'], 'a detour: the signal arrives late', 'a short, direct path')
    if ap > 0:
        g_block(d, op, ap)
        x, y = op
        det = [(x + 210, y + 141), (x + 210, y + 160), (x + 395, y + 160), (x + 395, y + 2), (x + 30, y + 2), (x + 30, y + 146),
               (x + 80, y + 146), (x + 80, y + 32), (x + 210, y + 32), (x + 210, y + 19)]
        d.line(det, fill=rgba(C_RED, 200 * ap), width=5)
        ph = ((t - T4['prob'] - 0.8) % 4.0) / 3.2
        if t > T4['prob'] + 0.8 and ph <= 1.0:
            cur = draw_path(d, det, ph, rgba(C_RED, 0), 1)
            dot(d, cur, C_AMBER, 9, ap)
    if as_ > 0:
        g_block(d, os_, as_, lx=160)
        x, y = os_
        d.line([(x + 210, y + 141), (x + 210, y + 19)], fill=rgba(C_GREEN, 255 * as_), width=7)
        ph = ((t - T4['sol'] - 0.8) % 1.6) / 0.5
        if t > T4['sol'] + 0.8 and ph <= 1.0:
            dot(d, (x + 210, y + 141 - 122 * ph), C_WHITE, 9, as_)
    b = seg(t, T4['bars'], 0.5)
    if b > 0:
        text(d, (540, 512), 'conflicts after each pass, with 160 wires pinned (logarithmic scale)', 20, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        bars(d, DG, t, T4['bars'] + 0.5, 5.0, (120, 550, 960, 745), 500, 40000, labels=((0, 'start'), (16, 'pass 16')), show=(0, 16),
             col_fn=lambda v: C_RED if v > 5000 else C_AMBER, a=b)
    for i, (kk, v, col, key) in enumerate((('finished after 7 hours', '1,207 conflicts left', C_RED, 'f1'),
                                           ('more hours needed', '0, it stops here', C_GREEN, 'f2'),
                                           ('replaced by', 'the 50 wires that limit the clock', C_PURPLE, 'f3'))):
        e = seg(t, T4[key], 0.5)
        if e > 0:
            fact(d, 808 + i * 100, kk, v, col, e)


def s_hours(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    x0, x1 = 150, 990
    hrs = ['19', '21', '23', '01', '03', '05']

    def X(h):                                  # h = hours after 19:00
        return x0 + (x1 - x0) * h / 10.0
    y_ax = 330
    d.line([(x0, y_ax), (x1, y_ax)], fill=rgba(C_DIM, 255 * a), width=2)
    for i, s in enumerate(hrs):
        x = X(i * 2)
        d.line([(x, y_ax - 8), (x, y_ax + 8)], fill=rgba(C_DIM, 255 * a), width=2)
        text(d, (x, y_ax - 30), s + ':00', 21, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    text(d, (540, 232), 'Indian Standard Time, from now', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    d.line([(X(0.25), y_ax - 14), (X(0.25), y_ax + 26)], fill=rgba(C_WHITE, 200 * a), width=3)
    text(d, (X(0.25) + 8, 372), 'now', 19, rgba(C_WHITE, 200 * a), 'SemiBold', 'lm')
    rows = [('experiment', 'none', C_PURPLE, 2.9, None, None, None),
            ('safety net', '1 to 2.5 hours', C_AMBER, 5.2, 0.25, 1.25, 2.75),
            ('main line', '40 min, then 3 to 8 hours', C_BLUE, 8.9, 0.25, 4.5, 9.0)]
    for i, (k, v, col, at, h0, h1, h2) in enumerate(rows):
        e = seg(t, at, 0.6)
        if e <= 0:
            continue
        y = 420 + i * 160
        text(d, (70, y), k, 26, rgba(col, 255 * e), 'Bold', 'lm')
        text(d, (70, y + 40), v, 22, rgba(C_WHITE, 255 * e), 'Medium', 'lm')
        if h0 is None:
            dot(d, (X(0.12), y + 86), col, 12, e)
            text(d, (X(0.12) + 24, y + 86), 'finished', 21, rgba(col, 255 * e), 'SemiBold', 'lm')
        else:
            g = seg(t, at + 0.4, 1.2)
            xa, xb, xc = X(h0), X(h0 + (h1 - h0) * g), X(h1 + (h2 - h1) * g)
            d.rectangle((xa, y + 74, xb, y + 98), fill=rgba(col, 235 * e))
            d.rectangle((xb, y + 74, xc, y + 98), fill=rgba(col, 90 * e))
            if i == 2:
                xp = X(1.0)
                d.line([(xp, y + 68), (xp, y + 104)], fill=rgba(C_WHITE, 220 * e), width=3)
                text(d, (xp + 6, y + 122), 'passes done', 18, rgba(C_GREY, 255 * e), 'Medium', 'lm')
    z = seg(t, 14.8, 0.6)
    if z > 0:
        card(d, (70, 905, 1010, 1010), z, C_GREEN)
        text(d, (540, 957), 'clean, antenna-repaired chip: 23:30 tonight to 04:00', 27, rgba(C_WHITE, 255 * z), 'Bold', 'mm')
    q = seg(t, 21.4, 0.6)
    if q > 0:
        text(d, (540, 1060), 'then: small final hold fix, the checks, the release', 24, rgba(C_GREY, 255 * q), 'Medium', 'mm')
        text(d, (540, 1100), 'the solid part is the likely end, the pale part the slower case', 19, rgba(C_DIM, 255 * q), 'Medium', 'mm')


def s_end(layer, t, dur):
    fp = B.FP(340, 420, 400); B.draw_die(layer, fp, dim=True)
    d = ImageDraw.Draw(layer)
    text(d, (540, 900), 'SoC2611', 40, C_WHITE, 'Bold', 'mm')
    text(d, (540, 955), 'the three runs · 11 November 2026, 19:15 IST', 24, C_GREY, 'Medium', 'mm')


SCENES = [
    ('Three runs tonight', s_title,
     'Three runs are on the machine tonight. This video says what each one is, what it fixes, and how many more hours '
     'it needs. The first is the main line. The second is a safety net. The third was an experiment.'),
    ('Run 1: local antenna route', s_local,
     'Run one: the local antenna route. This is the main line. The problem: in the factory, a long wire collects '
     'electric charge, and that charge can damage the transistor gate at its end. The solution: a small diode beside '
     'the gate, which drains the charge away. We placed seven thousand two hundred of them, and each one has to be '
     'wired to its gate. The route is called local, because every wire keeps the path it had, and only the short link '
     'to its diode is new. It started with two hundred thousand conflicts. After thirteen passes, seven hundred and '
     'eighty-three are left. Three passes remain, about forty minutes. Then the last conflicts are closed to zero, '
     'which takes three to eight more hours.'),
    ('Run 2: fallback closure', s_fallback,
     'Run two: the fallback closure. This is the safety net. It is the same chip with the hold repair, but without the '
     'antenna diodes. The problem it is fixing: after the hold repair, a few wires still touch each other, and two '
     'wires that touch are a short circuit. The solution: only the wires that touch are taken out, and laid again on '
     'a new path. Round by round, the count falls: two hundred and eighty-eight, then one hundred and forty-nine, then '
     'thirty. Round three is running now. It needs one to two and a half more hours. If the main line should fail, '
     'this chip could still be handed in.'),
    ('Run 3: data wire experiment', s_data,
     'Run three: the data wire experiment. The problem: some data wires take long detours around the memory blocks, so '
     'their signals arrive late, and the chip has to run slowly. The solution we tested: pin the one hundred and sixty '
     'slowest wires to short, direct paths. It finished a few minutes ago. After seven hours, one thousand two hundred '
     'conflicts were still left. So many pinned wires leave their neighbours no room. It needs no more hours, because '
     'it stops here. It is replaced by a smaller set: the fifty wires that really limit the clock.'),
    ('How many more hours', s_hours,
     'So, how many more hours? The experiment: none. The safety net: one to two and a half. The main line: about forty '
     'minutes for its passes, then three to eight hours to reach zero. That puts a clean, antenna-repaired chip between '
     'half past eleven tonight and four in the morning, Indian time. Then come the small final hold fix, the checks, '
     'and the release.'),
    ('', s_end, ''),
]

if __name__ == '__main__':
    B.SCENES = SCENES
    B.main()
