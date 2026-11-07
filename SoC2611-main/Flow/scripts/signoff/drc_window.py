#!/usr/bin/env python3
"""Count DRT markers inside an x/y window (um), per layer. usage: drc_window.py <rpt> x0 x1 y0 y1"""
import collections
import re
import sys

pat = re.compile(r"bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)")
x0, x1, y0, y1 = map(float, sys.argv[2:6])
c = collections.Counter()
for b in open(sys.argv[1], errors='replace').read().split("violation type:")[1:]:
    m = pat.search(b)
    if not m:
        continue
    x = (float(m.group(1)) + float(m.group(3))) / 2
    y = (float(m.group(2)) + float(m.group(4))) / 2
    if x0 <= x < x1 and y0 <= y < y1:
        c[m.group(5)] += 1
print(f"{sys.argv[1]} window x {x0:.0f}-{x1:.0f} y {y0:.0f}-{y1:.0f}: {sum(c.values())}  " + ', '.join(f"{k} {v}" for k, v in c.most_common()))
