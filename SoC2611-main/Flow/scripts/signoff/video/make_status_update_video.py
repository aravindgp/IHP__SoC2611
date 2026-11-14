#!/usr/bin/env python3
"""Status video of 11 November 2026, afternoon: the three kinds of violation of this update (routing, hold, antenna)
in plain words, the hold repair measured on the real routed wires (1,771 / 616 / 511 failing endpoints before,
15 / 14 / 14 after, what the rest is), the antenna repair as placed (7,213 diodes, 1,315 buffers), why new cells
mean new routing and how the leftovers close, the two lines that run in parallel, and the timeline.
Same renderer, captions and voice (en-GB-RyanNeural) as make_status_video.py, whose helpers are imported.
usage: make_status_update_video.py <out_dir> [--preview] [--jobs N]     (writes <out_dir>/SoC2611_status.mp4)"""
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


def pill(d, x1, y, s, col, a):
    pw = B.font(20).getlength(s) + 34
    rrect(d, (x1 - pw, y, x1, y + 32), 16, fill=rgba(col, 255 * a * .2))
    text(d, (x1 - pw / 2, y + 16), s, 20, rgba(col, 255 * a), 'Bold', 'mm')


def dot(d, p, col, r=8, a=1.0):
    d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=rgba(col, 255 * a))


