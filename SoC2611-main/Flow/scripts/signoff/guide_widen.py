#!/usr/bin/env python3
"""Soft channel v2, a pure widening of the guides (nothing moved, so connectivity cannot break): for every box of a
non-pad net that sits in the strip column next to the IO band (x in INNER..INNER+G, the column guide_clamp.py
projects onto), add a box covering the whole strip (INNER..STRIP_E) on the same layer and y-range, and if the box is
beside SRAM column 1 (y < YTOP) also a box across the gap between SRAM columns 1 and 2 (GAP_W..GAP_E) plus a Metal3
connector along the same y so the router may use the gap. Input must be an already clamped guide file.
usage: guide_widen.py <in_clamped.guide> <out.guide> <keep_nets.txt> [gap=1]"""
import os
import sys

src, dst, keepf = sys.argv[1:4]
use_gap = (sys.argv[4] if len(sys.argv) > 4 else '1') == '1'
G = 7200
INNER = 316800
# 7 gcell columns: 316.8 .. 367.2 um (SRAM column 1 starts at 365.7); env GUIDE_STRIP_E overrides (shifted column)
STRIP_E = int(os.environ.get('GUIDE_STRIP_E', 367200))
GAP_W, GAP_E = 784800, 828000
YTOP = 1700000
keep = set(l.strip() for l in open(keepf) if l.strip())
out = open(dst, 'w')
cur = None
boxes = []
added = nets = 0


def flush():
    global added, nets
    if cur is None:
        return
    extra = []
    if cur not in keep:
        for x0, y0, x1, y1, l in boxes:
            if x0 >= INNER and x1 <= INNER + G:
                extra.append((INNER, y0, STRIP_E, y1, l))
                if use_gap and y0 < YTOP and l in ('Metal2', 'Metal4'):
                    extra.append((GAP_W, y0, GAP_E, y1, l))
                    extra.append((INNER, y0, GAP_E, min(y1, y0 + G), 'Metal3'))
    if extra:
        nets += 1
        added += len(extra)
    out.write(cur + '\n(\n' + ''.join(f"{b[0]} {b[1]} {b[2]} {b[3]} {b[4]}\n" for b in boxes + extra) + ')\n')


for ln in open(src):
    p = ln.split()
    if len(p) == 1 and p[0] not in '()':
        flush()
        cur = p[0]
        boxes = []
    elif len(p) == 5:
        boxes.append((int(p[0]), int(p[1]), int(p[2]), int(p[3]), p[4]))
flush()
out.close()
print(f"GUIDE_WIDEN added {added} boxes on {nets} nets (gap={'on' if use_gap else 'off'}) -> {dst}")
