#!/usr/bin/env python3
"""Video of 13 November 2026: the slowest logic step of the chip, shown on the real layout.
The step needs 29.6 ns at the slow corner and has seven cells; two drive-1 gates take 23 ns of it (13.9 ns and
9.5 ns), because the wire between them is 8,658 um long although the two pins are 142 um apart. The wire is one of
the 202 nets that the routing closure of 11 November took out of crowded places; its planned detour was about
200 um wide, the route that came out runs along the right side of the chip.
Repairing it (strong buffers along the wire) would bring this step to about 9 ns (estimate), but: 493 single
stages of 3 ns or more are on the worst paths; with all of them at 2 ns the slowest logic step still needs 25.0 ns
(up to 64 gates in one step), and the path into the memories, which sets the rating (34.0 ns = 29.4 MHz), has no
slow stage and stays as it is (setup_path_stages.py on the slow-corner report of the v.2.5.0 database).
Data: data_1113/wire0050.txt (M = memory macro box, S = wire segment in route order, P = pin; um).
Same renderer, captions and voice (en-GB-RyanNeural) as make_status_video.py.
usage: make_slowest_wire_video.py <out_dir> [--preview] [--jobs N]     (writes <out_dir>/SoC2611_status.mp4)"""
import importlib.util
import math
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('svbase', os.path.join(HERE, 'make_status_video.py'))
B = importlib.util.module_from_spec(spec)
sys.modules['svbase'] = B          # the render pool pickles svbase.render_scene by name
spec.loader.exec_module(B)
text, rrect, seg, rgba, mix, lerp = B.text, B.rrect, B.seg, B.rgba, B.mix, B.lerp
C_WHITE, C_GREY, C_DIM, C_AMBER, C_TEAL, C_BLUE, C_GREEN, C_RED, C_PURPLE, BG = (
    B.C_WHITE, B.C_GREY, B.C_DIM, B.C_AMBER, B.C_TEAL, B.C_BLUE, B.C_GREEN, B.C_RED, B.C_PURPLE, B.BG)
CARD = (20, 26, 38); EDGE = (40, 48, 64)
DIE = 6600.0

MACS = []; SEGS = []; PINS = {}
for l in open(os.path.join(HERE, 'data_1113', 'wire0050.txt')):
    p = l.split()
    if p[0] == 'M':
        MACS.append(tuple(float(a) for a in p[1:5]))
    elif p[0] == 'S':
        SEGS.append((p[1],) + tuple(float(a) for a in p[2:6]))
    elif p[0] == 'P':
        PINS[p[1]] = (float(p[2]), float(p[3]))
DRV = PINS['_0998_/Y']; SNK = PINS['_0999_/B1']
SEG_LEN = [abs(s[3] - s[1]) + abs(s[4] - s[2]) for s in SEGS]
WIRE_UM = sum(SEG_LEN)
DIRECT_UM = abs(DRV[0] - SNK[0]) + abs(DRV[1] - SNK[1])
# the quarter of the chip that holds the route: x 3300..6600, y 0..3300 um, on a 900 px square
QX, QY, QS = 3300.0, 0.0, 3300.0
MX, MY, MS = 90, 190, 900


def clamp(x): return max(0.0, min(1.0, x))


def q(x, y):
    return (MX + (x - QX) * MS / QS, MY + (QY + QS - y) * MS / QS)


def card(d, box, a, outline=EDGE, fill=CARD, alpha=235):
    rrect(d, box, 18, fill=rgba(fill, alpha * a), outline=rgba(outline, 255 * a), width=2)


def dot(d, p, col, r=8, a=1.0):
    d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=rgba(col, 255 * a))


