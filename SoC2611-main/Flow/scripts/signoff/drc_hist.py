#!/usr/bin/env python3
"""Histogram of DRC markers (from drt::check_drc report) along y inside an x range, per layer.
usage: drc_hist.py <drc.rpt> x0 x1 [bin_um=20] [y0 y1]"""
import collections
import re
import sys

fn = sys.argv[1]
x0, x1 = float(sys.argv[2]), float(sys.argv[3])
b = float(sys.argv[4]) if len(sys.argv) > 4 else 20.0
y0 = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
y1 = float(sys.argv[6]) if len(sys.argv) > 6 else 1e9
H = collections.defaultdict(collections.Counter)
typ = None
for l in open(fn):
    if l.startswith('violation type:'):
        typ = l.split(':', 1)[1].strip()
    m = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', l)
    if m:
        bx0, by0, bx1, by1 = map(float, m.groups()[:4])
        lay = m.group(5)
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        if x0 <= cx < x1 and y0 <= cy < y1:
            H[lay][int(cy // b) * b] += 1
for lay in sorted(H):
    tot = sum(H[lay].values())
    print(f'--- {lay}: {tot} markers, x {x0:.0f}-{x1:.0f}')
    for y in sorted(H[lay]):
        n = H[lay][y]
        if n >= max(5, tot * 0.01):
            print(f'  y {y:6.0f} {n:6d} {"#" * min(60, n // max(1, tot // 60))}')
