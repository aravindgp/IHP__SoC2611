#!/usr/bin/env python3
"""Nets with signal-to-signal shorts outside macros inside a window, as a pairs-like file for nets_pins_xy_exact.tcl.
usage: knot_nets.py <drc.rpt> <macros.txt> <place.pl> x0 y0 x1 y1 > knot_nets.txt"""
import re
import sys

rpt, mac_f, pl_f = sys.argv[1:4]
x0, y0, x1, y1 = [float(v) for v in sys.argv[4:8]]
wh = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac_f) if len(l.split()) == 4}
macs = []
for l in open(pl_f):
    p = l.split()
    if len(p) == 4 and p[0] in wh:
        w, h = wh[p[0]]; macs.append((float(p[1]), float(p[2]), float(p[1]) + w, float(p[2]) + h))
def inside(x, y): return any(a <= x <= c and b <= y <= d for a, b, c, d in macs)
nets = set()
for b in open(rpt, errors='replace').read().split('violation type:')[1:]:
    if b.split('\n')[0].strip() != 'Short': continue
    m = re.search(r'srcs:(.*)', b); bb = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)', b)
    if not m or not bb: continue
    ns = [s[4:] for s in m.group(1).split() if s.startswith('net:')]
    if len(ns) < 2 or any(re.fullmatch(r'(?i)(vdd\w*|vss\w*)', s.split('/')[-1]) for s in ns): continue
    x = (float(bb.group(1)) + float(bb.group(3))) / 2; y = (float(bb.group(2)) + float(bb.group(4))) / 2
    if inside(x, y) or not (x0 <= x <= x1 and y0 <= y <= y1): continue
    nets.update(ns)
for n in sorted(nets): print(f'1 {n} knot')
