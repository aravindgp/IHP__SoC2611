#!/usr/bin/env python3
"""Short explainer video of the SoC2611 routing-closure status, in the style of a short-form technical clip:
dark 1080x1350 canvas, bold title, one animated diagram per scene, a caption pill in which the word being spoken is
highlighted, British male narration (edge-tts en-GB-RyanNeural; its word timings drive the captions).

Each scene = (title, draw function, narration). The narration is synthesised per scene, the scene lasts as long as
its audio plus a short tail, frames are drawn with PIL (one process per scene) and piped to ffmpeg, the scene clips
are concatenated and muxed with the padded audio.

usage: make_status_video.py <out_dir> [--fps 30] [--voice en-GB-RyanNeural] [--preview]
       --preview writes one PNG per scene (mid-scene frame) instead of the video.
Narration markup: {spoken words|Display text} shows "Display text" in the caption while "spoken words" are read.
"""
import argparse, asyncio, hashlib, json, math, os, re, subprocess, wave
from difflib import SequenceMatcher
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1350
BG = (10, 14, 23)
FONT_DIR = os.environ.get('FONT_DIR', '/root/.claude/jobs/658ac326/tmp/fonts')
MAC_FILE = '/workspace/chip_fp2/handoff/macros_name_w_h_um.txt'
PL_FILE = '/workspace/chip_fp2/handoff/H12_cpueast.pl'
BLK_FILE = '/workspace/chip_fp2/dpass/H13-pockets_blockages.txt'
DIE = 6600.0
C_WHITE = (240, 243, 247); C_GREY = (126, 134, 148); C_DIM = (70, 78, 92); C_AMBER = (247, 181, 74)
C_TEAL = (56, 189, 214); C_BLUE = (74, 138, 255); C_GREEN = (72, 199, 116); C_RED = (240, 84, 84)
C_PURPLE = (171, 120, 240); C_PILL = (28, 33, 45)

_fonts = {}
def font(size, weight='Bold'):
    k = (size, weight)
    if k not in _fonts:
        p = os.path.join(FONT_DIR, f'Inter-{weight}.ttf')
        if not os.path.exists(p):
            p = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if weight in ('Bold', 'SemiBold', 'ExtraBold') \
                else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        _fonts[k] = ImageFont.truetype(p, size)
    return _fonts[k]

def ease(x):                       # ease-out cubic, clamped
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def lerp(a, b, x): return a + (b - a) * x
def seg(t, t0, d): return ease((t - t0) / d)
def mix(c1, c2, x): return tuple(int(round(lerp(a, b, x))) for a, b in zip(c1, c2))
def rgba(c, a=255): return (c[0], c[1], c[2], max(0, min(255, int(a))))

def text(d, xy, s, size, color=C_WHITE, weight='Bold', anchor='la'):
    d.text(xy, s, font=font(size, weight), fill=color, anchor=anchor)

def glow(layer, draw_fn, radius=10, alpha=0.75):
    """draw_fn(ImageDraw) on a scratch RGBA; blurred copy composited under the sharp copy."""
    g = Image.new('RGBA', layer.size, (0, 0, 0, 0)); draw_fn(ImageDraw.Draw(g))
    b = g.filter(ImageFilter.GaussianBlur(radius))
    if alpha < 1:
        b.putalpha(b.split()[3].point(lambda v: int(v * alpha)))
    layer.alpha_composite(b); layer.alpha_composite(g)

def hatch(layer, box, color, step=14, width=2):
    x0, y0, x1, y1 = [int(v) for v in box]
    if x1 <= x0 or y1 <= y0: return
    h = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0)); d = ImageDraw.Draw(h)
    for s in range(-(y1 - y0), x1 - x0, step):
        d.line([(s, y1 - y0), (s + (y1 - y0), 0)], fill=color, width=width)
    layer.alpha_composite(h, (x0, y0))

def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

# ------------------------------------------------------------------ floorplan data
def load_fp():
    wh = {}
    for ln in open(MAC_FILE):
        p = ln.split()
        if len(p) >= 4: wh[p[0]] = (float(p[2]), float(p[3]))
    macs = []
    for ln in open(PL_FILE):
        p = ln.split()
        if len(p) >= 3 and p[0] in wh:
            w, h = wh[p[0]]; x, y = float(p[1]), float(p[2]); macs.append((x, y, x + w, y + h))
    blks = []
    for item in open(BLK_FILE).read().replace('\n', ';').split(';'):
        p = item.split()
        if len(p) == 4: blks.append(tuple(float(v) for v in p))
    return macs, blks

MACS, BLKS = load_fp()
BIG_BLKS = [b for b in BLKS if (b[2] - b[0]) * (b[3] - b[1]) > 60000]      # the two H10 placement blockages
POCKETS = [b for b in BLKS if b not in BIG_BLKS]

