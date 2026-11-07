#!/usr/bin/env python3
"""List the macros of a .pl placement that touch a window.  usage: pl_window.py <macros.txt> <place.pl> x0 y0 x1 y1"""
import sys

mac, pl = sys.argv[1:3]
x0, y0, x1, y1 = map(float, sys.argv[3:7])
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
for l in open(pl):
    p = l.split()
    if len(p) != 4:
        continue
    n, x, y, o = p[0], float(p[1]), float(p[2]), p[3]
    w, h = S[n]
    if x + w > x0 and x < x1 and y + h > y0 and y < y1:
        own = 'dp' if '/dp_' in n else 'axi' if 'axi_' in n else 'cam' if 'vstream' in n else n.split('/')[1][:10]
        print(f'{own:4s} x {x:7.1f}-{x + w:7.1f}  y {y:7.1f}-{y + h:7.1f}  {o:3s}  {n.split("/")[-1]}')
