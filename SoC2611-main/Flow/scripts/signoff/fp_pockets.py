#!/usr/bin/env python3
"""Dead spaces of a macro placement: (1) pockets = gaps of 30..130 um between two vertically adjacent macros whose
pin edges face each other (lower macro pins north = MX/R180, upper macro pins south = R0/MY), (2) margin strips =
the band between the core edge and an edge macro whose pins face away from the edge.  Standard cells placed there
have no vertical routing exit (M1-M4 are blocked inside RM_IHPSG13 macros, the process has no layer above TopMetal1).
usage: fp_pockets.py <macros.txt> <place.pl> [core_lo=340.3] [core_hi=6259.7]   prints "BLK x0 y0 x1 y1  # why" """
import sys

mac, pl = sys.argv[1:3]
lo = float(sys.argv[3]) if len(sys.argv) > 3 else 340.3
hi = float(sys.argv[4]) if len(sys.argv) > 4 else 6259.7
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
M = []
for l in open(pl):
    p = l.split()
    if len(p) == 4 and p[0] in S:
        x, y = float(p[1]), float(p[2])
        w, h = S[p[0]]
        M.append((p[0], x, y, x + w, y + h, p[3]))
pins_north = lambda o: o in ('MX', 'R180')
pins_south = lambda o: o in ('R0', 'MY')
out = []
for a in M:
    for b in M:
        if a is b or b[2] < a[4]:
            continue
        gap = b[2] - a[4]
        ox0, ox1 = max(a[1], b[1]), min(a[3], b[3])
        if ox1 - ox0 <= 0.5 * min(a[3] - a[1], b[3] - b[1]):
            continue
        if 30 <= gap <= 130 and pins_north(a[5]) and pins_south(b[5]):
            out.append((ox0, a[4], ox1, b[2], f'pocket {gap:.0f} um between {a[0].split("/")[-2][-30:]} {a[5]} and {b[0].split("/")[-2][-30:]} {b[5]}'))
        elif 3 < gap < 30 and not any(c is not a and c is not b and c[2] < b[2] and c[4] > a[4] and
                                       min(c[3], ox1) > max(c[1], ox0) for c in M):
            # thin blank gap (any orientation): 1-7 cell rows with no vertical exit at all
            out.append((ox0, a[4], ox1, b[2], f'thin gap {gap:.0f} um between {a[0].split("/")[-2][-30:]} {a[5]} and {b[0].split("/")[-2][-30:]} {b[5]}'))
for n, x0, y0, x1, y1, o in M:
    if y0 - lo <= 130 and pins_north(o):
        out.append((x0, lo, x1, y0, f'south margin strip under {n.split("/")[-2][-30:]} {o}'))
    if hi - y1 <= 130 and pins_south(o):
        out.append((x0, y1, x1, hi, f'north margin strip over {n.split("/")[-2][-30:]} {o}'))
out.sort(key=lambda r: (r[1], r[0]))
for x0, y0, x1, y1, why in out:
    print(f'BLK {x0:.2f} {y0:.2f} {x1:.2f} {y1:.2f}  # {why}')
print(f'# {len(out)} dead spaces, {sum((r[2]-r[0])*(r[3]-r[1]) for r in out)/1e6:.2f} mm2')
