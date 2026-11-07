#!/usr/bin/env python3
"""Picture of the south-west corner: IO band, strip, SRAM macros, DRT markers and the guide boxes of the west nets
before/after a guide rewrite. usage: sw_corner_svg.py <macros.txt> <drc.rpt> <guide_before> <guide_after> <keep> <out.svg>
window: x 0..1000 um, y 300..1800 um."""
import re
import sys

macf, rpt, gb, ga, keepf, out = sys.argv[1:7]
X0, X1, Y0, Y1 = 0.0, 1000.0, 300.0, 1800.0
S = 0.9  # px per um
W, H = int((X1 - X0) * S), int((Y1 - Y0) * S)
keep = set(l.strip() for l in open(keepf) if l.strip())


def px(x):
    return (x - X0) * S


def py(y):
    return H - (y - Y0) * S


def guide_boxes(path):
    cur = None
    res = []
    for ln in open(path):
        p = ln.split()
        if len(p) == 1 and p[0] not in '()':
            cur = p[0]
        elif len(p) == 5 and cur not in keep:
            x0, y0, x1, y1 = (int(v) / 1000 for v in p[:4])
            if x1 > X0 and x0 < X1 and y1 > Y0 and y0 < Y1 and (x0 < 370 or x1 < 900):
                res.append((x0, y0, x1, y1, p[4]))
    return res


def panel(ox, title, boxes, colour):
    s = [f'<g transform="translate({ox} 40)">', f'<text x="0" y="-12" font-size="16" font-weight="bold">{title}</text>',
         f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fafafa" stroke="#888"/>']
    # IO band 140..320 and strip 320..365.7
    s.append(f'<rect x="{px(140)}" y="0" width="{(320-140)*S}" height="{H}" fill="#ffe0e0"/>')
    s.append(f'<rect x="{px(320)}" y="0" width="{(365.7-320)*S}" height="{H}" fill="#fff3c4"/>')
    for ln in open(macf):
        x0, y0, x1, y1 = map(float, ln.split()[:4])
        if x1 > X0 and x0 < X1 and y1 > Y0 and y0 < Y1:
            s.append(f'<rect x="{px(x0)}" y="{py(y1)}" width="{(x1-x0)*S}" height="{(y1-y0)*S}" fill="#d8e4f0" stroke="#5a7fa8"/>')
    for x0, y0, x1, y1, l in boxes:
        s.append(f'<rect x="{px(max(x0, X0))}" y="{py(min(y1, Y1))}" width="{(min(x1, X1)-max(x0, X0))*S}" '
                 f'height="{(min(y1, Y1)-max(y0, Y0))*S}" fill="{colour}" fill-opacity="0.08" stroke="{colour}" stroke-opacity="0.5" stroke-width="0.5"/>')
    pat = re.compile(r"bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)")
    n = 0
    for b in open(rpt, errors='replace').read().split("violation type:")[1:]:
        m = pat.search(b)
        if not m:
            continue
        x = (float(m.group(1)) + float(m.group(3))) / 2
        y = (float(m.group(2)) + float(m.group(4))) / 2
        if X0 <= x < X1 and Y0 <= y < Y1:
            n += 1
            if n % 3 == 0:
                s.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="1.2" fill="#c00"/>')
    s.append(f'<text x="8" y="{H-8}" font-size="12">{n} DRT markers (every 3rd drawn), x 0..1000 um, y 300..1800 um; '
             f'pink = IO band, yellow = strip, blue = SRAM, {len(boxes)} guide boxes of the west nets</text>')
    s.append('</g>')
    return '\n'.join(s)


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{2*W+60}" height="{H+60}" font-family="sans-serif">',
       f'<rect width="{2*W+60}" height="{H+60}" fill="white"/>',
       panel(20, 'Before: guides of the west nets (orange), run D markers', guide_boxes(gb), '#e07000'),
       panel(W + 40, 'After: soft channel (green)', guide_boxes(ga), '#108040'), '</svg>']
open(out, 'w').write('\n'.join(svg))
print('wrote', out)
