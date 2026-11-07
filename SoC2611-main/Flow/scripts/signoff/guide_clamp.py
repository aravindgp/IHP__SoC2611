#!/usr/bin/env python3
"""Keep GRT guides out of the IO-cell band by clamping every guide box that enters it to the first gcell column/row
inside the core side of the band (a monotone projection, so each net's guide stays connected). GRT itself cannot be
told to avoid the band: capacity reductions there underflow (3 Nov: obstructions/region adjustments RAISED the
band's apparent capacity). Nets listed in KEEP (the pad nets, whose pins sit on the band's inner edge) are left as
they are. Guide coordinates are dbu (1000/um); the gcell grid is 7.2 um from the die origin.
usage: guide_clamp.py <in.guide> <out.guide> <keep_nets.txt> [die_um=6600] [inner_dbu=316800]"""
import sys

src, dst, keepf = sys.argv[1:4]
die = int(float(sys.argv[4]) * 1000) if len(sys.argv) > 4 else 6600000
lo = int(sys.argv[5]) if len(sys.argv) > 5 else 316800  # first gcell boundary at/after 316.8 um (band ends 318)
hi = die - lo
step = 7200
keep = set(l.strip() for l in open(keepf) if l.strip())
out = open(dst, 'w')
cur = None
nb = nn = 0
touched = set()
for ln in open(src):
    p = ln.split()
    if len(p) != 5:
        if len(p) == 1 and p[0] not in '()':
            cur = p[0]
        out.write(ln)
        continue
    x0, y0, x1, y1 = map(int, p[:4])
    if cur in keep:
        out.write(ln)
        continue
    nx0, ny0, nx1, ny1 = x0, y0, x1, y1
    if nx0 < lo:
        nx0 = lo
        if nx1 <= lo:
            nx1 = lo + step
    if nx1 > hi:
        nx1 = hi
        if nx0 >= hi:
            nx0 = hi - step
    if ny0 < lo:
        ny0 = lo
        if ny1 <= lo:
            ny1 = lo + step
    if ny1 > hi:
        ny1 = hi
        if ny0 >= hi:
            ny0 = hi - step
    if (nx0, ny0, nx1, ny1) != (x0, y0, x1, y1):
        nb += 1
        touched.add(cur)
    out.write(f"{nx0} {ny0} {nx1} {ny1} {p[4]}\n")
out.close()
print(f"GUIDE_CLAMP {nb} boxes moved on {len(touched)} nets ({len(keep)} nets kept) -> {dst}")