def quarter_map():
    """the quarter of the chip with its memory blocks, drawn once"""
    im = Image.new('RGBA', (B.W, B.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((MX, MY, MX + MS, MY + MS), fill=rgba((14, 19, 30), 255))
    for x0, y0, x1, y1 in MACS:
        if x1 < QX or y0 > QY + QS:
            continue
        a = q(max(x0, QX), min(y1, QY + QS)); b = q(min(x1, QX + QS), max(y0, QY))
        d.rectangle((a[0], a[1], b[0], b[1]), fill=rgba((44, 54, 72), 255), outline=rgba((70, 82, 104), 255))
    # die edge (right and bottom side of the quarter) and the frame of the view
    e0 = q(DIE, 0)
    d.line([(e0[0], MY), (e0[0], e0[1]), (MX, e0[1])], fill=rgba(C_GREY, 255), width=3)
    d.rectangle((MX, MY, MX + MS, MY + MS), outline=rgba(EDGE, 255), width=2)
    return im


QMAP = quarter_map()


def locator(d, a):
    """the whole chip, small, with the shown quarter marked"""
    x0, y0, s = 104, 204, 190
    rrect(d, (x0 - 8, y0 - 8, x0 + s + 8, y0 + s + 34), 10, fill=rgba(CARD, 245 * a), outline=rgba(EDGE, 255 * a), width=2)
    d.rectangle((x0, y0, x0 + s, y0 + s), fill=rgba((14, 19, 30), 255 * a), outline=rgba(C_GREY, 255 * a))
    for mx0, my0, mx1, my1 in MACS:
        d.rectangle((x0 + mx0 * s / DIE, y0 + (DIE - my1) * s / DIE, x0 + mx1 * s / DIE, y0 + (DIE - my0) * s / DIE),
                    fill=rgba((54, 66, 88), 255 * a))
    d.rectangle((x0 + s / 2, y0 + s / 2, x0 + s, y0 + s), outline=rgba(C_AMBER, 255 * a), width=3)
    text(d, (x0 + s / 2, y0 + s + 14), 'the whole chip, 6.6 mm', 15, rgba(C_GREY, 255 * a), 'Medium', 'mm')


def draw_wire(d, frac, col=C_AMBER, width=4, a=1.0):
    """the first `frac` of the wire, in route order; returns (length drawn um, head point)"""
    todo = WIRE_UM * clamp(frac); head = None; done = 0.0
    for (lay, x0, y0, x1, y1), ln in zip(SEGS, SEG_LEN):
        if todo <= 0:
            break
        if ln <= todo:
            d.line([q(x0, y0), q(x1, y1)], fill=rgba(col, 255 * a), width=width); head = (x1, y1)
            todo -= ln; done += ln
        else:
            f = todo / ln
            xm, ym = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            d.line([q(x0, y0), q(xm, ym)], fill=rgba(col, 255 * a), width=width); head = (xm, ym)
            done += todo; todo = 0
    return done, head


def gates(d, a, labels=True):
    pd, ps = q(*DRV), q(*SNK)
    dot(d, pd, C_GREEN, 9, a); dot(d, ps, C_BLUE, 9, a)
    if labels:
        text(d, (pd[0] - 18, pd[1] - 6), 'gate 1', 21, rgba(C_GREEN, 255 * a), 'Bold', 'rm')
        text(d, (ps[0] - 18, ps[1] + 8), 'gate 2', 21, rgba(C_BLUE, 255 * a), 'Bold', 'rm')


# ------------------------------------------------------------------ scene 0: title
def s_title(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.4, 0.5)
    text(d, (540, 215), 'the slowest logic step of the chip', 27, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    rows = [('1', 'Where it is on the chip', C_TEAL, T0['c1']), ('2', 'Why it is slow', C_AMBER, T0['c2']),
            ('3', 'Why repairing it gains nothing', C_RED, T0['c3'])]
    for i, (n, k, col, at) in enumerate(rows):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 300 + i * 230
        card(d, (70, y, 1010, y + 190), e, col)
        d.ellipse((100, y + 55, 180, y + 135), fill=rgba(col, 255 * e))
        text(d, (140, y + 95), n, 42, rgba(BG, 255 * e), 'Bold', 'mm')
        text(d, (215, y + 95), k, 38, rgba(C_WHITE, 255 * e), 'Bold', 'lm')


T0 = dict(c1=4.8, c2=7.0, c3=8.9)

# ------------------------------------------------------------------ scene 1: seven cells
STAGES = [('flip-flop', 0.28, C_GREY), ('buffer', 1.49, C_TEAL), ('buffer', 1.29, C_TEAL), ('buffer', 1.63, C_TEAL),
          ('gate 1', 13.87, C_RED), ('gate 2', 9.47, C_RED), ('multiplexer', 1.06, C_GREY)]
T1 = dict(need=2.5, cells=8.0, buf=11.2, g1=19.0, g2=22.6, sum=25.2, why=29.5)


def s_cells(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, T1['need'], 0.5)
    if a > 0:
        card(d, (70, 190, 1010, 300), a, C_AMBER)
        text(d, (105, 245), 'slowest step, slow corner', 28, rgba(C_WHITE, 255 * a), 'SemiBold', 'lm')
        text(d, (975, 245), '29.6 ns', 40, rgba(C_AMBER, 255 * a), 'Bold', 'rm')
    times = [T1['cells'], T1['buf'], T1['buf'] + 0.4, T1['buf'] + 0.8, T1['g1'], T1['g2'], T1['g2'] + 1.5]
    x0, sc = 330, 44.0                      # px per ns
    for i, ((name, ns, col), at) in enumerate(zip(STAGES, times)):
        e = seg(t, T1['cells'] + i * 0.25, 0.4)
        if e <= 0:
            continue
        y = 345 + i * 88
        text(d, (300, y + 30), name, 27, rgba(C_WHITE if col != C_RED else C_RED, 255 * e), 'Bold', 'rm')
        d.rectangle((x0, y + 6, x0 + 14.5 * sc, y + 54), fill=rgba((16, 21, 32), 255 * e))
        g = seg(t, at, 0.9)
        if g > 0:
            d.rectangle((x0, y + 6, x0 + max(4, ns * sc * g), y + 54), fill=rgba(col, 235))
            text(d, (x0 + ns * sc + 14, y + 30), f'{ns:.1f} ns', 26, rgba(C_WHITE, 255 * g), 'Bold', 'lm')
    z = seg(t, T1['sum'], 0.6)
    if z > 0:
        card(d, (70, 985, 1010, 1075), z, C_RED)
        text(d, (540, 1030), 'two gates take 23 of the 29 ns', 31, rgba(C_WHITE, 255 * z), 'Bold', 'mm')
    w = seg(t, T1['why'], 0.6)
    if w > 0:
        text(d, (540, 1118), 'the reason is the wire between them', 25, rgba(C_AMBER, 255 * w), 'SemiBold', 'mm')


# ------------------------------------------------------------------ scene 2: the wire on the chip
T2 = dict(map=0.3, gates=5.6, apart=8.4, wire=13.3, wire_dur=10.8, ratio=27.8)


def s_map(layer, t, dur):
    a = seg(t, T2['map'], 0.6)
    if a > 0:
        m = QMAP.copy()
        if a < 1:
            m.putalpha(m.split()[3].point(lambda v: int(v * a)))
        layer.alpha_composite(m)
    d = ImageDraw.Draw(layer)
    if a > 0:
        locator(d, a)
        text(d, (MX + MS - 8, MY + 22), 'lower right quarter · grey = memory blocks', 17, rgba(C_GREY, 255 * a), 'Medium', 'rm')
    f = (t - T2['wire']) / T2['wire_dur']
    if f > 0:
        done, head = draw_wire(d, f)
        if head is not None and f < 1:
            dot(d, q(*head), C_WHITE, 6)
        card(d, (70, 1100, 1010, 1160), 1.0)
        text(d, (105, 1130), 'wire laid', 23, rgba(C_GREY), 'Medium', 'lm')
        text(d, (975, 1130), f'{done:,.0f} um', 30, rgba(C_AMBER), 'Bold', 'rm')
    g = seg(t, T2['gates'], 0.5)
    if g > 0:
        gates(d, g)
    ap = seg(t, T2['apart'], 0.5)
    if ap > 0 and f <= 0:
        pd, ps = q(*DRV), q(*SNK)
        d.line([pd, ps], fill=rgba(C_WHITE, 255 * ap), width=2)
        card(d, (70, 1100, 1010, 1160), ap)
        text(d, (540, 1130), f'the two gates are {DIRECT_UM:.0f} um apart', 27, rgba(C_WHITE, 255 * ap), 'Bold', 'mm')
    r = seg(t, T2['ratio'], 0.6)
    if r > 0:
        x0, y0 = 104, 470
        card(d, (x0 - 8, y0, x0 + 300, y0 + 150), r, C_AMBER, alpha=250)
        text(d, (x0 + 146, y0 + 45), '8.7 mm of wire', 28, rgba(C_AMBER, 255 * r), 'Bold', 'mm')
        text(d, (x0 + 146, y0 + 88), f'{WIRE_UM / DIRECT_UM:.0f} times the', 22, rgba(C_WHITE, 255 * r), 'Medium', 'mm')
        text(d, (x0 + 146, y0 + 118), 'direct distance', 22, rgba(C_WHITE, 255 * r), 'Medium', 'mm')


# ------------------------------------------------------------------ scene 3: why it runs like this
T3 = dict(c1=2.6, c2=8.5, c3=20.3)


def s_why(layer, t, dur):
    m = QMAP.copy()
    layer.alpha_composite(m)
    d = ImageDraw.Draw(layer)
    draw_wire(d, 1.0, mix(C_AMBER, BG, .25), 3)
    gates(d, 1.0, labels=False)
    rows = [(T3['c1'], C_RED, '11 November', ['short circuits in crowded', 'places between the', 'memory blocks']),
            (T3['c2'], C_AMBER, '202 wires sent around', ['this wire is one of them;', 'its planned detour was', 'small, the route is long']),
            (T3['c3'], C_GREEN, 'routing closed', ['0 violations with this', 'route, so the wire has', 'been left alone since'])]
    for i, (at, col, head, lines) in enumerate(rows):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 215 + i * 255
        card(d, (100, y, 460, y + 225), e, col, alpha=250)
        text(d, (124, y + 42), head, 27, rgba(col, 255 * e), 'Bold', 'lm')
        for j, s in enumerate(lines):
            text(d, (124, y + 96 + j * 38), s, 22, rgba(C_WHITE, 255 * e), 'Medium', 'lm')


# ------------------------------------------------------------------ scene 4: can we repair it
T4 = dict(o1=4.0, o2=9.4, but=17.1, r1=20.0, r1b=26.5, r2=36.5, r3=45.0)


def bar_row(d, y, label, sub, before, after, col, t, at, at_b, sc=17.0):
    e = seg(t, at, 0.5)
    if e <= 0:
        return
    text(d, (105, y), label, 26, rgba(C_WHITE, 255 * e), 'Bold', 'lm')
    text(d, (105, y + 34), sub, 19, rgba(C_GREY, 255 * e), 'Medium', 'lm')
    x0 = 105
    g = seg(t, at + 0.3, 0.8)
    d.rectangle((x0, y + 60, x0 + before * sc * g, y + 92), fill=rgba(mix(col, BG, .45), 255))
    text(d, (x0 + before * sc + 12, y + 76), f'now {before:.1f} ns', 22, rgba(C_GREY, 255 * g), 'SemiBold', 'lm')
    h = seg(t, at_b, 0.8)
    if h > 0:
        d.rectangle((x0, y + 100, x0 + after * sc * h, y + 132), fill=rgba(col, 255))
        text(d, (x0 + after * sc + 12, y + 116), f'repaired {after:.1f} ns', 22, rgba(C_WHITE, 255 * h), 'Bold', 'lm')


def s_repair(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, T4['o1'], 0.5)
    if a > 0:
        card(d, (70, 190, 530, 400), a, C_RED)
        text(d, (96, 228), 'lay it straight again', 27, rgba(C_RED, 255 * a), 'Bold', 'lm')
        text(d, (96, 282), 'back into the crowded place', 21, rgba(C_WHITE, 255 * a), 'Medium', 'lm')
        text(d, (96, 322), 'risk: new short circuits', 21, rgba(C_WHITE, 255 * a), 'Medium', 'lm')
    b = seg(t, T4['o2'], 0.5)
    if b > 0:
        card(d, (550, 190, 1010, 400), b, C_GREEN)
        text(d, (576, 228), 'strong buffers on the wire', 27, rgba(C_GREEN, 255 * b), 'Bold', 'lm')
        text(d, (576, 282), 'this step: 29 ns to about 9 ns', 21, rgba(C_WHITE, 255 * b), 'Medium', 'lm')
        text(d, (576, 322), 'an estimate, not yet done', 21, rgba(C_GREY, 255 * b), 'Medium', 'lm')
    z = seg(t, T4['but'], 0.5)
    if z > 0:
        card(d, (70, 430, 1010, 1010), z)
        text(d, (540, 470), 'but the chip does not get faster', 28, rgba(C_AMBER, 255 * z), 'Bold', 'mm')
    bar_row(d, 520, 'slowest logic step', 'all 493 slow stages repaired: up to 64 gates in a row remain',
            29.6, 25.0, C_TEAL, t, T4['r1'], T4['r1b'])
    bar_row(d, 690, 'path into the memories', 'sets the speed of the chip · no slow stage in it',
            34.0, 34.0, C_RED, t, T4['r2'], T4['r2'] + 2.5)
    r = seg(t, T4['r3'], 0.6)
    if r > 0:
        d.line([(95, 868), (985, 868)], fill=rgba(EDGE, 255 * r), width=2)
        text(d, (105, 930), 'rating of the chip', 28, rgba(C_WHITE, 255 * r), 'Bold', 'lm')
        text(d, (985, 915), '29.4 MHz', 40, rgba(C_AMBER, 255 * r), 'Bold', 'rm')
        text(d, (985, 962), 'before and after', 21, rgba(C_GREY, 255 * r), 'Medium', 'rm')


# ------------------------------------------------------------------ scene 5: where the cure is
T5 = dict(c1=4.9, c2=9.8, c3=12.6, keep=15.6)


def s_cure(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.5, 0.5)
    text(d, (540, 215), 'not in this wire: in the next chip', 27, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    rows = [(T5['c1'], C_TEAL, 'memories next to their logic', 'no wire has to go around them'),
            (T5['c2'], C_BLUE, 'registers inside the long steps', 'fewer gates in a row'),
            (T5['c3'], C_PURPLE, 'no half step into the memories', 'a whole step for every memory path')]
    for i, (at, col, k, v) in enumerate(rows):
        e = seg(t, at, 0.5)
        if e <= 0:
            continue
        y = 280 + i * 215
        card(d, (70, y, 1010, y + 185), e, col)
        text(d, (105, y + 70), k, 34, rgba(C_WHITE, 255 * e), 'Bold', 'lm')
        text(d, (105, y + 124), v, 24, rgba(C_GREY, 255 * e), 'Medium', 'lm')
    z = seg(t, T5['keep'], 0.6)
    if z > 0:
        card(d, (70, 955, 1010, 1045), z, C_AMBER)
        text(d, (540, 1000), 'this chip stays as it is', 30, rgba(C_WHITE, 255 * z), 'Bold', 'mm')


def s_end(layer, t, dur):
    fp = B.FP(340, 420, 400); B.draw_die(layer, fp, dim=True)
    d = ImageDraw.Draw(layer)
    text(d, (540, 900), 'SoC2611', 40, C_WHITE, 'Bold', 'mm')
    text(d, (540, 955), 'the slowest wire · 13 November 2026', 24, C_GREY, 'Medium', 'mm')


SCENES = [
    ('The slowest wire', s_title,
     'This film shows the slowest logic step of {S o C twenty six eleven|SoC2611}. Where it is on the chip. '
     'Why it is slow. And why repairing it would not make the chip faster.'),
    ('Seven cells, two of them slow', s_cells,
     'At the slow corner, the slowest step from one flip-flop to the next needs {twenty-nine point six|29.6} '
     'nanoseconds. It is not long logic. It has only seven cells. '
     'Three small buffers take about one and a half nanoseconds each. '
     'Then come two small gates. The first takes {thirteen point nine|13.9} nanoseconds. '
     'The second takes {nine and a half|9.5}. '
     'These two gates alone take {twenty-three|23} of the {twenty-nine|29} nanoseconds. '
     'The reason is the wire between them.'),
    ('The wire on the chip', s_map,
     'Here is the lower right quarter of the real chip. The grey blocks are memories. '
     'The two gates sit here. '
     'They are neighbours: {one hundred and forty-two|142} micrometres apart. '
     'Now watch the wire that joins them. It does not go straight. It leaves the area, and wanders far out between '
     'the memory blocks, to the right edge of the chip, and back again. '
     '{Eight point seven|8.7} millimetres of thin wire. '
     'That is sixty times the direct distance, on a chip that is {six point six|6.6} millimetres wide. '
     'A small gate needs a long time to charge that much wire.'),
    ('Why it runs like this', s_why,
     'Why does it run like this? On the eleventh of November, the routing had short circuits in crowded places '
     'between the memory blocks. '
     '{Two hundred and two|202} wires were taken out of those places, and sent around them. This wire is one of '
     'them. Its planned detour was small, but the router found its room far away. '
     'With this route, the routing closed with zero violations. That is why the wire has been left alone since.'),
    ('Can we repair it?', s_repair,
     'Can we repair it? There are two ways. '
     'Laying it straight again would take it back into the crowded place, with the risk of new short circuits. '
     'Strong buffers along the wire are safer. They would bring this step from {twenty-nine|29} nanoseconds to '
     'about nine. '
     'But the chip would not get faster. '
     'There are {four hundred and ninety-three|493} slow stages like this one. '
     'Even with all of them repaired, the slowest step still needs {twenty-five|25} nanoseconds, because other '
     'steps have up to {sixty-four|64} gates in a row. '
     'And the speed of the chip is not set by this step at all. It is set by the path into the memories. '
     'That path needs {thirty-four|34} nanoseconds, and has no slow stage to repair. '
     'So the rating stays at {twenty-nine point four megahertz|29.4 MHz}.'),
    ('Where the cure is', s_cure,
     'So the cure is not in this wire. It is in the next chip. '
     'Memories placed next to their logic, so that no wire has to go around them. '
     'Registers inside the long steps. '
     'And no half step into the memories. '
     'This chip stays as it is.'),
    ('', s_end, ''),
]

if __name__ == '__main__':
    B.SCENES = SCENES
    B.main()