class FP:
    """die -> pixel mapping; (ox, oy) top-left, size px."""
    def __init__(self, ox, oy, size): self.ox, self.oy, self.s = ox, oy, size / DIE
    def px(self, x, y): return (self.ox + x * self.s, self.oy + (DIE - y) * self.s)
    def box(self, b):
        x0, y0 = self.px(b[0], b[3]); x1, y1 = self.px(b[2], b[1]); return (x0, y0, x1, y1)

def draw_die(layer, fp, macs_frac=1.0, macro_col=C_TEAL, macro_alpha=200, ring=True, dim=False):
    d = ImageDraw.Draw(layer)
    x0, y0 = fp.px(0, DIE); x1, y1 = fp.px(DIE, 0)
    d.rectangle((x0, y0, x1, y1), fill=rgba((14, 19, 30)), outline=rgba((60, 70, 90)), width=2)
    if ring:
        p = 300 * fp.s
        d.rectangle((x0 + p, y0 + p, x1 - p, y1 - p), outline=rgba((48, 56, 74)), width=1)
    n = int(round(len(MACS) * macs_frac))
    def body(dd):
        for m in MACS[:n]:
            dd.rectangle(fp.box(m), fill=rgba(macro_col, macro_alpha if not dim else 70),
                         outline=rgba(mix(macro_col, C_WHITE, .3), 160 if not dim else 60))
    if n:
        if dim: body(d)
        else: glow(layer, body, radius=6, alpha=0.5)

# ------------------------------------------------------------------ scenes
# Each draw(layer, t, dur): t seconds since scene start.  Content band: y 190..1120.  Captions at y ~1230.

def s_intro(layer, t, dur):
    d = ImageDraw.Draw(layer)
    fp = FP(140, 215, 800)
    draw_die(layer, fp, macs_frac=seg(t, 0.4, 2.6))
    d = ImageDraw.Draw(layer)
    a = seg(t, 3.0, 0.6)
    if a > 0:
        col = rgba(C_GREY, 255 * a)
        text(d, (540, 1052), '6.6 × 6.6 mm  ·  IHP SG13CMOS5L  ·  5 metal layers', 26, col, 'Medium', 'mm')
        text(d, (540, 1095), f'{len(MACS)} SRAM macros  ·  RISC-V + ztachip AI accelerator', 26, col, 'Medium', 'mm')

DONE_ITEMS = [('Detailed routing', '641 violations down to 0 in one night'),
              ('Power grid', 'VDD and VSS pass the grid check'),
              ('Seal ring, fill, corners', 'PDK + top-up fill; fill at the die corners cleaned'),
              ('Density', '0 violations on every layer'),
              ('IHP minimum DRC', '27 of 28 rule tables clean; Nwell still running'),
              ('Release candidate rc2', 'on GitHub main, with SHA-256 hashes'),
              ('Timing analysis', 'first full report of the routed chip: see next')]

def checklist(layer, t, items, y0=240, rh=118, t0=0.4, dt=0.5, status=('DONE', C_GREEN)):
    d = ImageDraw.Draw(layer)
    for i, (name, detail) in enumerate(items):
        a = seg(t, t0 + i * dt, 0.45)
        if a <= 0: continue
        y = y0 + i * rh; dx = (1 - a) * 60
        al = int(255 * a)
        rrect(d, (70 + dx, y, 1010 + dx, y + rh - 16), 18, fill=rgba((20, 26, 38), al), outline=rgba((40, 48, 64), al))
        cx, cy = 125 + dx, y + (rh - 16) / 2
        st, sc = status
        d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=rgba(sc, al))
        d.line([(cx - 10, cy), (cx - 3, cy + 8), (cx + 11, cy - 8)], fill=rgba(BG, al), width=5)
        text(d, (175 + dx, cy - 18), name, 34, rgba(C_WHITE, al), 'Bold', 'lm')
        text(d, (175 + dx, cy + 22), detail, 24, rgba(C_GREY, al), 'Medium', 'lm')
        pw = font(20).getlength(st) + 34
        rrect(d, (985 + dx - pw, cy - 16, 985 + dx, cy + 16), 16, fill=rgba(sc, al * .18))
        text(d, (985 + dx - pw / 2, cy), st, 20, rgba(sc, al), 'Bold', 'mm')

def s_done(layer, t, dur): checklist(layer, t, DONE_ITEMS)

