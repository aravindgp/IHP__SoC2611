#!/usr/bin/env python3
"""Nets whose ROUTED/FIXED/COVER wiring has a point inside a rectangle (um) on the given layers (default Metal1-4).
usage: def_region_nets.py <chip.def> <out.txt> x0 y0 x1 y1 [layers=Metal1,Metal2,Metal3,Metal4]"""
import re
import sys

deff, out = sys.argv[1:3]
x0, y0, x1, y1 = (float(v) * 1000 for v in sys.argv[3:7])
layers = set((sys.argv[7] if len(sys.argv) > 7 else 'Metal1,Metal2,Metal3,Metal4').split(','))
pt = re.compile(r"\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*(?:-?\d+)?\s*\)")
nets = set()
cur = None
innets = False
lx = ly = None
lay = None
for ln in open(deff, errors='replace'):
    if ln.startswith('NETS'):
        innets = True
        continue
    if ln.startswith('END NETS'):
        break
    if not innets:
        continue
    s = ln.strip()
    if s.startswith('- '):
        cur = s.split()[1]
        continue
    if cur in nets:
        continue
    if s.startswith(('+ ROUTED', '+ FIXED', '+ COVER', 'NEW ')):
        p = s.split()
        lay = p[2] if s.startswith('+') else p[1]
        lx = ly = None
        if lay not in layers:
            continue
        for m in pt.finditer(s):
            px, py = m.group(1), m.group(2)
            px = lx if px == '*' else int(px)
            py = ly if py == '*' else int(py)
            if lx is not None and ((x0 <= px <= x1 and y0 <= py <= y1) or (x0 <= lx <= x1 and y0 <= ly <= y1)
                                   or (min(lx, px) <= x1 and max(lx, px) >= x0 and min(ly, py) <= y1 and max(ly, py) >= y0
                                       and (lx == px or ly == py))):
                nets.add(cur)
                break
            if lx is None and x0 <= px <= x1 and y0 <= py <= y1:
                nets.add(cur)
                break
            lx, ly = px, py
open(out, 'w').write('\n'.join(sorted(nets)) + '\n')
print(f"DEF_REGION {len(nets)} nets touch x {x0/1000:.1f}..{x1/1000:.1f} y {y0/1000:.1f}..{y1/1000:.1f} on {','.join(sorted(layers))} -> {out}")
