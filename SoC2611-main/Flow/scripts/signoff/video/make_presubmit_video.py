#!/usr/bin/env python3
"""Video of the evening of 11 November 2026: what is solved and what the final submission is still waiting for.
Solved: clock wires on direct paths and hold on the real wires (1,771 / 616 / 511 failing inputs before, 15 / 14 / 14
after, of which 14 pad inputs and 1 flip-flop at 0.03 ns), the antenna repair as placed and its route (203,334 down
to about 1,500 at pass 9 of 16), row fillers with density 0, and the wires that limit the speed (10 MHz today at the
slow corner; what-if of setup_path_wires.py). Waiting: the routes, the checks on the final file, LVS on a second
machine, the release. Same renderer, captions and voice (en-GB-RyanNeural) as make_status_video.py.
usage: make_presubmit_video.py <out_dir> [--preview] [--jobs N]     (writes <out_dir>/SoC2611_status.mp4)"""
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


def tick(d, x, y, col, a, r=17):
    d.ellipse((x - r, y - r, x + r, y + r), fill=rgba(col, 255 * a))
    d.line([(x - 8, y), (x - 2, y + 7), (x + 9, y - 7)], fill=rgba(BG, 255 * a), width=4)


def clock_sym(d, x, y, col, a, r=17):
    d.ellipse((x - r, y - r, x + r, y + r), outline=rgba(col, 255 * a), width=4)
    d.line([(x, y - 9), (x, y), (x + 7, y + 4)], fill=rgba(col, 255 * a), width=3)


# ------------------------------------------------------------------ scenes
SOLVED = ['clock wires on short paths', 'hold on the real wires', 'antenna repair placed', 'row fillers and density', 'the speed limit found']
WAIT = ['the routes have to close', 'a small final hold fix', 'all checks on the final file', 'LVS on a second machine']


def s_title(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 4.8, 0.6)
    if a > 0:
        card(d, (70, 195, 1010, 650), a, C_GREEN)
        text(d, (110, 245), 'Solved', 40, rgba(C_GREEN, 255 * a), 'Bold', 'lm')
        for i, s in enumerate(SOLVED):
            e = seg(t, 5.2 + i * 0.35, 0.4)
            if e > 0:
                tick(d, 130, 320 + i * 62, C_GREEN, e)
                text(d, (170, 320 + i * 62), s, 28, rgba(C_WHITE, 255 * e), 'SemiBold', 'lm')
    b = seg(t, 7.8, 0.6)
    if b > 0:
        card(d, (70, 680, 1010, 1075), b, C_AMBER)
        text(d, (110, 730), 'Still waiting', 40, rgba(C_AMBER, 255 * b), 'Bold', 'lm')
        for i, s in enumerate(WAIT):
            e = seg(t, 8.2 + i * 0.35, 0.4)
            if e > 0:
                clock_sym(d, 130, 805 + i * 62, C_AMBER, e)
                text(d, (170, 805 + i * 62), s, 28, rgba(C_WHITE, 255 * e), 'SemiBold', 'lm')


CORN = [('fast', 1771, 15), ('typical', 616, 14), ('slow', 511, 14)]