def s_stuck(layer, t, dur):
    d = ImageDraw.Draw(layer)
    mx0, my0, mx1, my1 = 150, 290, 930, 1000
    rrect(d, (mx0, my0, mx1, my1), 6, fill=rgba((18, 25, 37)), outline=rgba(C_TEAL, 200), width=3)
    text(d, (mx0 + 18, my0 + 16), 'RM_IHPSG13 SRAM macro', 24, C_TEAL, 'SemiBold')
    # Metal4 power stripes (horizontal inside the macro), revealed top to bottom
    n = 7; a = seg(t, 0.2, 1.0)
    ys = [my0 + 150 + i * 80 for i in range(n)]
    for i, yy in enumerate(ys):
        if (i + 1) / n > a + 1e-6: break
        col = C_AMBER if i % 2 == 0 else (120, 140, 170)
        d.rectangle((mx0 + 30, yy - 10, mx1 - 30, yy + 10), fill=rgba(col, 170))
        text(d, (mx1 - 40, yy - 24), 'VDD' if i % 2 == 0 else 'VSS', 18, rgba(col, 220), 'SemiBold', 'rm')
    if a >= 1:
        text(d, (540, my1 - 28), 'Metal4 power stripes of the macro', 22, C_GREY, 'Medium', 'mm')
    # vertical signal wire coming down through the macro
    b = seg(t, 1.5, 1.6); y_end = lerp(200, 1030, b)
    if b > 0:
        def wire(dd): dd.line([(590, 200), (590, y_end)], fill=rgba((110, 220, 255)), width=6)
        glow(layer, wire, radius=12, alpha=.9)
        d = ImageDraw.Draw(layer)
        for yy in ys:
            if y_end > yy + 10:
                c = seg(t, 1.5 + (yy - 200) / (830 / 1.6), 0.25); r = 15 * c
                d.line([(590 - r, yy - r), (590 + r, yy + r)], fill=rgba(C_RED), width=5)
                d.line([(590 - r, yy + r), (590 + r, yy - r)], fill=rgba(C_RED), width=5)
    if t > 3.4:
        a2 = seg(t, 3.4, 0.5)
        rrect(d, (640, 318, 905, 410), 14, fill=rgba((40, 20, 24), 230 * a2), outline=rgba(C_RED, 200 * a2), width=2)
        text(d, (772, 348), 'Metal4 short', 26, rgba(C_RED, 255 * a2), 'Bold', 'mm')
        text(d, (772, 386), 'signal × power stripe', 20, rgba(C_GREY, 255 * a2), 'Medium', 'mm')
        text(d, (540, 1090), '~1,000 violations after routing · ~860 of them are this', 24, rgba(C_GREY, 255 * a2), 'Medium', 'mm')

def s_layers(layer, t, dur):
    d = ImageDraw.Draw(layer)
    names = ['Metal1', 'Metal2', 'Metal3', 'Metal4', 'TopMetal1']
    cols = [(90, 110, 150), (90, 110, 150), (90, 110, 150), (90, 110, 150), C_TEAL]
    x0, x1 = 120, 760; yb = 980; lh = 92; gap = 36
    for i, nm in enumerate(names):
        a = seg(t, 0.2 + i * 0.3, 0.4)
        if a <= 0: continue
        y1 = yb - i * (lh + gap); y0 = y1 - lh
        al = int(255 * a)
        d.rectangle((x0, y0 + (1 - a) * 30, x1, y1 + (1 - a) * 30), fill=rgba(cols[i], 80 if i < 4 else 160), outline=rgba(cols[i], al))
        text(d, (x1 + 24, (y0 + y1) / 2), nm, 28, rgba(C_WHITE, al), 'SemiBold', 'lm')
    b = seg(t, 1.9, 0.5)
    if b > 0:
        bx0, bx1 = 300, 580; by0 = yb - 3 * (lh + gap) - lh; by1 = yb
        hatch(layer, (bx0, by0, bx1, by1), rgba((200, 120, 120), 170 * b))
        d = ImageDraw.Draw(layer)
        d.rectangle((bx0, by0, bx1, by1), outline=rgba(C_RED, 220 * b), width=3)
        text(d, (x0, by1 + 30), 'SRAM macro: Metal1–4 taken', 24, rgba(C_RED, 255 * b), 'SemiBold', 'lm')
    c = seg(t, 2.6, 0.5)
    if c > 0:
        ty1 = yb - 4 * (lh + gap); ty0 = ty1 - lh; ym = (ty0 + ty1) / 2
        for k in range(3):
            xx = x0 + 60 + k * 200; L = 150 * c
            d.line([(xx, ym), (xx + L, ym)], fill=rgba(C_WHITE, 220), width=4)
            d.polygon([(xx + L, ym - 9), (xx + L + 14, ym), (xx + L, ym + 9)], fill=rgba(C_WHITE, 220))
        text(d, (x0, ty0 - 24), 'TopMetal1: horizontal only', 24, rgba(C_TEAL, 255 * c), 'SemiBold', 'lm')
    e = seg(t, 3.4, 0.8)
    if e > 0:
        xx = 500; ys = yb - 5 * (lh + gap) + 10; ye = lerp(ys, yb + 40, e)
        yy = ys
        while yy < ye:
            d.line([(xx, yy), (xx, min(yy + 16, ye))], fill=rgba(C_AMBER, 230), width=5); yy += 28
        if e >= 1:
            text(d, (xx + 52, 640), '✗', 44, C_RED, 'Bold', 'mm')
            text(d, (540, 1085), 'no legal north–south path over a macro', 26, C_GREY, 'Medium', 'mm')

def nearest_macro_above(px, py):
    best = None
    for m in MACS:
        if m[0] <= px <= m[2] and m[1] >= py:
            if best is None or m[1] < best[1]: best = m
    return best

