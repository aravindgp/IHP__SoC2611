#!/usr/bin/env python3
"""XOR one layer of two GDS windows (flattened) and list the differing shapes with the cells they come from.

usage: xor_layer.py <a.gds> <a_top> <b.gds> <b_top> <layer> <datatype> [max_print=20] [min_y_um]
"""
import sys
import klayout.db as db

a, at, b, bt, ln, dt = sys.argv[1:7]
mx = int(sys.argv[7]) if len(sys.argv) > 7 else 20
min_y = float(sys.argv[8]) if len(sys.argv) > 8 else None


def region(path, top):
    ly = db.Layout()
    ly.read(path)
    li = ly.find_layer(int(ln), int(dt))
    c = ly.cell(top)
    r = db.Region(c.begin_shapes_rec(li)) if li is not None else db.Region()
    owners = []
    if li is not None:
        it = c.begin_shapes_rec(li)
        while not it.at_end():
            owners.append((it.shape().bbox().transformed(it.trans()), it.cell().name))
            it.next()
    return r.merged(), owners, ly.dbu


ra, oa, dbu = region(a, at)
rb, ob, _ = region(b, bt)
if min_y is not None:
    win = db.Region(db.Box(-10**9, int(min_y / dbu), 10**9, 10**9))
    ra, rb = ra & win, rb & win
for name, d, owners in (('only in A', ra - rb, oa), ('only in B', rb - ra, ob)):
    print(f'{name}: {d.count()} polygon(s), area {d.area() * dbu * dbu:.3f} um2')
    for p in list(d.each())[:mx]:
        bb = p.bbox()
        src = sorted({n for o, n in owners if o.overlaps(bb) or o.contains(bb.center())})[:4]
        print(f'  {bb.to_dtype(dbu)}  from {src}')
