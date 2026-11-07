#!/usr/bin/env python3
"""Count GRT guide boxes that lie inside the IO-cell band (default 140..318 um from each die edge) per side and layer,
and the nets that have one. Gate for the west-band ECO: after chip_grt.tcl with the band obstructed, this must be ~0.
usage: guide_band.py <route.guide> [die_um=6600] [lo=140] [hi=318]"""
import collections
import sys

g = sys.argv[1]
die = float(sys.argv[2]) if len(sys.argv) > 2 else 6600.0
lo = float(sys.argv[3]) if len(sys.argv) > 3 else 140.0
hi = float(sys.argv[4]) if len(sys.argv) > 4 else 318.0
dbu = 1000.0
cnt = collections.defaultdict(collections.Counter)
nets = collections.defaultdict(set)
cur = None
with open(g) as f:
    for ln in f:
        p = ln.split()
        if len(p) == 1 and p[0] not in '()':
            cur = p[0]
            continue
        if len(p) != 5:
            continue
        x0, y0, x1, y1 = (int(v) / dbu for v in p[:4])
        lay = p[4]
        for side, inside in (('W', x0 < hi and x1 > lo), ('E', x1 > die - hi and x0 < die - lo),
                             ('S', y0 < hi and y1 > lo), ('N', y1 > die - hi and y0 < die - lo)):
            if inside:
                cnt[side][lay] += 1
                nets[side].add(cur)
tot = sum(sum(c.values()) for c in cnt.values())
print(f"GUIDE_BAND total boxes in band {lo:.0f}..{hi:.0f} um: {tot}")
for side in 'WESN':
    c = cnt[side]
    print(f"  {side}: {sum(c.values()):6d} boxes, {len(nets[side]):5d} nets  " + ', '.join(f"{l} {n}" for l, n in c.most_common()))