def pocket_examples():
    out = []
    for i in [20, 44, 73, 98, 118, 133]:
        if i >= len(POCKETS): continue
        p = POCKETS[i]; cx, cy = (p[0] + p[2]) / 2, (p[1] + p[3]) / 2
        m = nearest_macro_above(cx, cy)
        if m: out.append((cx, cy, m))
    return out
EXAMPLES = pocket_examples()

def s_pockets(layer, t, dur):
    fp = FP(140, 205, 800)
    draw_die(layer, fp, dim=True)
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.3, 1.2)
    for i, p in enumerate(POCKETS):
        if i / len(POCKETS) > a: break
        d.rectangle(fp.box(p), fill=rgba(C_AMBER, 150))
    b = seg(t, 1.8, 1.4)
    if b > 0:
        def wires(dd):
            for k, (cx, cy, m) in enumerate(EXAMPLES):
                if k / len(EXAMPLES) > b: break
                x, y = fp.px(cx, cy); _, ytop = fp.px(cx, m[3] + 250)
                dd.ellipse((x - 5, y - 5, x + 5, y + 5), fill=rgba(C_WHITE))
                dd.line([(x, y), (x, ytop)], fill=rgba((255, 120, 120)), width=4)
        glow(layer, wires, radius=8, alpha=.8)
        d = ImageDraw.Draw(layer)
    c = seg(t, 3.2, 0.5)
    if c > 0:
        rrect(d, (120, 1030, 960, 1105), 16, fill=rgba((24, 30, 42), 230 * c), outline=rgba(C_AMBER, 160 * c))
        text(d, (540, 1067), '98 of 112 crossing nets start in a dead space (orange)', 24, rgba(C_WHITE, 255 * c), 'SemiBold', 'mm')

def bar(d, x, y, w, hmax, val, vmax, col, label, num, a, num_size=30):
    if a <= 0: return
    h = hmax * (val / vmax) * a
    d.rectangle((x, y - h, x + w, y), fill=rgba(col, 220))
    text(d, (x + w / 2, y - h - 22), num if a > 0.95 else f'{int(val * a):,}', num_size, C_WHITE, 'Bold', 'mm')
    text(d, (x + w / 2, y + 22), label, 22, C_GREY, 'Medium', 'mm')

def s_h13(layer, t, dur):
    fp = FP(240, 200, 600)
    draw_die(layer, fp, dim=True)
    a = seg(t, 0.2, 1.2)
    for i, p in enumerate(BLKS):
        if i / len(BLKS) > a: break
        hatch(layer, fp.box(p), rgba((150, 170, 200), 200), step=8, width=1)
    d = ImageDraw.Draw(layer)
    text(d, (540, 828), '146 placement blockages on the dead spaces', 24, C_GREY, 'Medium', 'mm')
    b = seg(t, 1.8, 1.0)
    if b > 0:
        d.line([(140, 1070), (940, 1070)], fill=rgba(C_DIM), width=2)
        bar(d, 200, 1070, 120, 160, 9522, 9522, (120, 130, 150), 'H12 overflow', '9,522', b)
        bar(d, 420, 1070, 120, 160, 3061, 9522, C_TEAL, 'H13 overflow', '3,061', seg(t, 2.3, 1.0))
        c = seg(t, 3.4, 0.6)
        if c > 0:
            rrect(d, (620, 905, 960, 1040), 16, fill=rgba((40, 26, 20), 230 * c), outline=rgba(C_AMBER, 180 * c))
            text(d, (790, 945), 'but a floor stays', 24, rgba(C_AMBER, 255 * c), 'Bold', 'mm')
            text(d, (790, 985), '≈ 800 shorts inside macros', 22, rgba(C_WHITE, 255 * c), 'Medium', 'mm')
            text(d, (790, 1015), 'fresh routes refill the rows', 20, rgba(C_GREY, 255 * c), 'Medium', 'mm')

