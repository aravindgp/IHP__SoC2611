#!/usr/bin/env python3
"""Third explainer: the eight ECO rounds of 8-9 November (timeline, what each attacked, the counts), why routing
closure means a sound route (IHP DRC scoreboard), what is verified and what is not, and the ask to IHP.
Reuses make_status_video.py (same look, voice and renderer).  usage: make_rounds_video.py <out_dir> [--preview]"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_status_video as V
from PIL import ImageDraw

C_WHITE, C_GREY, C_DIM, C_AMBER, C_TEAL, C_BLUE, C_GREEN, C_RED, C_PURPLE = (
    V.C_WHITE, V.C_GREY, V.C_DIM, V.C_AMBER, V.C_TEAL, V.C_BLUE, V.C_GREEN, V.C_RED, V.C_PURPLE)
text, rrect, seg, lerp, mix, rgba, bar = V.text, V.rrect, V.seg, V.lerp, V.mix, V.rgba, V.bar

# (round, start hour from 8 Nov 00:00 IST, end hour, inside shorts, total, phase colour)
ROUNDS = [('A', 11.0, 13.2, 439, '4,819', C_TEAL), ('B', 13.2, 18.15, 208, '2,071', C_TEAL), ('C', 18.15, 21.07, 165, '1,689', C_TEAL),
          ('D', 21.15, 24.1, 156, '1,662', C_TEAL), ('E', 24.1, 27.38, 105, '1,683', C_PURPLE), ('F', 27.38, 29.75, 90, '1,428', C_PURPLE),
          ('G', 29.75, 32.1, 95, '1,384', C_PURPLE), ('H', 32.25, 34.5, None, 'running', C_GREEN)]

def s_timeline(layer, t, dur):
    d = ImageDraw.Draw(layer)
    x0, x1 = 150, 1000; h0, h1 = 10.0, 35.0
    X = lambda h: lerp(x0, x1, (h - h0) / (h1 - h0))
    for hh, lab in ((12, '8 Nov 12:00'), (18, '18:00'), (24, '9 Nov 00:00'), (30, '06:00')):
        d.line([(X(hh), 250), (X(hh), 980)], fill=rgba((40, 48, 64)), width=1)
        text(d, (X(hh), 235), lab, 18, C_DIM, 'Medium', 'mm')
    for i, (r, s, e, inside, total, col) in enumerate(ROUNDS):
        a = seg(t, 0.3 + i * 0.35, 0.5)
        if a <= 0: continue
        y = 280 + i * 86
        text(d, (90, y + 22), r, 30, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
        xe = lerp(X(s), X(e), a)
        rrect(d, (X(s), y, max(xe, X(s) + 6), y + 44), 10, fill=rgba(col, 200 * a))
        if r == 'H':
            pa = 0.5 + 0.5 * math.sin(t * 4)
            rrect(d, (X(s), y, X(e), y + 44), 10, outline=rgba(col, 120 + 120 * pa), width=2)
        dh = e - s; lab = f'{int(dh)} h {int(round((dh - int(dh)) * 60)):02d}'
        text(d, (X(e) + 12, y + 22), lab if r != 'H' else 'running', 20, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        if inside is not None: text(d, (1010, y + 22), f'{inside}', 22, rgba(col, 255 * a), 'Bold', 'rm')
    a = seg(t, 3.4, 0.6)
    if a > 0:
        text(d, (1010, 262), 'shorts inside', 16, rgba(C_GREY, 255 * a), 'Medium', 'rm')
        text(d, (540, 1040), 'eight rounds, 23 hours, 687 to 95 so far', 26, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 1082), 'each round: re-plan from the last DRC report, ECO, 20 to 24 route passes', 20, rgba(C_GREY, 255 * a), 'Medium', 'mm')

PHASES = [('A to D', 'side moves', 'cells on the minority side of a crossing net moved across the macro row', '687 → 156', C_TEAL),
          ('E to G', 'obstructions + full re-route', 'Metal2/4 obstructions inside every macro, all crossing nets re-routed', '156 → 95', C_PURPLE),
          ('H', 'loads into the pin pockets', 'true pin edge; far-side loads of SRAM data pins moved in front of the pin', '95 → ?', C_GREEN)]

def s_phases(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (rounds, name, detail, nums, col) in enumerate(PHASES):
        a = seg(t, 0.4 + i * 1.2, 0.5)
        if a <= 0: continue
        y = 250 + i * 250; dx = (1 - a) * 50
        rrect(d, (70 + dx, y, 1010 + dx, y + 210), 20, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 200 * a), width=2)
        text(d, (100 + dx, y + 44), rounds, 26, rgba(col, 255 * a), 'Bold', 'lm')
        text(d, (100 + dx, y + 90), name, 34, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
        words = detail.split(); half = len(words) // 2 + 1
        text(d, (100 + dx, y + 140), ' '.join(words[:half]), 22, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        text(d, (100 + dx, y + 172), ' '.join(words[half:]), 22, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        text(d, (980 + dx, y + 44), nums, 30, rgba(col, 255 * a), 'Bold', 'rm')

def s_counts(layer, t, dur):
    d = ImageDraw.Draw(layer)
    text(d, (330, 250), 'shorts inside the SRAM macros', 24, C_TEAL, 'SemiBold', 'mm')
    d.line([(60, 640), (640, 640)], fill=rgba(C_DIM), width=2)
    vals = [(r, i, c) for r, s, e, i, tot, c in ROUNDS if i is not None]
    for k, (r, v, c) in enumerate(vals):
        bar(d, 70 + k * 78, 640, 56, 330, v, 450, c, r, f'{v}', seg(t, 0.3 + k * 0.3, 0.6), 22)
    pa = 0.5 + 0.5 * math.sin(t * 4)
    if t > 2.6:
        x = 70 + 7 * 78
        d.rectangle((x, 640 - 70, x + 56, 640), outline=rgba(C_GREEN, 120 + 120 * pa), width=3)
        text(d, (x + 28, 662), 'H', 22, C_GREEN, 'Medium', 'mm'); text(d, (x + 28, 640 - 92), '?', 24, C_GREEN, 'Bold', 'mm')
    text(d, (860, 250), 'nets touching VDD and VSS', 24, C_RED, 'SemiBold', 'mm')
    d.line([(700, 640), (1020, 640)], fill=rgba(C_DIM), width=2)
    for k, (r, v) in enumerate([('E', 13), ('F', 8), ('G', 8)]):
        bar(d, 715 + k * 80, 640, 56, 330, v, 15, C_RED, r, f'{v}', seg(t, 1.2 + k * 0.3, 0.6), 24)
    if t > 2.6:
        x = 715 + 3 * 80
        d.rectangle((x, 640 - 70, x + 56, 640), outline=rgba(C_GREEN, 120 + 120 * pa), width=3)
        text(d, (x + 28, 662), 'H', 22, C_GREEN, 'Medium', 'mm'); text(d, (x + 28, 640 - 92), '?', 24, C_GREEN, 'Bold', 'mm')
    a = seg(t, 3.2, 0.6)
    if a > 0:
        rrect(d, (90, 780, 990, 1000), 20, fill=rgba((20, 26, 38), 240 * a), outline=rgba((40, 48, 64), 255 * a))
        text(d, (540, 828), 'the red bars decide whether the chip powers up', 25, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')
        text(d, (540, 880), 'all 8 are SRAM data-pin nets: the kind round H treats', 23, rgba(C_GREY, 255 * a), 'Medium', 'mm')
        text(d, (540, 930), 'zero is two or three rounds away for the inside count', 23, rgba(C_GREY, 255 * a), 'Medium', 'mm')
        text(d, (540, 970), 'each round about 2 h 20', 21, rgba(C_DIM, 255 * a), 'Medium', 'mm')

CLEAN = ['Activ', 'GatPoly', 'Cont', 'Via1', 'Via2-3', 'TopVia1', 'Metal1', 'Forbidden C5L', 'PWell block', 'nBuLay', 'Latch-up',
         'Forbidden', 'Pad', 'Passiv', 'Seal ring', 'Density', 'Metal slits', 'Thick ox', 'Pin', 'LBE', 'PSD', 'Activ fill', 'Poly fill']
DIRTY = [('Metal4 spacing', '971', 'the shorts inside the SRAMs themselves', C_RED), ('TopMetal1 / Metal2 spacing', '41 + 10', 'routing residue, cleared by the final passes', C_AMBER),
         ('fill to metal, die corners', '34', 'fill squares at a 45° chamfer, fixed in the fill step', C_AMBER)]

def s_drc(layer, t, dur):
    d = ImageDraw.Draw(layer)
    text(d, (540, 240), "IHP's own precheck deck on the current GDS", 24, C_GREY, 'Medium', 'mm')
    for i, nm in enumerate(CLEAN):
        a = seg(t, 0.3 + i * 0.08, 0.3)
        if a <= 0: continue
        r, c = divmod(i, 4); x0 = 70 + c * 240; y0 = 285 + r * 58
        rrect(d, (x0, y0, x0 + 225, y0 + 46), 12, fill=rgba((16, 40, 30), 240 * a), outline=rgba(C_GREEN, 140 * a))
        text(d, (x0 + 14, y0 + 23), nm, 19, rgba(C_WHITE, 255 * a), 'Medium', 'lm')
        text(d, (x0 + 210, y0 + 23), '0', 20, rgba(C_GREEN, 255 * a), 'Bold', 'rm')
    for i, (nm, n, why, col) in enumerate(DIRTY):
        a = seg(t, 2.6 + i * 0.5, 0.5)
        if a <= 0: continue
        y0 = 650 + i * 100
        rrect(d, (70, y0, 1010, y0 + 84), 14, fill=rgba((20, 26, 38), 240 * a), outline=rgba(col, 180 * a))
        text(d, (96, y0 + 28), nm, 24, rgba(C_WHITE, 255 * a), 'Bold', 'lm')
        text(d, (96, y0 + 60), why, 20, rgba(C_GREY, 255 * a), 'Medium', 'lm')
        text(d, (985, y0 + 42), n, 34, rgba(col, 255 * a), 'Bold', 'rm')
    a = seg(t, 4.2, 0.6)
    if a > 0:
        text(d, (540, 1000), 'the shorts are the problem, not a symptom of a broken flow', 24, rgba(C_WHITE, 255 * a), 'SemiBold', 'mm')

VER = [('verified', C_GREEN, ['chip top passes its simulation suites (HyperRAM, memories, boot)', 'IHP memory layer formally equivalent to the FPGA one (25 / 25)',
                              'density, seal ring, pad ring, fill: clean on the precheck deck', 'the post-route chain rehearsed end to end']),
       ('still to run', C_AMBER, ['LVS of the released GDS against the released netlist', 'timing sign-off: hold on the CPU to SRAM paths',
                                   'antenna repair (rehearsed, not applied)', 'FPGA regression of this exact configuration'])]

def s_verified(layer, t, dur):
    d = ImageDraw.Draw(layer)
    for i, (title, col, items) in enumerate(VER):
        y0 = 240 + i * 420
        a = seg(t, 0.3 + i * 1.8, 0.5)
        if a <= 0: continue
        text(d, (80, y0), title, 30, rgba(col, 255 * a), 'Bold', 'lm')
        for k, it in enumerate(items):
            b = seg(t, 0.6 + i * 1.8 + k * 0.3, 0.4)
            if b <= 0: continue
            y = y0 + 50 + k * 78
            rrect(d, (70, y, 1010, y + 64), 14, fill=rgba((20, 26, 38), 240 * b), outline=rgba((40, 48, 64), 255 * b))
            d.ellipse((92, y + 20, 116, y + 44), fill=rgba(col, 255 * b))
            text(d, (134, y + 32), it, 21, rgba(C_WHITE, 255 * b), 'Medium', 'lm')

def s_ask(layer, t, dur):
    d = ImageDraw.Draw(layer)
    a = seg(t, 0.3, 0.7)
    rrect(d, (90, 300, 990, 620), 26, fill=rgba((20, 26, 38), 240 * a), outline=rgba(C_AMBER, 220 * a), width=3)
    text(d, (540, 360), 'The ask to IHP', 30, rgba(C_AMBER, 255 * a), 'Bold', 'mm')
    text(d, (540, 430), 'a few days on the November run', 40, rgba(C_WHITE, 255 * a), 'Bold', 'mm')
    text(d, (540, 495), 'to deliver a checked GDS: routing closed, antenna repaired,', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    text(d, (540, 530), 'DRC and LVS clean, timing report, hashes', 22, rgba(C_GREY, 255 * a), 'Medium', 'mm')
    text(d, (540, 580), 'target: 12 November', 26, rgba(C_TEAL, 255 * a), 'SemiBold', 'mm')
    b = seg(t, 2.4, 0.6)
    if b > 0:
        rrect(d, (90, 700, 990, 860), 22, fill=rgba((20, 26, 38), 240 * b), outline=rgba((40, 48, 64), 255 * b))
        text(d, (540, 745), 'what we will not do', 24, rgba(C_RED, 255 * b), 'Bold', 'mm')
        text(d, (540, 795), 'submit a GDS with supply shorts to make a date', 24, rgba(C_WHITE, 255 * b), 'SemiBold', 'mm')
        text(d, (540, 832), 'a dead chip costs the same as a working one', 20, rgba(C_GREY, 255 * b), 'Medium', 'mm')
    c = seg(t, 4.0, 0.6)
    if c > 0:
        text(d, (540, 960), 'if the days are not available: the 20 November paid slot, else 14 March 2027', 21, rgba(C_GREY, 255 * c), 'Medium', 'mm')

V.SCENES = [
    ('Eight rounds in 23 hours', s_timeline,
     'Since yesterday morning the routed chip has been through eight ECO rounds, back to back, about two and a half hours '
     'each. Every round re-plans from the previous round\'s DRC report, applies its moves, and re-routes only the touched '
     'nets for twenty to twenty-four passes.'),
    ('What each round attacked', s_phases,
     'Rounds A to D moved the minority-side cells of every crossing net across the macro row: six hundred and eighty-seven '
     'shorts inside the SRAMs down to one hundred and fifty-six. Rounds E to G added obstructions inside every macro and '
     're-routed all crossing nets: down to ninety-five. Round {H|H} treats the cause of the rest: the loads of SRAM data '
     'pins, moved into the pocket in front of their pin.'),
    ('The count that matters', s_counts,
     'The red bars decide whether the chip powers up: nets that touch both VDD and VSS. Thirteen after round E, eight '
     'after F and G. All eight are SRAM data-pin nets, exactly the kind round {H|H} treats. Zero shorts inside the '
     'macros is still two or three rounds away.'),
    ('Why closure means a sound route', s_drc,
     'Why are we confident the chip works once the shorts are closed? Because IHP\'s own precheck deck, run on the current '
     'GDS, is clean on every table but four. The nine hundred and seventy-one Metal four markers are the shorts themselves. '
     'The rest is routing residue and a fill detail at the die corners. The shorts are the problem, not a symptom of a '
     'broken flow.'),
    ('Verified, and still to run', s_verified,
     'What is verified: the chip top passes its simulation suites, the IHP memory layer is formally equivalent to the FPGA '
     'one, and density, seal ring and pad ring are clean. What is still to run before we call it done: LVS, the hold timing '
     'on the CPU to SRAM paths, antenna repair, and an FPGA regression of this exact configuration.'),
    ('The ask', s_ask,
     'So the ask to IHP is time, not leniency: a few days on the November run, to deliver a checked GDS by the twelfth. '
     'What we will not do is submit a GDS with supply shorts to make a date. If the days are not available, the paid slot '
     'on the twentieth, and failing that, March.'),
    ('', V.s_end, ''),
]

if __name__ == '__main__':
    V.main()
