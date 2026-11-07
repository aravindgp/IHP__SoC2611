#!/usr/bin/env python3
"""Open areas of a placement: occupancy grid (50 um, macros grown by 20 um) over the usable box 440..6160, then the
largest macro-free rectangles.  Optionally ignores macros with llx < XW (the west column to be relocated) and lists
them.  usage: fp_free_rects.py <macros.txt> <place.pl> [XW=0] [min_w=500] [min_h=300]"""
import collections
import sys

import numpy as np

mac, pl = sys.argv[1:3]
XW = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
MINW = float(sys.argv[4]) if len(sys.argv) > 4 else 500.0
MINH = float(sys.argv[5]) if len(sys.argv) > 5 else 300.0
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
bx = []
for l in open(pl):
    p = l.split()
    if len(p) != 4:
        continue
    w, h = S[p[0]]
    bx.append((p[0], float(p[1]), float(p[2]), float(p[1]) + w, float(p[2]) + h, p[3]))
west = [b for b in bx if b[1] < XW]
if west:
    print('relocate', len(west), 'macros, y', min(b[2] for b in west), '-', max(b[4] for b in west))
    kinds = collections.Counter()
    for b in west:
        k = 'pcore' if 'pcore' in b[0] else 'stream' if 'stream' in b[0] else 'axi' if 'axi_' in b[0] else 'other'
        kinds[(k, S[b[0]])] += 1
    for k, v in sorted(kinds.items()):
        print('  ', v, 'x', k)
g = 50.0
n = int(5720 / g)
occ = np.zeros((n, n), bool)
for b in bx:
    if b in west:
        continue
    x0 = max(0, int((b[1] - 440 - 20) // g)); x1 = min(n, int(np.ceil((b[3] - 440 + 20) / g)))
    y0 = max(0, int((b[2] - 440 - 20) // g)); y1 = min(n, int(np.ceil((b[4] - 440 + 20) / g)))
    occ[y0:y1, x0:x1] = True
H = np.zeros((n, n), int)
for i in range(n):
    for j in range(n):
        H[i, j] = 0 if occ[i, j] else (H[i - 1, j] + 1 if i > 0 else 1)
res = []
for i in range(n):
    st = []
    for j in range(n + 1):
        h = H[i, j] if j < n else 0
        start = j
        while st and st[-1][1] >= h:
            idx, hh = st.pop()
            if hh * g >= MINH and (j - idx) * g >= MINW:
                res.append((hh * (j - idx), idx, i - hh + 1, j, i))
            start = idx
        st.append((start, h))
res.sort(reverse=True)
seen = []
for area, x0, y0, x1, y1 in res:
    r = (440 + x0 * g, 440 + y0 * g, 440 + x1 * g, 440 + (y1 + 1) * g)
    if any(not (r[2] <= s[0] or s[2] <= r[0] or r[3] <= s[1] or s[3] <= r[1]) for s in seen):
        continue
    seen.append(r)
    print('free rect x %d-%d y %d-%d  (%d x %d um, %.2f mm2)' % (r[0], r[2], r[1], r[3], r[2] - r[0], r[3] - r[1],
                                                                  (r[2] - r[0]) * (r[3] - r[1]) / 1e6))
    if len(seen) >= 10:
        break
