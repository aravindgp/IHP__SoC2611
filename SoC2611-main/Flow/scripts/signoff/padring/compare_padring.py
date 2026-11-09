#!/usr/bin/env python3
"""Compare OpenROAD's pad-ring DEF with make_padring.py's GDS.
usage: compare_padring.py padring_openroad.def padring.gds [top]
Pads, corners and bondpads must match exactly (master, DEF lower-left, DEF orientation);
IO fillers are compared as covered area per row (OpenROAD orders filler sizes differently)."""
import re
import sys
from collections import Counter
import klayout.db as db

defp, gdsp = sys.argv[1], sys.argv[2]
top = sys.argv[3] if len(sys.argv) > 3 else 'dgrid_padring'
txt = open(defp).read()
units = int(re.search(r'UNITS DISTANCE MICRONS (\d+)', txt).group(1))
comps = re.search(r'COMPONENTS \d+ ;(.*?)END COMPONENTS', txt, re.S).group(1)
FILLW = {'sg13cmos5l_Filler10000': 50, 'sg13cmos5l_Filler4000': 20, 'sg13cmos5l_Filler2000': 10,
         'sg13cmos5l_Filler1000': 5, 'sg13cmos5l_Filler400': 2, 'sg13cmos5l_Filler200': 1}
SIZE = {'sg13cmos5l_Corner': (180, 180), 'bondpad_70x70': (70, 70)}
ORI = {'N': db.Trans.R0, 'W': db.Trans.R90, 'S': db.Trans.R180, 'E': db.Trans.R270,
       'FN': db.Trans.M90, 'FW': db.Trans.M45, 'FS': db.Trans.M0, 'FE': db.Trans.M135}
INV = {v.rot: k for k, v in ORI.items()}   # fixpoint code 0..7 -> DEF orientation


def size(master):
    if master in FILLW:
        return FILLW[master], 180
    return SIZE.get(master, (80, 180))


d, g = Counter(), Counter()
dfill, gfill = db.Region(), db.Region()
for m in re.finditer(r'-\s+(\S+)\s+(\S+)\s+\+\s+(?:PLACED|FIXED|FIRM)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)', comps):
    inst, master, x, y, ori = m.groups()
    x, y = int(x) * 1000 // units, int(y) * 1000 // units   # nm
    w, h = size(master)
    bb = db.Box(0, 0, w * 1000, h * 1000).transformed(ORI[ori])
    if master in FILLW:
        dfill.insert(bb.moved(x - bb.left, y - bb.bottom))
    else:
        d[(master, x, y, ori)] += 1

ly = db.Layout(); ly.read(gdsp)
assert ly.dbu == 0.001
for inst in ly.cell(top).each_inst():
    c = ly.cell(inst.cell_index)
    if c.name == 'sealring':
        continue
    t = inst.trans
    w, h = size(c.name)
    bb = db.Box(0, 0, w * 1000, h * 1000).transformed(t)
    if c.name in FILLW:
        gfill.insert(bb)
    else:
        g[(c.name, bb.left, bb.bottom, INV[t.rot])] += 1

only_d, only_g = d - g, g - d
fx = (dfill ^ gfill).merged()
print(f'pads/corners/bondpads: DEF {sum(d.values())}, GDS {sum(g.values())}, matched {sum((d & g).values())}')
print(f'IO filler area: DEF {dfill.merged().area() / 1e6:.0f} um2, GDS {gfill.merged().area() / 1e6:.0f} um2, '
      f'XOR {fx.area() / 1e6:.0f} um2')
for k, v in list(only_d.items())[:10]:
    print('  only in DEF:', k, v)
for k, v in list(only_g.items())[:10]:
    print('  only in GDS:', k, v)
ok = not only_d and not only_g and fx.is_empty()
print('PADRING DEF == GDS' if ok else 'PADRING MISMATCH')
sys.exit(0 if ok else 1)
