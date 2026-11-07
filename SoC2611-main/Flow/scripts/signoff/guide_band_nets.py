#!/usr/bin/env python3
"""Which nets still have guide boxes inside the IO band, and whether they are pad nets.
usage: guide_band_nets.py <route.guide> <padnets.txt> [lo=140] [hi=316.8]"""
import sys

g, padf = sys.argv[1:3]
lo = float(sys.argv[3]) * 1000 if len(sys.argv) > 3 else 140000
hi = float(sys.argv[4]) * 1000 if len(sys.argv) > 4 else 316800
die = 6600000
pads = set(l.strip() for l in open(padf) if l.strip())
cur = None
inband = {}
for ln in open(g):
    p = ln.split()
    if len(p) == 1 and p[0] not in '()':
        cur = p[0]
    elif len(p) == 5:
        x0, y0, x1, y1 = map(int, p[:4])
        if (x0 < hi and x1 > lo) or (x1 > die - hi and x0 < die - lo) or (y0 < hi and y1 > lo) or (y1 > die - hi and y0 < die - lo):
            inband[cur] = inband.get(cur, 0) + 1
pad = [n for n in inband if n in pads]
non = [n for n in inband if n not in pads]
print(f"GUIDE_BAND_NETS {len(inband)} nets in band: {len(pad)} pad nets ({sum(inband[n] for n in pad)} boxes), "
      f"{len(non)} NON-pad nets ({sum(inband[n] for n in non)} boxes)")
for n in non[:10]:
    print('  non-pad:', n, inband[n])