def s_hold(layer, t, dur):
    d = ImageDraw.Draw(layer)
    # the clock wire: detour, then direct
    a = seg(t, 0.4, 0.5)
    y = 300
    for x, lab in ((170, 'clock'), (910, 'flip-flop')):
        rrect(d, (x - 85, y - 36, x + 85, y + 36), 12, fill=rgba(CARD, 255 * a), outline=rgba(C_TEAL, 255 * a), width=3)
        text(d, (x, y), lab, 24, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
    sw = seg(t, 9.4, 1.0)
    det = [(255, y), (300, y), (300, 215), (470, 215), (470, 400), (640, 400), (640, 215), (780, 215), (780, y), (825, y)]
    d.line(det, fill=rgba(C_RED, 255 * a * (1 - sw)), width=6)
    if sw > 0:
        d.line([(255, y), (825, y)], fill=rgba(C_GREEN, 255 * sw), width=7)
        text(d, (540, y - 34), '42 clock wires on direct paths', 24, rgba(C_GREEN, 255 * sw), 'Bold', 'mm')
    else:
        text(d, (540, 440), 'a clock wire on a detour: the beat arrives late', 22, rgba(C_RED, 255 * a), 'SemiBold', 'mm')
    base = 940
    b = seg(t, 13.0, 0.5)
    if b > 0:
        d.line([(120, base), (960, base)], fill=rgba(C_DIM, 255 * b), width=2)
        d.rectangle((150, 478, 176, 504), fill=rgba(C_RED, 230 * b)); text(d, (190, 491), 'failing inputs before', 22, rgba(C_GREY, 255 * b), 'Medium', 'lm')
        b2 = seg(t, 21.5, 0.5)
        d.rectangle((560, 478, 586, 504), fill=rgba(C_GREEN, 240 * b2)); text(d, (600, 491), 'after the repair', 22, rgba(C_GREY, 255 * b2), 'Medium', 'lm')
    for i, (name, bef, aft) in enumerate(CORN):
        x = 170 + i * 280
        if b > 0:
            text(d, (x + 110, base + 34), name + ' corner', 24, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        g = seg(t, 17.5 + i * 0.5, 0.9)
        if g > 0:
            h = 370 * (bef / 1771.0) * g
            d.rectangle((x, base - h, x + 100, base), fill=rgba(C_RED, 230))
            text(d, (x + 50, base - h - 26), f'{bef:,}', 32, rgba(C_WHITE, 255 * g), 'Bold', 'mm')
        g2 = seg(t, 21.9 + i * 0.4, 0.9)
        if g2 > 0:
            h2 = max(370 * (aft / 1771.0), 6) * g2
            d.rectangle((x + 120, base - h2, x + 220, base), fill=rgba(C_GREEN, 240))
            text(d, (x + 170, base - h2 - 26), str(aft), 32, rgba(C_GREEN, 255 * g2), 'Bold', 'mm')
    e = seg(t, 23.5, 0.6)
    if e > 0:
        card(d, (90, 1020, 990, 1112), e, C_GREEN)
        text(d, (540, 1066), 'left: 14 pad inputs, and 1 flip-flop early by 0.03 ns', 26, rgba(C_WHITE, 255 * e), 'SemiBold', 'mm')


PASSES = [203334, 21429, 16292, 3469, 2416, 2023, 1858, 1642, 1575]


def s_ant(layer, t, dur):
    d = ImageDraw.Draw(layer)
    rows = [('wires over the antenna limit', '6,131', C_AMBER, 4.3), ('diodes beside their gates', '7,213', C_GREEN, 8.7),
            ('buffers at memory and pad pins', '1,315', C_TEAL, 13.1)]
    for i, (k, num, col, at) in enumerate(rows):
        a = seg(t, at, 0.5)
        if a <= 0:
            continue
        y = 195 + i * 112; dx = (1 - a) * 50
        card(d, (70 + dx, y, 1010 + dx, y + 96), a, col)
        text(d, (105 + dx, y + 48), k, 27, rgba(C_WHITE, 255 * a), 'SemiBold', 'lm')
        text(d, (975 + dx, y + 48), num, 50, rgba(col, 255 * a), 'Bold', 'rm')
    k = seg(t, 18.0, 0.6)
    if k > 0:
        text(d, (540, 565), 'each wire keeps its old path, only the link to its diode is new', 24, rgba(C_TEAL, 255 * k), 'SemiBold', 'mm')
    b = seg(t, 23.5, 0.5)
    if b > 0:
        base, top = 1010, 640
        text(d, (540, 615), 'routing conflicts after each pass', 22, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        d.line([(110, base), (980, base)], fill=rgba(C_DIM, 255 * b), width=2)
        lo, hi = math.log10(300), math.log10(250000)
        n_show = len(PASSES) * min(1.0, max(0.0, (t - 24.0) / 5.0))
        for i, v in enumerate(PASSES):
            if i >= n_show:
                break
            x = 150 + i * 90
            h = (base - top) * (math.log10(v) - lo) / (hi - lo)
            col = C_RED if v > 10000 else (C_AMBER if v > 2500 else C_GREEN)
            d.rectangle((x, base - h, x + 64, base), fill=rgba(col, 230))
            if i in (0, 3, 8):
                text(d, (x + 32, base - h - 22), f'{v:,}', 24, rgba(C_WHITE, 255), 'Bold', 'mm')
        text(d, (150, base + 28), 'start', 20, rgba(C_GREY, 255 * b), 'Medium', 'lm')
        text(d, (934, base + 28), 'pass 8', 20, rgba(C_GREY, 255 * b), 'Medium', 'rm')
        text(d, (540, base + 28), 'logarithmic scale', 20, rgba(C_DIM, 255 * b), 'Medium', 'mm')
        pill(d, 985, 1070, 'PASS 9 OF 16 RUNNING', C_BLUE, seg(t, 29.4, 0.5))


def s_fill(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    # a cell row with gaps; the filler cells drop in
    y0 = 300
    cells = [(110, 150), (300, 110), (470, 190), (720, 90), (860, 110)]          # logic cells: x, width
    gaps = [(260, 40), (410, 60), (660, 60), (810, 50)]
    text(d, (540, 230), 'one row of cells', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    d.rectangle((110, y0 + 92, 970, y0 + 104), fill=rgba(C_DIM, 255 * a))
    for x, w in cells:
        rrect(d, (x, y0, x + w, y0 + 90), 6, fill=rgba(CARD, 255 * a), outline=rgba(C_TEAL, 255 * a), width=2)
    g = seg(t, 4.5, 1.2)
    for i, (x, w) in enumerate(gaps):
        if g <= 0:
            d.rectangle((x + 4, y0 + 30, x + w - 4, y0 + 60), outline=rgba(C_RED, 200 * a), width=2)
        else:
            yy = y0 - (1 - g) * 110
            rrect(d, (x + 2, yy, x + w - 2, yy + 90), 6, fill=rgba(mix(C_GREEN, BG, .6), 255 * g), outline=rgba(C_GREEN, 255 * g), width=2)
    if g <= 0:
        text(d, (540, y0 + 140), 'gaps between the cells', 22, rgba(C_RED, 255 * a), 'SemiBold', 'mm')
    else:
        text(d, (540, y0 + 140), 'filler cells close the gaps: the wells underneath are continuous', 22, rgba(C_GREEN, 255 * g), 'SemiBold', 'mm')
    rows = [('row filler cells placed', '1,080,061', C_GREEN, 10.0), ('front-end rule tables with them', '11 of 11 clean', C_GREEN, 14.8),
            ('density violations with them', '0', C_GREEN, 17.8), ('the final file carries them', 'YES', C_TEAL, 20.6)]
    for i, (k, num, col, at) in enumerate(rows):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 520 + i * 145; dx = (1 - e) * 50
        card(d, (70 + dx, y, 1010 + dx, y + 124), e, col)
        text(d, (105 + dx, y + 62), k, 27, rgba(C_WHITE, 255 * e), 'SemiBold', 'lm')
        text(d, (975 + dx, y + 62), num, 44, rgba(col, 255 * e), 'Bold', 'rm')


SPEED = [(0, 10.0), (1, 15.0), (4, 16.4), (10, 18.9), (20, 22.2), (30, 25.1), (50, 26.9)]


def s_speed(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    text(d, (540, 215), 'clock speed at the slow corner, in MHz', 26, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    base = 760
    d.line([(110, base), (980, base)], fill=rgba(C_DIM, 255 * a), width=2)
    text(d, (540, base + 70), 'wires put on a direct path, most useful first', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    when = (4.0, 13.5, 16.8, 17.2, 17.6, 18.0, 18.6)
    for i, (n, mhz) in enumerate(SPEED):
        g = seg(t, when[i], 0.8)
        if g <= 0:
            continue
        x = 140 + i * 118
        h = 440 * (mhz / 27.0) * g
        col = C_RED if n == 0 else (C_AMBER if n < 30 else C_GREEN)
        d.rectangle((x, base - h, x + 84, base), fill=rgba(col, 230))
        text(d, (x + 42, base - h - 26), f'{mhz:.1f}'.rstrip('0').rstrip('.') if mhz != 10.0 else '10', 32, rgba(C_WHITE, 255 * g), 'Bold', 'mm')
        text(d, (x + 42, base + 28), str(n), 24, rgba(C_GREY, 255 * g), 'SemiBold', 'mm')
    b = seg(t, 21.0, 0.6)
    if b > 0:
        card(d, (70, 870, 1010, 980), b, C_TEAL)
        text(d, (540, 925), 'the 50 wires are prepared: a separate line routes them tonight', 25, rgba(C_WHITE, 255 * b), 'SemiBold', 'mm')
    c = seg(t, 26.5, 0.6)
    if c > 0:
        card(d, (70, 1000, 1010, 1110), c, C_GREEN)
        text(d, (540, 1055), 'if it closes cleanly: speed. If not: the chip still works, slower', 25, rgba(C_WHITE, 255 * c), 'SemiBold', 'mm')


def step(d, y, a, col, n, k, v, st):
    card(d, (70, y, 1010, y + 170), a, col)
    d.ellipse((96, y + 57, 152, y + 113), fill=rgba(col, 255 * a))
    text(d, (124, y + 85), n, 30, rgba(BG, 255 * a), 'Bold', 'mm')
    text(d, (180, y + 62), k, 30, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
    text(d, (180, y + 112), v, 23, rgba(C_GREY, 255 * a), 'Medium', 'lm')
    pill(d, 985, y + 16, st, col, a)


def s_routes(layer, t, dur):
    d = ImageDraw.Draw(layer)
    rows = [('1', 'The antenna route finishes', 'pass 9 of 16 now, done this evening', 'RUNNING', C_BLUE, 4.6),
            ('2', 'Its last conflicts close to zero', 'the least predictable step', 'NEXT', C_AMBER, 8.9),
            ('3', 'The speed line, beside it', 'the 50 wires on direct paths', 'NEXT', C_TEAL, 14.4),
            ('4', 'A small final hold fix', 'new routes move some wires', 'AFTER', C_PURPLE, 18.3)]
    for i, (n, k, v, st, col, at) in enumerate(rows):
        a = seg(t, at, 0.5)
        if a > 0:
            step(d, 215 + i * 200, a, col, n, k, v, st)


CHECKS = [('Design rule check', 'all 26 tables and the GatPoly filler table', C_BLUE, 5.4),
          ('Density', 'the rehearsal with row fillers shows 0', C_BLUE, 11.5),
          ('Every wire traced', 'layout against the netlist', C_BLUE, 12.7),
          ('Antenna check', 'after the repair', C_BLUE, 15.8),
          ('Hold at three corners', 'on the real wires', C_BLUE, 17.6),
          ('LVS, on a second machine', 'rehearsal on the previous candidate first', C_PURPLE, 21.9)]


def s_checks(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 2.2, 0.5)
    text(d, (540, 212), 'every check is repeated on the final file', 26, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    for i, (k, v, col, at) in enumerate(CHECKS):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 258 + i * 144; dx = (1 - e) * 50
        card(d, (70 + dx, y, 1010 + dx, y + 126), e, col)
        clock_sym(d, 125 + dx, y + 63, col, e, 20)
        text(d, (175 + dx, y + 44), k, 29, rgba(C_WHITE, 255 * e), 'Bold', 'lm')
        text(d, (175 + dx, y + 88), v, 23, rgba(C_GREY, 255 * e), 'Medium', 'lm')


TIME = [('tonight', 'the antenna route finishes', C_BLUE, 3.4),
        ('overnight', 'closure to zero, and the speed line', C_BLUE, 5.9),
        ('12 Nov, morning', 'the small final hold fix', C_PURPLE, 9.1),
        ('12 Nov, afternoon', 'final checks, release on a branch', C_GREEN, 12.7),
        ('then, your turn', 'merge, post on the IHP issue, confirm', C_TEAL, 17.7),
        ('16 Nov, 04:29', 'deadline: 15 Nov, 23:59 in Germany', C_AMBER, 23.9)]


def s_time(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    text(d, (540, 205), 'Indian Standard Time', 24, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    g = min(1.0, max(0.0, (t - 3.0) / 21.0))
    d.line([(150, 265), (150, 265 + 830 * g)], fill=rgba(C_DIM, 255 * a), width=4)
    for i, (when, what, col, at) in enumerate(TIME):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 270 + i * 140
        dot(d, (150, y + 52), col, 16, e)
        card(d, (200, y, 1010, y + 112), e, col)
        text(d, (235, y + 34), when, 29, rgba(col, 255 * e), 'Bold', 'lm')
        text(d, (235, y + 80), what, 24, rgba(C_WHITE, 255 * e), 'Medium', 'lm')
    n = seg(t, 31.4, 0.5)
    if n > 0:
        text(d, (540, 1122), 'estimates: the closure steps are the uncertain part', 22, rgba(C_GREY, 255 * n), 'Medium', 'mm')


def s_end(layer, t, dur):
    fp = B.FP(340, 420, 400); B.draw_die(layer, fp, dim=True)
    d = ImageDraw.Draw(layer)
    text(d, (540, 900), 'SoC2611', 40, C_WHITE, 'Bold', 'mm')
    text(d, (540, 955), 'solved and waiting · 11 November 2026, evening', 24, C_GREY, 'Medium', 'mm')


SCENES = [
    ('Before the final submission', s_title,
     'This is where {S o C twenty six eleven|SoC2611} stands on the evening of the eleventh of November. '
     'First, what is solved. Then, what we are still waiting for, before the file goes to {I H P|IHP}.'),
    ('Solved: clock and hold', s_hold,
     'Solved, first: the clock and hold. Forty-two clock wires had been pushed onto long detours, so some flip-flops '
     'heard the clock late. They now run on short, direct paths. Then we repaired hold on the real, measured wires. '
     'At the fast corner, the failing inputs went from one thousand seven hundred and seventy-one to fifteen. '
     'Fourteen of those are pad inputs, which are excluded by design. One flip-flop is left inside the chip, early by '
     'three hundredths of a nanosecond.'),
    ('Solved: antenna repair placed', s_ant,
     'Solved, second: the antenna repair is placed. Six thousand one hundred and thirty-one wires were over the antenna '
     'limit. Seven thousand two hundred and thirteen diodes now sit beside their gates, with one thousand three hundred '
     'and fifteen small buffers at memory and pad pins. Each wire keeps its old path, and only the short link to its '
     'diode is new. That route is converging: from two hundred thousand conflicts to about one thousand five hundred, '
     'at pass nine of sixteen.'),
    ('Solved: fillers and density', s_fill,
     'Solved, third: the empty places in the cell rows. {I H P|IHP} asks for filler cells there, so that the wells '
     'underneath are continuous. A trial placed one million and eighty thousand filler cells. With them, the eleven '
     'front-end rule tables are clean, and the density check shows zero violations. So the final file will carry them.'),
    ('Found: what limits the speed', s_speed,
     'We also found what limits the speed. At the slow corner, the chip runs at ten megahertz today. The cause is a '
     'small number of wires on long detours. One wire alone, once shortened, lifts the speed to fifteen megahertz. '
     'The fifty most useful wires would bring it to about twenty-seven. Those fifty have their direct paths prepared, '
     'and a separate line routes them tonight. If that line closes cleanly, the final file gets the speed. '
     'If not, the chip still works, at the lower clock.'),
    ('Waiting: the routes', s_routes,
     'Now, what we are waiting for. First, the routes. The antenna route finishes its sixteen passes this evening. '
     'Then its last conflicts are closed to zero, which is the least predictable step. Beside it, the speed line routes '
     'the fifty wires. After that comes a small final hold fix, because new routes move some wires.'),
    ('Waiting: the final checks', s_checks,
     'Second, the checks. Every check is repeated on the final file. The design rule check, with all twenty-six '
     'tables and the GatPoly filler table. Density. The trace of every wire in the layout against the netlist. '
     'The antenna check. And hold, at three corners, on the real wires. {L V S|LVS}, the comparison of layout and '
     'schematic, has never finished on this machine. So it runs on a second machine, starting with a rehearsal on '
     'the previous candidate.'),
    ('The path to submission', s_time,
     'The path to submission, in Indian time. Tonight, the antenna route finishes. Overnight come the closure and '
     'the speed line. On the morning of the twelfth, the small hold fix. In the afternoon, the final checks, and the '
     'release on a branch. Then it is your turn: merge the release, post the note on the {I H P|IHP} issue, and '
     'confirm the delivery. The deadline is the sixteenth, at four twenty-nine in the morning. That leaves about three '
     'days of margin. These are estimates, and the closure steps are the uncertain part.'),
    ('', s_end, ''),
]

if __name__ == '__main__':
    B.SCENES = SCENES
    B.main()