def box(d, x, y, label, col, a=1.0, w=150, h=70, size=24):
    rrect(d, (x - w / 2, y - h / 2, x + w / 2, y + h / 2), 12, fill=rgba(CARD, 255 * a), outline=rgba(col, 255 * a), width=3)
    text(d, (x, y), label, size, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')


# ------------------------------------------------------------------ scenes
HEAD = [('Hold on the real wires', '1,771 → 15', 'failing flip-flop inputs, fast corner', C_GREEN, 7.3),
        ('Antenna repair', '7,213', 'diodes placed, now routing', C_TEAL, 10.9),
        ('Routing conflicts', '288', 'left to close', C_AMBER, 14.3)]


def s_title(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (k, num, v, col, at) in enumerate(HEAD):
        a = seg(t, at, 0.6)
        if a <= 0:
            continue
        y = 215 + i * 290; dx = (1 - a) * 50
        card(d, (90 + dx, y, 990 + dx, y + 250), a, col)
        text(d, (540 + dx, y + 50), k, 30, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
        text(d, (540 + dx, y + 135), num, 88, rgba(col, 255 * a), 'Bold', 'mm')
        text(d, (540 + dx, y + 212), v, 24, rgba(C_GREY, 255 * a), 'Medium', 'mm')


def s_kinds(layer, t, dur):
    d = ImageDraw.Draw(layer)
    rows = [('Routing', 'two wires touch or sit too close', 'repair: route those wires again', C_AMBER, 2.9, 8.0),
            ('Hold', 'new data reaches a flip-flop too early', 'repair: a small delay cell on the data', C_BLUE, 11.2, 17.4),
            ('Antenna', 'a long wire collects charge in the factory', 'repair: a diode at the gate', C_PURPLE, 21.2, 26.9)]
    for i, (k, what, fix, col, at, at2) in enumerate(rows):
        a = seg(t, at, 0.5)
        if a <= 0:
            continue
        y = 200 + i * 310
        card(d, (70, y, 1010, y + 285), a, col)
        text(d, (360, y + 52), k, 38, rgba(col, 255 * a), 'Bold', 'lm')
        text(d, (360, y + 112), what, 25, rgba(C_WHITE, 255 * a), 'Medium', 'lm')
        b = seg(t, at2, 0.5)
        if b > 0:
            rrect(d, (360, y + 170, 980, y + 240), 14, fill=rgba(C_GREEN, 40 * b), outline=rgba(C_GREEN, 255 * b), width=2)
            text(d, (670, y + 205), fix, 25, rgba(C_GREEN, 255 * b), 'SemiBold', 'mm')
        # the icon, in a 250 x 245 field at the left
        cx, cy = 215, y + 142
        u = max(0.0, t - at)
        if i == 0:
            off = 46 * max(0.0, 1 - u / 2.5)                       # the second wire comes closer and touches
            d.line([(cx - 105, cy - 12), (cx + 105, cy - 12)], fill=rgba(C_WHITE, 255 * a), width=10)
            d.line([(cx - 60, cy + 4 + off), (cx + 20, cy + 4 + off), (cx + 20, cy + 80)], fill=rgba(C_AMBER, 255 * a), width=10)
            if off < 2:
                d.ellipse((cx - 44, cy - 34, cx + 4, cy + 14), outline=rgba(C_RED, 255), width=5)
        elif i == 1:
            x0, x1 = cx - 110, cx + 110
            xe = cx + 20                                             # the clock edge at flip-flop B
            d.line([(x0, cy - 30), (xe, cy - 30), (xe, cy - 70), (x1, cy - 70)], fill=rgba(C_WHITE, 255 * a), width=5)
            xd = xe + 50 - 90 * min(1.0, u / 2.5)                    # the data edge slides in front of the clock edge
            d.line([(x0, cy + 60), (xd, cy + 60), (xd, cy + 20), (x1, cy + 20)], fill=rgba(C_RED if xd < xe else C_BLUE, 255 * a), width=5)
            text(d, (x0, cy - 92), 'clock', 20, rgba(C_GREY, 255 * a), 'Medium', 'lm')
            text(d, (x0, cy + 86), 'data', 20, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        else:
            d.line([(cx - 110, cy - 50), (cx + 60, cy - 50), (cx + 60, cy + 10)], fill=rgba(C_WHITE, 255 * a), width=7)
            rrect(d, (cx + 15, cy + 10, cx + 105, cy + 56), 6, fill=rgba(CARD, 255 * a), outline=rgba(C_WHITE, 255 * a), width=2)
            text(d, (cx + 60, cy + 33), 'gate', 20, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
            hot = min(1.0, u / 4.0)
            d.rectangle((cx + 15, cy + 56, cx + 105, cy + 66), fill=rgba(mix(C_TEAL, C_RED, hot), 255 * a))
            for k2 in range(8):
                ph = (u * 0.9 + k2 / 8.0) % 1.0
                dot(d, (cx - 100 + 160 * ph, cy - 50), C_AMBER, 6, a)


CORN = [('fast', 1771, 15), ('typical', 616, 14), ('slow', 511, 14)]


def s_hold(layer, t, dur):
    d = ImageDraw.Draw(layer)
    # data path with the delay cell
    a = seg(t, 0.4, 0.5)
    y = 265
    box(d, 190, y, 'flip-flop A', C_TEAL, a, 190, 74); box(d, 890, y, 'flip-flop B', C_TEAL, a, 190, 74)
    d.line([(285, y), (795, y)], fill=rgba(C_DIM, 255 * a), width=5)
    dl = seg(t, 16.5, 0.8)
    if dl > 0:
        box(d, 540, y - (1 - dl) * 60, 'delay cell', C_GREEN, dl, 190, 74)
    ph = ((t - 1.0) % 2.4) / (1.0 + 0.8 * dl)
    if t > 1.0 and ph <= 1.0:
        dot(d, (285 + 510 * ph, y), C_AMBER if dl < 0.5 else C_GREEN, 11)
    base = 930
    b = seg(t, 2.0, 0.5)
    if b > 0:
        d.line([(120, base), (960, base)], fill=rgba(C_DIM, 255 * b), width=2)
    for i, (name, bef, aft) in enumerate(CORN):
        x = 170 + i * 280
        g = seg(t, (10.5, 11.3, 12.1)[i], 0.9)
        if b > 0:
            text(d, (x + 110, base + 34), name + ' corner', 24, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        if g > 0:
            h = 430 * (bef / 1771.0) * g
            d.rectangle((x, base - h, x + 100, base), fill=rgba(C_RED, 230))
            text(d, (x + 50, base - h - 26), f'{bef:,}', 32, rgba(C_WHITE, 255 * g), 'Bold', 'mm')
        g2 = seg(t, (27.0, 29.6, 30.0)[i], 0.9)
        if g2 > 0:
            h2 = max(430 * (aft / 1771.0), 6) * g2
            d.rectangle((x + 120, base - h2, x + 220, base), fill=rgba(C_GREEN, 240))
            text(d, (x + 170, base - h2 - 26), str(aft), 32, rgba(C_GREEN, 255 * g2), 'Bold', 'mm')
    c = seg(t, 9.0, 0.5)
    if c > 0:
        d.rectangle((150, 395, 176, 421), fill=rgba(C_RED, 230 * c)); text(d, (190, 408), 'before the repair', 22, rgba(C_GREY, 255 * c), 'Medium', 'lm')
        c2 = seg(t, 26.0, 0.5)
        d.rectangle((560, 395, 586, 421), fill=rgba(C_GREEN, 240 * c2)); text(d, (600, 408), 'after, measured on the real wires', 22, rgba(C_GREY, 255 * c2), 'Medium', 'lm')
    e = seg(t, 17.5, 0.6)
    if e > 0:
        card(d, (90, 1020, 990, 1110), e, C_GREEN)
        text(d, (540, 1065), '7,205 delay cells added, every existing cell kept in place', 26, rgba(C_WHITE, 255 * e), 'SemiBold', 'mm')


# what is left of hold at the fast corner (hold_excl_report.sh: 15 endpoints, 1 with the pad inputs excluded;
# 6 in the group pads -> clk_main flops, 8 receive flops of the memory bus in the strobe's group)
LEFT = [(6, C_GREY), (8, C_BLUE), (1, C_AMBER)]


def s_left(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    text(d, (540, 212), '15 failing inputs at the fast corner', 28, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    cols = [c for n, c in LEFT for _ in range(n)]
    when = [4.6] * 6 + [10.4] * 8 + [24.4]
    for k in range(15):
        x = 190 + (k % 8) * 100; y = 290 + (k // 8) * 90
        g = seg(t, 0.6 + k * 0.08, 0.4)
        B_ = seg(t, when[k], 0.8)
        d.ellipse((x - 26, y - 26, x + 26, y + 26), fill=rgba(mix(C_RED, cols[k], B_), 255 * g))
    rows = [('6', 'plain inputs from a pad', 'GPIO, UART receive and similar pins', C_GREY, 4.6),
            ('8', 'data pins of the memory bus', 'covered by the delayed strobe', C_BLUE, 10.4),
            ('1', 'flip-flop inside the chip', 'early by 0.03 ns: the final hold fix takes it', C_AMBER, 24.4)]
    for i, (num, k, v, col, at) in enumerate(rows):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 450 + i * 172 + (40 if i == 2 else 0); dx = (1 - e) * 50
        card(d, (70 + dx, y, 1010 + dx, y + 150), e, col)
        text(d, (150 + dx, y + 75), num, 70, rgba(col, 255 * e), 'Bold', 'mm')
        text(d, (240 + dx, y + 50), k, 29, rgba(C_WHITE, 255 * e), 'Bold', 'lm')
        text(d, (240 + dx, y + 100), v, 24, rgba(C_GREY, 255 * e), 'Medium', 'lm')
    n = seg(t, 13.8, 0.5)
    if n > 0:
        text(d, (540, 810), 'pad timing is set by the board, not by the chip', 24, rgba(C_TEAL, 255 * n), 'SemiBold', 'mm')


ANT = [('wires over the antenna limit', '6,131', C_AMBER, 2.8), ('diodes placed, one beside each gate pin', '7,213', C_GREEN, 8.3),
       ('buffers at memory and pad pins', '1,315', C_TEAL, 14.3), ('memory clock pins left alone, on purpose', '26', C_PURPLE, 21.7),
       ('placement legal, existing cells unmoved', 'OK', C_GREEN, 28.7)]


def s_ant(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (k, num, col, at) in enumerate(ANT):
        a = seg(t, at, 0.5)
        if a <= 0:
            continue
        y = 200 + i * 182; dx = (1 - a) * 50
        card(d, (70 + dx, y, 1010 + dx, y + 158), a, col)
        text(d, (105 + dx, y + 79), k, 27, rgba(C_WHITE, 255 * a), 'SemiBold', 'lm')
        text(d, (975 + dx, y + 79), num, 60, rgba(col, 255 * a), 'Bold', 'rm')


PASSES = [48246, 15102, 14618, 1710, 1026, 801, 715, 675, 601, 570, 469, 410, 390, 361, 342, 332, 288]


def s_route(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    text(d, (540, 210), 'routing conflicts after each repair pass', 26, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    base, top = 760, 280
    d.line([(110, base), (980, base)], fill=rgba(C_DIM, 255 * a), width=2)
    lo, hi = math.log10(100), math.log10(60000)
    n_show = len(PASSES) * min(1.0, max(0.0, (t - 6.5) / 13.0))
    for i, v in enumerate(PASSES):
        if i >= n_show:
            break
        x = 125 + i * 50
        h = (base - top) * (math.log10(v) - lo) / (hi - lo)
        col = C_RED if v > 5000 else (C_AMBER if v > 500 else C_GREEN)
        d.rectangle((x, base - h, x + 36, base), fill=rgba(col, 230))
        if i in (0, 3, 16):
            text(d, (x + 18, base - h - 22), f'{v:,}', 24, rgba(C_WHITE, 255), 'Bold', 'mm')
    text(d, (125, base + 28), 'start', 20, rgba(C_GREY, 255 * a), 'Medium', 'lm')
    text(d, (960, base + 28), 'pass 16', 20, rgba(C_GREY, 255 * a), 'Medium', 'rm')
    text(d, (540, base + 28), 'bar height on a logarithmic scale', 20, rgba(C_DIM, 255 * a), 'Medium', 'mm')
    b = seg(t, 21.2, 0.6)
    if b > 0:
        card(d, (70, 826, 1010, 1122), b, C_TEAL)
        text(d, (540, 866), 'the last few hundred: the closure loop', 28, rgba(C_TEAL, 255 * b), 'Bold', 'mm')
        steps = ('take only the wires named in the conflicts', 'send them on a new path', 'sixteen passes again, repeat until 0')
        for i, (s, at) in enumerate(zip(steps, (24.5, 27.2, 28.9))):
            e = seg(t, at, 0.5)
            if e > 0:
                d.ellipse((150, 906 + i * 52, 182, 938 + i * 52), fill=rgba(C_TEAL, 255 * e))
                text(d, (166, 922 + i * 52), str(i + 1), 20, rgba(BG, 255 * e), 'Bold', 'mm')
                text(d, (205, 922 + i * 52), s, 25, rgba(C_WHITE, 255 * e), 'Medium', 'lm')
        z = seg(t, 31.4, 0.5)
        if z > 0:
            text(d, (540, 1086), 'earlier today this method reached 0', 25, rgba(C_GREEN, 255 * z), 'Bold', 'mm')


def lane(d, y, a, col, title, steps, t, t0):
    card(d, (70, y, 1010, y + 250), a, col)
    text(d, (105, y + 42), title, 28, rgba(col, 255 * a), 'Bold', 'lm')
    n = len(steps); w = 860 / n
    for i, s in enumerate(steps):
        e = seg(t, t0 + i * 1.2, 0.5)
        if e <= 0:
            continue
        x = 110 + i * w
        rrect(d, (x, y + 85, x + w - 16, y + 215), 12, fill=rgba(BG, 255 * e), outline=rgba(col, 200 * e), width=2)
        for j, ln in enumerate(s.split('\n')):
            text(d, (x + (w - 16) / 2, y + 150 + (j - (len(s.split('\n')) - 1) / 2) * 30), ln, 21, rgba(C_WHITE, 255 * e), 'SemiBold', 'mm')


def s_lines(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 3.2, 0.5)
    if a > 0:
        lane(d, 200, a, C_TEAL, 'Fast line', ('antenna repair\n+ closure\nin one route', 'small final\nhold fix', 'sign-off\nand release'), t, 3.8)
        pill(d, 985, 216, 'SAVES ABOUT 4 HOURS', C_TEAL, seg(t, 8.7, 0.5))
    b = seg(t, 10.8, 0.5)
    if b > 0:
        lane(d, 480, b, C_GREY, 'Fallback line', ('closure of the\nhold repair alone', 'takes over if the\nfast line stalls'), t, 11.4)
    c = seg(t, 16.6, 0.5)
    if c > 0:
        card(d, (70, 765, 1010, 925), c, C_GREEN)
        text(d, (105, 815), 'Rehearsal: fill and density', 27, rgba(C_GREEN, 255 * c), 'Bold', 'lm')
        text(d, (105, 868), '1,080,061 row filler cells close the gaps in the cell rows', 23, rgba(C_GREY, 255 * c), 'Medium', 'lm')
    e = seg(t, 24.1, 0.5)
    if e > 0:
        card(d, (70, 950, 1010, 1110), e, C_PURPLE)
        text(d, (105, 1000), 'Experiment: shorter paths for slow data wires', 27, rgba(C_PURPLE, 255 * e), 'Bold', 'lm')
        text(d, (105, 1053), 'affects speed only, not whether the chip works', 23, rgba(C_GREY, 255 * e), 'Medium', 'lm')


TIME = [('about 19:00, 11 Nov', 'antenna repair routed', C_BLUE, 2.8),
        ('22:00 to 23:30', 'closed to zero conflicts', C_BLUE, 6.5),
        ('04:00 to 06:00, 12 Nov', 'small final hold fix closed', C_PURPLE, 9.0),
        ('about midday, 12 Nov', 'full sign-off, release candidate', C_GREEN, 16.0),
        ('04:29, 16 Nov', 'deadline: 15 Nov, 23:59 in Germany', C_AMBER, 20.6)]


def s_time(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    text(d, (540, 205), 'Indian Standard Time', 24, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    g = min(1.0, max(0.0, (t - 2.5) / 18.5))
    d.line([(150, 280), (150, 280 + 800 * g)], fill=rgba(C_DIM, 255 * a), width=4)
    for i, (when, what, col, at) in enumerate(TIME):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 300 + i * 165
        dot(d, (150, y + 40), col, 16, e)
        card(d, (200, y - 15, 1010, y + 110), e, col)
        text(d, (235, y + 22), when, 30, rgba(col, 255 * e), 'Bold', 'lm')
        text(d, (235, y + 72), what, 24, rgba(C_WHITE, 255 * e), 'Medium', 'lm')
    n = seg(t, 29.6, 0.5)
    if n > 0:
        text(d, (540, 1118), 'estimates: the closure steps are the uncertain part', 22, rgba(C_GREY, 255 * n), 'Medium', 'mm')


def s_end(layer, t, dur):
    fp = B.FP(340, 420, 400); B.draw_die(layer, fp, dim=True)
    d = ImageDraw.Draw(layer)
    text(d, (540, 900), 'SoC2611', 40, C_WHITE, 'Bold', 'mm')
    text(d, (540, 955), 'status · 11 November 2026, afternoon', 24, C_GREY, 'Medium', 'mm')


SCENES = [
    ('Status, 11 November', s_title,
     'This is the status of {S o C twenty six eleven|SoC2611} on the afternoon of the eleventh of November. '
     'Three things happened. The hold repair works on the real wires. The antenna repair is placed, and routing. '
     'And a few hundred routing conflicts are left to close. Here is what each one means, and how we solve it.'),
    ('Three kinds of violation', s_kinds,
     'There are three kinds of violation in this update. A routing violation means two wires touch, or sit too close. '
     'The repair is to route those wires again. A hold violation means new data reaches a flip-flop too early, so it '
     'stores the wrong value. The repair is a small delay cell on the data. An antenna violation means a long wire '
     'collects charge in the factory, and can damage a gate. The repair is a diode at the gate.'),
    ('Hold: before and after', s_hold,
     'Hold first. We check the chip at three corners: fast silicon, typical silicon, and slow silicon. '
     'Before the repair, on the real routed wires, one thousand seven hundred and seventy-one flip-flop inputs failed '
     'at the fast corner. We added seven thousand two hundred and five small delay cells, exactly where the data was '
     'too fast, and kept every existing cell in place. After routing and measuring again: fifteen at the fast corner, '
     'and fourteen at the other two.'),
    ('What is left of hold', s_left,
     'What are the last fifteen? Fourteen come straight from a pad. Six are plain inputs, such as {G P I O|GPIO} and the '
     '{U ART|UART} receive line. Eight are the data pins of the memory bus. For all of them, the timing is set by the '
     'board and by the device outside, so this check does not apply. The memory bus has its own fix: a delayed strobe. '
     'That leaves one flip-flop inside the chip, early by three hundredths of a nanosecond. '
     'The small final hold fix takes it.'),
    ('Antenna repair, placed', s_ant,
     'Now antenna. On the hold-repaired chip, six thousand one hundred and thirty-one wires are over the limit. '
     'The repair is placed: seven thousand two hundred and thirteen diodes, each beside its gate pin. '
     'One thousand three hundred and fifteen memory and pad pins got a small buffer as well, so the long wire ends on '
     'the buffer. Twenty-six memory clock pins were left alone on purpose, because a buffer there would make that '
     'memory hear the clock late. The placement is legal, and every existing cell stayed where it was.'),
    ('New cells need new wires', s_route,
     'Every new cell needs wires. So the touched wires are removed and routed again. At first the router leaves '
     'thousands of conflicts, where wires cross or crowd. Pass after pass, it repairs them. For the hold repair, it '
     'went from forty-eight thousand to two hundred and eighty-eight in sixteen passes. The last few hundred need a '
     'different step. We take only the wires named in the conflicts, send them on a new path, and run sixteen passes '
     'again. Earlier today, that method reached zero.'),
    ('Two lines in parallel', s_lines,
     'To save time, two lines run side by side. The fast line puts the antenna repair and the closure into one route. '
     'That saves about four hours. The fallback line closes the hold repair alone, in case the fast line stalls. '
     'Beside them, a rehearsal checks fill and density with one million row filler cells, which close the gaps in the '
     'cell rows. And an experiment shortens the slowest data wires. That affects speed only.'),
    ('The timeline', s_time,
     'The timeline, in Indian time. The antenna repair should be routed by about seven this evening, and closed to '
     'zero before midnight. Then a small final hold fix, because new routes move some wires, closed by early morning '
     'on the twelfth. Then the full sign-off, and a release candidate around midday on the twelfth. '
     'The deadline is the sixteenth, at four twenty-nine in the morning. That is one minute to midnight on the '
     'fifteenth in Germany. These are estimates, and the closure steps are the uncertain part.'),
    ('', s_end, ''),
]

if __name__ == '__main__':
    B.SCENES = SCENES
    B.main()
