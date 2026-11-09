#!/usr/bin/env python3
"""Second explainer: would SoC2611 work with the residual shorts inside the SRAMs, why those nets resisted the ECO
rounds, and what round H does.  Reuses make_status_video.py (same look, same voice, same renderer).
usage: make_shorts_video.py <out_dir> [--preview] [--h-status 'text'] [--h-inside N] [--h-both N]"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_status_video as V
from PIL import ImageDraw

C_WHITE, C_GREY, C_DIM, C_AMBER, C_TEAL, C_BLUE, C_GREEN, C_RED, C_PURPLE = (
    V.C_WHITE, V.C_GREY, V.C_DIM, V.C_AMBER, V.C_TEAL, V.C_BLUE, V.C_GREEN, V.C_RED, V.C_PURPLE)
text, rrect, hatch, glow, seg, lerp, mix, rgba = V.text, V.rrect, V.hatch, V.glow, V.seg, V.lerp, V.mix, V.rgba

H_STATUS = os.environ.get('H_STATUS', 'running, result about 10:40 IST')
H_INSIDE = os.environ.get('H_INSIDE', '?'); H_BOTH = os.environ.get('H_BOTH', '?')

def card(d, box, big, small, col, a):
    rrect(d, box, 20, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 200 * a), width=2)
    cx = (box[0] + box[2]) / 2
    text(d, (cx, box[1] + 62), big, 54, rgba(col, 255 * a), 'Bold', 'mm')
    text(d, (cx, box[1] + 122), small, 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')

def s_counts(layer, t, dur):
    d = ImageDraw.Draw(layer)
    items = [('44', 'signal nets still crossing an SRAM', C_TEAL), ('95', 'Metal4 shorts to VDD / VSS stripes', C_AMBER),
             ('9', 'macros affected', C_TEAL), ('8', 'nets touching VDD and VSS both', C_RED)]
    for i, (big, small, col) in enumerate(items):
        a = seg(t, 0.4 + i * 0.5, 0.5)
        if a <= 0: continue
        r, c = divmod(i, 2)
        x0 = 70 + c * 480; y0 = 260 + r * 230
        card(d, (x0, y0, x0 + 460, y0 + 170), big, small, col, a)
    a = seg(t, 3.0, 0.6)
    if a > 0:
        text(d, (540, 800), 'state after ECO round G, 9 November, 08:07 IST', 24, rgba(C_GREY, 255 * a), 'Medium', 'mm')
        text(d, (540, 900), 'Would a chip like this work?', 40, rgba(C_WHITE, 255 * a), 'Bold', 'mm')

def stripes(d, mx0, my0, mx1, my1, n=7, start=90, step=80):
    ys = [my0 + start + i * step for i in range(n)]
    for i, yy in enumerate(ys):
        col = C_AMBER if i % 2 == 0 else (120, 140, 170)
        d.rectangle((mx0 + 30, yy - 9, mx1 - 30, yy + 9), fill=rgba(col, 170))
        text(d, (mx1 - 40, yy - 22), 'VDD' if i % 2 == 0 else 'VSS', 17, rgba(col, 220), 'SemiBold', 'rm')
    return ys

def s_kinds(layer, t, dur):
    d = ImageDraw.Draw(layer)
    mx0, my0, mx1, my1 = 120, 260, 960, 980
    rrect(d, (mx0, my0, mx1, my1), 6, fill=rgba((18, 25, 37)), outline=rgba(C_TEAL, 200), width=3)
    text(d, (mx0 + 18, my1 - 40), 'SRAM macro, Metal4 power stripes', 22, C_TEAL, 'SemiBold')
    ys = stripes(d, mx0, my0, mx1, my1)
    # wire A: touches one stripe only (ends between stripes)
    a = seg(t, 0.8, 1.0)
    if a > 0:
        ya = lerp(200, ys[0] + 30, a)
        def wa(dd): dd.line([(330, 200), (330, ya)], fill=rgba((110, 220, 255)), width=6)
        glow(layer, wa, radius=10, alpha=.8); d = ImageDraw.Draw(layer)
        if a >= 1:
            d.line([(316, ys[0] - 14), (344, ys[0] + 14)], fill=rgba(C_RED), width=5); d.line([(316, ys[0] + 14), (344, ys[0] - 14)], fill=rgba(C_RED), width=5)
            text(d, (330, my0 + 48), 'one stripe: stuck at 1,', 21, C_AMBER, 'Bold', 'mm')
            text(d, (330, my0 + 72), 'driver fights the rail', 19, C_GREY, 'Medium', 'mm')
    # wire B: crosses VDD and VSS
    b = seg(t, 2.6, 1.2)
    if b > 0:
        yb = lerp(200, ys[2] + 30, b)
        def wb(dd): dd.line([(720, 200), (720, yb)], fill=rgba((110, 220, 255)), width=6)
        glow(layer, wb, radius=10, alpha=.8); d = ImageDraw.Draw(layer)
        for yy in ys[:3]:
            if yb > yy + 10:
                d.line([(706, yy - 14), (734, yy + 14)], fill=rgba(C_RED), width=5); d.line([(706, yy + 14), (734, yy - 14)], fill=rgba(C_RED), width=5)
        if b >= 1:
            # current path VDD -> wire -> VSS
            ph = (t * 2) % 1.0
            for k in range(6):
                yy = lerp(ys[0], ys[1], (k / 6 + ph) % 1.0)
                d.ellipse((720 - 5, yy - 5, 720 + 5, yy + 5), fill=rgba(C_RED))
            text(d, (720, my0 + 48), 'VDD and VSS both:', 21, C_RED, 'Bold', 'mm')
            text(d, (720, my0 + 72), 'direct supply short', 19, C_GREY, 'Medium', 'mm')
    if t > 4.2:
        c = seg(t, 4.2, 0.5)
        text(d, (540, 1060), '36 nets of the first kind, 8 of the second', 26, rgba(C_WHITE, 255 * c), 'SemiBold', 'mm')

def s_arith(layer, t, dur):
    d = ImageDraw.Draw(layer)
    rows = [('wire', 'thin Metal4, a few hundred µm', '10 – 50 Ω', C_TEAL),
            ('per net', 'at 1.2 V core supply', '25 – 100 mA', C_AMBER),
            ('8 nets', 'before anything switches', '0.2 – 0.8 A', C_RED)]
    for i, (k, s, v, col) in enumerate(rows):
        a = seg(t, 0.4 + i * 0.9, 0.5)
        if a <= 0: continue
        y = 270 + i * 150
        rrect(d, (70, y, 1010, y + 120), 18, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 180 * a), width=2)
        text(d, (100, y + 42), k, 30, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
        text(d, (100, y + 84), s, 22, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        text(d, (980, y + 60), v, 40, rgba(col, 255 * a), 'Bold', 'rm')
    b = seg(t, 3.4, 0.8)
    if b > 0:
        # bar: shorts current vs what the core draws at reset
        d.line([(120, 1000), (960, 1000)], fill=rgba(C_DIM), width=2)
        w1 = 840 * 0.15 * b; w2 = 840 * min(1.0, 0.8) * b
        d.rectangle((120, 900, 120 + w1, 940), fill=rgba(C_TEAL, 220)); text(d, (130 + w1, 920), 'core at reset, ~0.1 A', 20, C_TEAL, 'Medium', 'lm')
        d.rectangle((120, 950, 120 + w2, 990), fill=rgba(C_RED, 220)); text(d, (540, 970), 'the 8 shorts, up to 0.8 A', 20, C_WHITE, 'Bold', 'mm')
        text(d, (540, 760), 'the shorts draw more than the whole core', 24, rgba(C_WHITE, 255 * b), 'SemiBold', 'mm')

def s_outcomes(layer, t, dur):
    d = ImageDraw.Draw(layer)
    items = [('Most likely', 'core rail never comes up: regulator or pads current-limit, nothing boots', C_RED),
             ('Possible', 'a shorted wire burns open like a fuse; uncontrolled, may take neighbours', C_AMBER),
             ('Best case', 'rail survives, CPU boots; 36 stuck nets kill the accelerator FIFOs and the AXI read path', C_GREY)]
    for i, (k, s, col) in enumerate(items):
        a = seg(t, 0.4 + i * 1.1, 0.5)
        if a <= 0: continue
        y = 250 + i * 230; dx = (1 - a) * 50
        rrect(d, (70 + dx, y, 1010 + dx, y + 190), 20, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 200 * a), width=2)
        text(d, (100 + dx, y + 48), k, 34, rgba(col, 255 * a), 'Bold', 'lm')
        # wrap the sentence into two lines
        words = s.split(); l1, l2 = ' '.join(words[:len(words) // 2 + 1]), ' '.join(words[len(words) // 2 + 1:])
        text(d, (100 + dx, y + 108), l1, 23, rgba(C_WHITE, 255 * a), 'Medium', 'lm')
        text(d, (100 + dx, y + 146), l2, 23, rgba(C_WHITE, 255 * a), 'Medium', 'lm')
    b = seg(t, 4.0, 0.6)
    if b > 0:
        text(d, (540, 980), 'stuck nets: dp_sink3 and dp_fetch FIFOs, AXI read command FIFO, camera write FIFO', 20, rgba(C_GREY, 255 * b), 'Medium', 'mm')

def s_verdict(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.3, 0.8)
    rrect(d, (90, 420, 990, 760), 28, fill=rgba((40, 20, 24), 240 * a), outline=rgba(C_RED, 220 * a), width=3)
    text(d, (540, 520), 'With these shorts:', 36, rgba(C_WHITE, 255 * a), 'Medium', 'mm')
    text(d, (540, 600), 'a dead chip', 64, rgba(C_RED, 255 * a), 'Bold', 'mm')
    text(d, (540, 680), 'not a partly working one', 30, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    b = seg(t, 2.0, 0.6)
    if b > 0:
        text(d, (540, 880), 'a tape-out in this state buys silicon that cannot be tested', 24, rgba(C_WHITE, 255 * b), 'SemiBold', 'mm')
        text(d, (540, 930), 'the fab charge is the same for a working one', 22, rgba(C_GREY, 255 * b), 'Medium', 'mm')

def macro_scene(layer, t, move):
    """macro with a south-edge pin, blocked pocket below, load buffer north; move in [0,1] slides the buffer into
    the pocket and reroutes"""
    d = ImageDraw.Draw(layer)
    mx0, my0, mx1, my1 = 140, 520, 940, 760
    # pocket below the macro
    pk = (mx0, my1 + 10, mx1, my1 + 130)
    blk_a = 1.0 - move
    if blk_a > 0:
        hatch(layer, pk, rgba((150, 170, 200), 150 * blk_a), step=10, width=1)
        d = ImageDraw.Draw(layer)
        d.rectangle(pk, outline=rgba((150, 170, 200), 180 * blk_a), width=2)
        text(d, (540, pk[1] + 60), 'pocket: placement blocked (H13)', 22, rgba((170, 185, 210), 255 * blk_a), 'SemiBold', 'mm')
    else:
        d.rectangle(pk, outline=rgba(C_GREEN, 120), width=2)
    d.rectangle((mx0, my0, mx1, my1), fill=rgba((18, 25, 37)), outline=rgba(C_TEAL, 200), width=3)
    text(d, (mx0 + 16, my0 + 12), 'SRAM macro (R0)', 22, C_TEAL, 'SemiBold')
    for i in range(5):
        col = C_AMBER if i % 2 == 0 else (120, 140, 170)
        yy = my0 + 55 + i * 40
        d.rectangle((mx0 + 30, yy - 6, mx1 - 30, yy + 6), fill=rgba(col, 150))
    # pin on the south edge
    px, py = 520, my1 - 6
    d.rectangle((px - 7, py - 7, px + 7, py + 7), fill=rgba(C_WHITE))
    text(d, (px - 16, py - 4), 'dout pin, south edge', 20, C_WHITE, 'SemiBold', 'rm')
    # buffer: north (y 400) -> pocket (y 820)
    bx, by = 560, lerp(400, my1 + 60, move)
    # wire
    def w(dd):
        if move < 1:
            dd.line([(px, py), (px, 400), (bx, 400)], fill=rgba(mix(C_RED, C_GREEN, move)), width=5)
        else:
            dd.line([(px, py), (px, by), (bx, by)], fill=rgba(C_GREEN), width=5)
    glow(layer, w, radius=8, alpha=.7); d = ImageDraw.Draw(layer)
    d.rectangle((bx - 18, by - 14, bx + 18, by + 14), fill=rgba(mix((200, 210, 230), C_GREEN, move)))
    text(d, (bx + 30, by), 'load buffer', 20, mix(C_GREY, C_GREEN, move), 'SemiBold', 'lm')
    if move <= 0:
        for yy in (my0 + 55, my0 + 135, my0 + 215):
            d.line([(px - 12, yy - 12), (px + 12, yy + 12)], fill=rgba(C_RED), width=4); d.line([(px - 12, yy + 12), (px + 12, yy - 12)], fill=rgba(C_RED), width=4)
        text(d, (px + 24, my0 + 30), 'forced through the macro', 20, C_RED, 'SemiBold', 'lm')

def s_why(layer, t, dur):
    macro_scene(layer, t, 0.0)
    d = ImageDraw.Draw(layer)
    a = seg(t, 3.0, 0.6)
    if a > 0:
        rrect(d, (90, 940, 990, 1090), 18, fill=rgba((20, 26, 38), 240 * a), outline=rgba((40, 48, 64), 255 * a))
        text(d, (540, 985), '30 of the 44 nets are exactly this: SRAM data pins', 24, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 1025), 'whose only load sits on the far side of the macro', 24, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 1062), 'the planner had taken the macro centre as the pin, so it never moved them', 20, rgba(C_GREY, 255 * a), 'Medium', 'mm')

def s_fix(layer, t, dur):
    macro_scene(layer, t, seg(t, 1.2, 1.6))
    d = ImageDraw.Draw(layer)
    a = seg(t, 3.2, 0.6)
    if a > 0:
        for i, (big, small) in enumerate([('35', 'cells moved into their pin pockets'), ('148', 'placement blockages lifted'),
                                          ('44', 'nets re-routed, obstructions kept'), ('20', 'passes')]):
            x0 = 70 + (i % 2) * 480; y0 = 900 + (i // 2) * 110
            rrect(d, (x0, y0, x0 + 460, y0 + 90), 16, fill=rgba((20, 26, 38), 240 * a), outline=rgba((40, 48, 64), 255 * a))
            text(d, (x0 + 24, y0 + 45), big, 36, rgba(C_GREEN, 255 * a), 'Bold', 'lm')
            text(d, (x0 + 120, y0 + 45), small, 21, rgba(C_WHITE, 255 * a), 'Medium', 'lm')

def s_stand(layer, t, dur):
    d = ImageDraw.Draw(layer)
    text(d, (300, 250), 'shorts inside the macros', 24, C_TEAL, 'SemiBold', 'mm')
    d.line([(80, 620), (560, 620)], fill=rgba(C_DIM), width=2)
    vals = [('round E', 105), ('round F', 90), ('round G', 95)]
    for i, (lab, v) in enumerate(vals):
        V.bar(d, 100 + i * 115, 620, 80, 300, v, 120, C_TEAL, lab, f'{v}', seg(t, 0.3 + i * 0.4, 0.7), 28)
    text(d, (820, 250), 'nets touching VDD and VSS', 24, C_RED, 'SemiBold', 'mm')
    d.line([(620, 620), (1000, 620)], fill=rgba(C_DIM), width=2)
    both = [('round E', 13), ('round F', 8), ('round G', 8)]
    for i, (lab, v) in enumerate(both):
        V.bar(d, 640 + i * 95, 620, 70, 300, v, 15, C_RED, lab, f'{v}', seg(t, 0.6 + i * 0.4, 0.7), 28)
    pa = 0.5 + 0.5 * math.sin(t * 4)
    if t > 2.0:
        for x, w, lab, val in ((100 + 3 * 115, 80, 'round H', H_INSIDE), (640 + 3 * 95, 70, 'round H', H_BOTH)):
            d.rectangle((x, 620 - 150, x + w, 620), outline=rgba(C_BLUE, 120 + 120 * pa), width=3)
            text(d, (x + w / 2, 642), lab, 22, C_BLUE, 'Medium', 'mm')
            text(d, (x + w / 2, 620 - 172), val, 26, C_BLUE, 'Bold', 'mm')
    a = seg(t, 3.0, 0.6)
    if a > 0:
        rrect(d, (90, 760, 990, 1000), 20, fill=rgba((20, 26, 38), 240 * a), outline=rgba((40, 48, 64), 255 * a))
        text(d, (540, 805), f'round H: {H_STATUS}', 24, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 855), 'the number to watch: nets touching both supplies', 23, rgba(C_RED, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 905), 'zero: GDS out by noon, decision on the rest', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')
        text(d, (540, 945), 'not zero: the honest answer to IHP is the 20th', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')

V.SCENES = [
    ('Would the chip work?', s_counts,
     'After round G, forty-four signal nets still cross an SRAM and short to its Metal four power stripes: ninety-five '
     'shorts in nine macros. The question is simple. Would a chip like that work? Let us go through it.'),
    ('Two kinds of short', s_kinds,
     'A wire that touches one stripe is tied to that supply. The signal is stuck at one or zero, and its driver fights '
     'the rail. A wire that touches both stripes is worse: it joins VDD to VSS through a thin Metal four line. That is a '
     'direct supply short. Thirty-six nets are of the first kind, eight of the second.'),
    ('The arithmetic', s_arith,
     'A thin Metal four wire a few hundred micrometres long is ten to fifty ohms. At one point two volts that is '
     'twenty-five to a hundred milliamps per net. Eight nets: a quarter to three quarters of an amp, before a single '
     'transistor switches. More than the whole core draws at reset.'),
    ('What happens at power-up', s_outcomes,
     'Most likely the core rail never comes up: the regulator or the pads current-limit, and nothing boots. Perhaps a '
     'wire burns open like a fuse, which is uncontrolled. In the best case the rail survives and the CPU boots, but the '
     'other thirty-six stuck nets kill the accelerator FIFOs and the AXI read path anyway.'),
    ('The verdict', s_verdict,
     'So with these shorts the chip is dead, not partly working. A tape-out in this state buys silicon that cannot be '
     'tested, at the same price as a working one.'),
    ('Why these 44 resisted', s_why,
     'Why did these forty-four resist every round? Thirty of them are SRAM data pins. The pin sits on the macro\'s south '
     'edge. The pocket in front of it was blocked for placement, so the load buffer landed on the far side, and the only '
     'route to it went straight through the macro. The planner had taken the macro centre as the pin, so it never moved '
     'them.'),
    ('Round H: the fix', s_fix,
     'Round {H|H} fixes the cause. The planner now uses the true pin edge, lifts the blockage, and moves each far-side '
     'load into the pocket in front of its pin: thirty-five cells, forty-four nets re-routed with the obstructions kept, '
     'twenty passes.'),
    ('Where we stand', s_stand,
     'Round {H|H} is running now. The number to watch is the nets touching both supplies: thirteen after round E, eight '
     'after F and G. If H takes it to zero, the GDS goes out by noon. If not, the honest answer to IHP is the twentieth.'),
    ('', V.s_end, ''),
]

if __name__ == '__main__':
    V.main()