def s_eco(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for k in range(3):
        x0 = 90 + k * 310
        d.rectangle((x0, 560, x0 + 290, 780), fill=rgba((18, 25, 37)), outline=rgba(C_TEAL, 170), width=2)
        d.rectangle((x0 + 10, 764, x0 + 280, 772), fill=rgba(C_TEAL, 120))     # pin edge (south)
    text(d, (540, 805), 'macro row · pins on the south edge', 22, C_GREY, 'Medium', 'mm')
    for yy in [300, 350, 400, 940, 990]:
        d.line([(120, yy), (960, yy)], fill=rgba((40, 48, 64)), width=3)
    text(d, (960, 270), 'other nets: frozen', 20, C_DIM, 'Medium', 'rm')
    north = [(300, 460), (380, 470), (470, 455), (600, 465), (690, 458)]
    move = seg(t, 2.4, 1.4)
    sx, sy0 = 520, 880; sy = lerp(sy0, 520, move)
    steiner = (520, 470)
    def wires(dd):
        for c in north: dd.line([c, (c[0], 470), steiner], fill=rgba((110, 220, 255)), width=4)
        dd.line([steiner, (sx, sy)], fill=rgba(mix(C_RED, C_GREEN, move)), width=5)
    glow(layer, wires, radius=8, alpha=.7)
    d = ImageDraw.Draw(layer)
    for c in north: d.rectangle((c[0] - 16, c[1] - 14, c[0] + 16, c[1] + 14), fill=rgba((200, 210, 230)))
    d.rectangle((sx - 16, sy - 14, sx + 16, sy + 14), fill=rgba(mix(C_RED, C_GREEN, move)))
    if move <= 0 and t > 1.0:
        a = seg(t, 1.0, 0.4)
        text(d, (sx + 30, sy), 'minority side: 1 cell', 22, rgba(C_RED, 255 * a), 'SemiBold', 'lm')
        text(d, (560, 670), 'crossing: short', 22, rgba(C_RED, 255 * a), 'SemiBold', 'lm')
    if move > 0:
        text(d, (sx + 30, sy), 'moved across the row', 22, rgba(C_GREEN, 255 * move), 'SemiBold', 'lm')
    if move >= 1:
        a = seg(t, 3.9, 0.5)
        text(d, (540, 1075), 'then: incremental global route + detailed route of the touched nets only', 21, rgba(C_GREY, 255 * a), 'Medium', 'mm')

def s_progress(layer, t, dur):
    d = ImageDraw.Draw(layer)
    text(d, (540, 250), 'router violations, night of 9 to 10 November', 26, C_TEAL, 'SemiBold', 'mm')
    d.line([(110, 700), (970, 700)], fill=rgba(C_DIM), width=2)
    vals = [('start', 641, C_RED), ('detour', 347, C_AMBER), ('lift + detour', 174, C_AMBER), ('24 passes', 11, C_TEAL), ('again', 0, C_GREEN)]
    for i, (lab, v, c) in enumerate(vals):
        bar(d, 150 + i * 165, 700, 110, 360, v, 700, c, lab, f'{v}', seg(t, 0.4 + i * 0.6, 0.7), 34)
    a = seg(t, 3.6, 0.5)
    if a > 0:
        rrect(d, (90, 790, 990, 1010), 18, fill=rgba((20, 26, 38), 230 * a), outline=rgba((40, 48, 64), 255 * a))
        text(d, (540, 830), 'most shorted nets only pass through a congested spot', 23, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 872), 'detour: route them around it, with every spot closed to every detour', 22, rgba(C_AMBER, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 914), 'lift: one 64x16 SRAM macro moved 63 um, power grid repaired under it', 22, rgba(C_AMBER, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 956), 'the late, high-cost repair passes clear the rest: 128 to 11, then to 0', 22, rgba(C_GREEN, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 992), 'the independent DRC on that database: 0 violations', 20, rgba(C_DIM, 255 * a), 'Medium', 'mm')

NOW = [('1', 'SRAM clock arrives 4.6 ns after the flip-flop clock', 'the time-multiplexed SRAMs need aligned edges; 10,324 SRAM pins fail hold', C_RED),
       ('2', 'the fix: put the three clocks in order', 'SRAM first, then phase and core flip-flops; repeaters on the 10 mm clock root', C_TEAL),
       ('3', 'tonight: hold buffers, re-route, repeat the checks', 'about 7,600 buffers at the fast corner; 24 repair passes', C_GREEN)]

