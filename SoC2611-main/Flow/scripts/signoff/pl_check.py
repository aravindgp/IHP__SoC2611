#!/usr/bin/env python3
"""Strict checks of a .pl placement: count, unknown names, orientations, box 440..6160 (or core with --core),
true overlaps, and the smallest vertical / horizontal gap between neighbouring macros.
usage: pl_check.py <macros.txt> <place.pl> [--core]"""
import sys

mac, pl = sys.argv[1:3]
core = '--core' in sys.argv
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
rows = [l.split() for l in open(pl) if len(l.split()) == 4]
unknown = [r[0] for r in rows if r[0] not in S]
ori = sorted(set(r[3] for r in rows))
bx = [(r[0], float(r[1]), float(r[2]), float(r[1]) + S[r[0]][0], float(r[2]) + S[r[0]][1]) for r in rows if r[0] in S]
lo, hi = (340.32, 6259.68) if core else (440.0, 6160.0)
outside = sum(1 for b in bx if b[1] < lo - 1e-6 or b[2] < lo - 1e-6 or b[3] > hi + 1e-6 or b[4] > hi + 1e-6)
ov = 0; minv = 1e9; minh = 1e9
for i in range(len(bx)):
    for j in range(i + 1, len(bx)):
        a, b = bx[i], bx[j]
        if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]:
            ov += 1; print('OVERLAP', a[0][-50:], b[0][-50:])
            continue
        xo = a[1] < b[3] and b[1] < a[3]
        yo = a[2] < b[4] and b[2] < a[4]
        if xo:
            minv = min(minv, max(b[2] - a[4], a[2] - b[4]))
        if yo:
            minh = min(minh, max(b[1] - a[3], a[1] - b[3]))
print(f'macros {len(rows)} unknown {len(unknown)} orients {ori} outside {outside} overlaps {ov} '
      f'min vertical gap {minv:.1f} um  min horizontal gap {minh:.1f} um  missing {len(set(S) - set(r[0] for r in rows))}')