def s_now(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (n, k, v, col) in enumerate(NOW):
        a = seg(t, 0.4 + i * 0.9, 0.5)
        if a <= 0: continue
        y = 250 + i * 190
        rrect(d, (70, y, 1010, y + 160), 20, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 220 * a), width=2)
        d.ellipse((96, y + 52, 152, y + 108), fill=rgba(col, 255 * a))
        text(d, (124, y + 80), n, 30, rgba(BG, 255 * a), 'Bold', 'mm')
        text(d, (180, y + 58), k, 26, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
        text(d, (180, y + 104), v, 20, rgba(C_GREY, 255 * a), 'Medium', 'lm')
    b = seg(t, 3.4, 0.6)
    if b > 0:
        rrect(d, (90, 850, 990, 1010), 18, fill=rgba((20, 26, 38), 230 * b), outline=rgba((40, 48, 64), 255 * b))
        text(d, (540, 895), 'a hold failure does not go away at a lower clock: it has to be fixed', 22, rgba(C_WHITE, 255 * b), 'SemiBold', 'mm')
        text(d, (540, 940), 'with the fix in analysis: SRAM hold failures 10,324 to 0, at all three corners', 22, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        text(d, (540, 980), 'speed after the fix: about 35 MHz core typical, 22 MHz worst case', 20, rgba(C_DIM, 255 * b), 'Medium', 'mm')

NEXT_ITEMS = [('Timing fix', 'clock order, root repeaters, hold buffers; routing tonight', 'RUNNING', C_BLUE),
              ('Antenna repair', '11,513 diodes on 6,105 nets; repair pass 14 of 24', 'RUNNING', C_BLUE),
              ('IHP minimum DRC', '27 of 28 clean on rc2; repeated on the final file', 'REPEAT', C_PURPLE),
              ('LVS vs the released CDL', 'devices extracted; netlist comparison running', 'RUNNING', C_BLUE),
              ('Dry run at IHP', 'requested on release candidate rc2', 'ASKED', C_AMBER),
              ('Final release v.2.0.0', 'GDS, hashes, DRC result files, issue #79', 'PENDING', C_GREY)]

def s_next(layer, t, dur):
    d = ImageDraw.Draw(layer)
    y0, rh = 235, 128
    for i, (name, detail, st, col) in enumerate(NEXT_ITEMS):
        a = seg(t, 0.3 + i * 0.5, 0.45)
        if a <= 0: continue
        y = y0 + i * rh; al = int(255 * a)
        if i > 0:
            d.line([(130, y - 24), (130, y + 2)], fill=rgba(C_DIM, al), width=3)
            d.polygon([(122, y - 2), (138, y - 2), (130, y + 8)], fill=rgba(C_DIM, al))
        rrect(d, (70, y + 8, 1010, y + rh - 20), 18, fill=rgba((20, 26, 38), al), outline=rgba(col if st != 'PENDING' else (40, 48, 64), al))
        cy = y + 8 + (rh - 28) / 2
        d.ellipse((108, cy - 20, 148, cy + 20), fill=rgba(col, al))
        if st == 'RUNNING':
            ang = (t * 240) % 360
            d.pieslice((112, cy - 16, 144, cy + 16), ang, ang + 90, fill=rgba(BG, al))
        text(d, (180, cy - 18), name, 32, rgba(C_WHITE, al), 'Bold', 'lm')
        text(d, (180, cy + 20), detail, 23, rgba(C_GREY, al), 'Medium', 'lm')
        pw = font(19).getlength(st) + 32
        rrect(d, (985 - pw, cy - 15, 985, cy + 15), 15, fill=rgba(col, al * .2))
        text(d, (985 - pw / 2, cy), st, 19, rgba(col, al), 'Bold', 'mm')

def s_dates(layer, t, dur):
    d = ImageDraw.Draw(layer)
    y = 560; x0, x1 = 120, 960
    a = seg(t, 0.2, 0.8)
    d.line([(x0, y), (lerp(x0, x1, a), y)], fill=rgba((60, 70, 90)), width=4)
    pts = [(170, '9 Nov', 'open run', 'not used', (120, 130, 150), 0.6),
           (400, '13 Nov', 'checked GDS', 'target', C_TEAL, 0.9),
           (620, '15 Nov', '23:59 CET', 'requested', C_AMBER, 1.2),
           (880, '14 Mar 2027', 'next MPW run', 'fallback', (120, 130, 150), 1.8)]
    for x, dt, lab, st, col, t0 in pts:
        b = seg(t, t0, 0.5)
        if b <= 0: continue
        r = 16 * b
        if st == 'requested':
            pr = 16 + 14 * (0.5 + 0.5 * math.sin(t * 3))
            d.ellipse((x - pr, y - pr, x + pr, y + pr), outline=rgba(col, 120), width=3)
        d.ellipse((x - r, y - r, x + r, y + r), fill=rgba(col, 255 * b))
        if st == 'missed':
            d.line([(x - 8, y - 8), (x + 8, y + 8)], fill=rgba(BG), width=4); d.line([(x - 8, y + 8), (x + 8, y - 8)], fill=rgba(BG), width=4)
        text(d, (x, y - 60), dt, 34, rgba(C_WHITE, 255 * b), 'Bold', 'mm')
        text(d, (x, y + 50), lab, 22, rgba(C_GREY, 255 * b), 'Medium', 'mm')
        text(d, (x, y + 84), 'hard deadline' if st == 'requested' else st, 22, rgba(col, 255 * b), 'SemiBold', 'mm')
    c = seg(t, 0.9, 0.4)
    if c > 0:
        d.line([(230, y - 20), (230, y + 20)], fill=rgba(C_WHITE, 200 * c), width=3)
        text(d, (230, y - 120), 'today · 10 Nov', 20, rgba(C_WHITE, 220 * c), 'Medium', 'mm')
    e = seg(t, 2.6, 0.6)
    if e > 0:
        rrect(d, (120, 790, 960, 1010), 20, fill=rgba((20, 26, 38), 230 * e), outline=rgba((40, 48, 64), 255 * e))
        text(d, (540, 840), 'rc2 on GitHub: routing clean, density clean, DRC 27 of 28 tables', 24, rgba(C_WHITE, 255 * e), 'SemiBold', 'mm')
        text(d, (540, 895), 'no run on 20 November: 15 November is the last date, one attempt', 23, rgba(C_GREY, 255 * e), 'Medium', 'mm')
        text(d, (540, 940), 'the final GDS is a re-run of the scripted chain on the fixed database', 23, rgba(C_GREY, 255 * e), 'Medium', 'mm')
        text(d, (540, 985), 'chip_finish → stream → seal ring → fill → DRC → LVS → release', 20, rgba(C_TEAL, 255 * e), 'Medium', 'mm')

def s_end(layer, t, dur):
    fp = FP(340, 420, 400); draw_die(layer, fp, dim=True)
    d = ImageDraw.Draw(layer)
    text(d, (540, 900), 'SoC2611', 40, C_WHITE, 'Bold', 'mm')
    text(d, (540, 955), 'status · 10 November 2026', 24, C_GREY, 'Medium', 'mm')

SCENES = [
    ('SoC2611: status, 10 November', s_intro,
     'This is {S o C twenty six eleven|SoC2611}: a RISC-V chip with an AI accelerator, built for IHP\'s one hundred and thirty '
     'nanometre process. Six point six millimetres a side, with two hundred and ninety-eight SRAM macros. Here is where it '
     'stands on the tenth of November.'),
    ('How the routing closed', s_progress,
     'Last night the routing closed. Six hundred and forty-one violations at the start. Most of the shorted nets only passed '
     'through a congested spot, so we routed them around it: three hundred and forty-seven. One SRAM macro was moved by '
     'sixty-three micrometres and the same detour applied: one hundred and seventy-four. Then the late repair passes '
     'took it to eleven, and a second run to zero.'),
    ('What is done', s_done,
     'So the list of finished items is long. Routing is clean. The power grid passes. Seal ring and fill are in, and density '
     'is clean. The IHP minimum DRC is clean on twenty-seven of twenty-eight rule tables, with the last one still running. '
     'That state is on GitHub as release candidate two.'),
    ('What the timing check found', s_now,
     'Then we ran the first full timing report of the routed chip, and it found a real problem. The single-port memories do '
     'two accesses per cycle, and for that their clock must line up with the flip-flop clock. It does not: the memory clock '
     'arrives four point six nanoseconds late, and ten thousand memory pins fail hold. A hold failure does not go away at a '
     'lower clock. The fix is to put the three clocks in order, the memory first, and to add repeaters on the clock root. '
     'In analysis that brings the memory failures to zero at all three corners. The price is speed: about thirty-five '
     'megahertz, where fifty was the target.'),
    ('What comes next', s_next,
     'Tonight the timing fix is routed, and the antenna repair runs beside it. Then the checks are repeated on the final '
     'file: the DRC deck, LVS against the released netlist, and the dry run we asked IHP for. Last comes the tagged '
     'release with hashes.'),
    ('The dates', s_dates,
     'There is no run on the twentieth. IHP will wait until the fifteenth of November, with one attempt and no time to '
     'iterate. Our target for the checked file is the thirteenth. Every step is scripted, so the final GDS is a re-run '
     'on the fixed database, not a rebuild.'),
    ('', s_end, ''),
]

# ------------------------------------------------------------------ narration
TOK = re.compile(r'\{([^|}]+)\|([^}]+)\}|(\S+)')
def parse_narration(s):
    toks = []
    for m in TOK.finditer(s):
        if m.group(3): toks.append(([m.group(3)], m.group(3)))
        else: toks.append((m.group(1).split(), m.group(2)))
    return toks
def spoken_text(toks): return ' '.join(w for t in toks for w in t[0])
def norm(w): return re.sub(r'[^a-z0-9]', '', w.lower())

async def _tts(text_, voice, rate, mp3):
    import edge_tts
    c = edge_tts.Communicate(text_, voice, rate=rate, boundary='WordBoundary')
    words = []
    with open(mp3, 'wb') as f:
        async for ch in c.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] == 'WordBoundary': words.append((ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']))
    return words

def tts(text_, voice, rate, cache):
    h = hashlib.sha1(f'{voice}|{rate}|{text_}'.encode()).hexdigest()[:16]
    mp3, js = os.path.join(cache, h + '.mp3'), os.path.join(cache, h + '.json')
    if not (os.path.exists(mp3) and os.path.exists(js)):
        words = asyncio.run(_tts(text_, voice, rate, mp3)); json.dump(words, open(js, 'w'))
    return mp3, json.load(open(js))

def audio_len(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]).strip())

def align(toks, words):
    """give each display token a (start, end) from the TTS word boundaries."""
    spoken = [w for t in toks for w in t[0]]
    a = [norm(w) for w in spoken]; b = [norm(w[2]) for w in words]
    tmap = [None] * len(spoken)
    for i, j, n in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(n): tmap[i + k] = (words[j + k][0], words[j + k][1])
    for i in range(len(tmap)):
        if tmap[i] is None:
            prev = next((tmap[k][1] for k in range(i - 1, -1, -1) if tmap[k]), 0.0)
            nxt = next((tmap[k][0] for k in range(i + 1, len(tmap)) if tmap[k]), prev + 0.3)
            tmap[i] = (prev, nxt)
    out, i = [], 0
    for sp, disp in toks:
        seg_ = tmap[i:i + len(sp)]; i += len(sp)
        out.append((seg_[0][0], seg_[-1][1], disp))
    return out

def phrases(timed, max_chars=34, max_words=6):
    """group timed display tokens into caption phrases; break at punctuation / length."""
    out, cur = [], []
    for st, en, disp in timed:
        cur.append((st, en, disp))
        chars = sum(len(x[2]) + 1 for x in cur)
        if disp[-1] in '.,:;?!' or chars >= max_chars or len(cur) >= max_words:
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out

# ------------------------------------------------------------------ frame drawing
def draw_caption(img, phrase, t):
    words = [p[2] for p in phrase]
    size = 46
    while True:
        f = font(size); gapw = f.getlength(' ')
        widths = [f.getlength(w) for w in words]
        total = sum(widths) + gapw * (len(words) - 1)
        if total <= 960 or size <= 30: break
        size -= 2
    pad = 34; ph = size + 54
    x0 = (W - total) / 2 - pad; y0 = 1230 - ph / 2
    d = ImageDraw.Draw(img, 'RGBA')
    d.rounded_rectangle((x0, y0, x0 + total + 2 * pad, y0 + ph), radius=22, fill=rgba(C_PILL, 235))
    x = x0 + pad
    for (st, en, w), wd in zip(phrase, widths):
        if t >= en: col = C_WHITE
        elif t >= st - 0.02: col = C_AMBER
        else: col = C_GREY
        d.text((x, 1230), w, font=f, fill=col, anchor='lm'); x += wd + gapw

def render_frame(scene, t, dur, caps):
    img = Image.new('RGB', (W, H), BG)
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    title, fn, _ = scene
    if title:
        text(ImageDraw.Draw(layer), (W / 2, 105), title, 58, C_WHITE, 'Bold', 'mm')
    fn(layer, t, dur)
    fade = min(1.0, t / 0.35, max(0.0, (dur - t) / 0.3))
    if fade < 1:
        layer.putalpha(layer.split()[3].point(lambda v: int(v * fade)))
    img.paste(layer, (0, 0), layer)
    cur = None
    for ph in caps:
        if t >= ph[0][0] - 0.15: cur = ph
    if cur is not None and t < caps[-1][-1][1] + 1.2:
        draw_caption(img, cur, t)
    return img

def render_scene(args):
    idx, scene, dur, caps, fps, out = args
    n = int(round(dur * fps))
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', out],
                         stdin=subprocess.PIPE)
    for k in range(n):
        p.stdin.write(render_frame(scene, k / fps, dur, caps).tobytes())
    p.stdin.close(); p.wait()
    return idx, n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out_dir'); ap.add_argument('--fps', type=int, default=30); ap.add_argument('--voice', default='en-GB-RyanNeural')
    ap.add_argument('--rate', default='-4%'); ap.add_argument('--preview', action='store_true'); ap.add_argument('--jobs', type=int, default=12)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True); cache = os.path.join(a.out_dir, 'tts'); os.makedirs(cache, exist_ok=True)
    plan = []
    for sc in SCENES:
        title, fn, narr = sc
        if narr:
            toks = parse_narration(narr)
            mp3, words = tts(spoken_text(toks), a.voice, a.rate, cache)
            alen = audio_len(mp3); caps = phrases(align(toks, words))
            dur = max(alen + 0.9, 5.0)
        else:
            mp3, alen, caps, dur = None, 0.0, [], 3.0
        plan.append((sc, dur, caps, mp3, alen))
    total = sum(p[1] for p in plan)
    print(f'{len(plan)} scenes, {total:.1f} s', flush=True)
    if a.preview:
        for i, (sc, dur, caps, mp3, alen) in enumerate(plan):
            render_frame(sc, dur * 0.55, dur, caps).save(os.path.join(a.out_dir, f'preview_{i:02d}.png'))
        return
    sr = 48000; track = []
    for sc, dur, caps, mp3, alen in plan:
        n = int(round(dur * sr)); buf = np.zeros((n, 2), dtype=np.int16)
        if mp3:
            wavp = mp3[:-4] + '.wav'
            subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-i', mp3, '-ar', str(sr), '-ac', '2', wavp])
            with wave.open(wavp) as wf: data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).reshape(-1, 2)
            m = min(len(data), n); buf[:m] = data[:m]
        track.append(buf)
    track = np.concatenate(track)
    wav_out = os.path.join(a.out_dir, 'narration.wav')
    with wave.open(wav_out, 'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(track.tobytes())
    jobs = [(i, sc, dur, caps, a.fps, os.path.join(a.out_dir, f'scene_{i:02d}.mp4')) for i, (sc, dur, caps, mp3, alen) in enumerate(plan)]
    with Pool(min(a.jobs, len(jobs))) as pool:
        for idx, n in pool.imap_unordered(render_scene, jobs): print(f'scene {idx} done ({n} frames)', flush=True)
    lst = os.path.join(a.out_dir, 'concat.txt')
    with open(lst, 'w') as f:
        for j in jobs: f.write(f"file '{j[5]}'\n")
    final = os.path.join(a.out_dir, 'SoC2611_status.mp4')
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', wav_out, '-c:v', 'copy',
                           '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', final])
    print('wrote', final)

if __name__ == '__main__':
    main()
