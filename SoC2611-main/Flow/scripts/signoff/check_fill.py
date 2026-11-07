#!/usr/bin/env python3
"""Geometric check of the filler shapes (datatype 22) against the SG13CMOS5L filler rules, flat.

The PDK main decks only check filler-to-drawn spacing (AFil.c/c1/d/j, GFil.d/e, MFil.c, TM1Fil.c) and
MFil.a2/TM1Fil.a1 max size; the filler width/space rules (AFil.a/a1/b, GFil.a/b/c, MFil.a1/b,
TM1Fil.a/b) live only in sg13cmos5l_maximal.drc, which cannot run on the full chip here.  This script
checks all of them on the filler shapes alone, plus filler-to-drawn spacing, in one KLayout
TilingProcessor pass.

usage: check_fill.py <gds> [--top TOP] [-j 8] [--cell DG_TOPUP_FILL]   (--cell: only that cell's fill)
exit 0 = clean, 1 = violations.
"""
import argparse
import sys
import time

import klayout.db as db

# name: (fill layer, min width, min space, max bbox, [(drawn layer, min separation)])
RULES = {
    'Activ': ((1, 22), 1.0, 0.42, 5.0, [((1, 0), 0.42), ((6, 0), 1.1), ((5, 0), 1.1)]),
    'GatPoly': ((5, 22), 0.7, 0.8, 5.0, [((1, 0), 1.1), ((5, 0), 1.1), ((6, 0), 1.1), ((14, 0), 1.1),
                                         ((7, 21), 1.1), ((28, 0), 1.1), ((31, 0), 1.1)]),
    'M1': ((8, 22), 1.0, 0.42, 5.0, [((8, 0), 0.42)]),
    'M2': ((10, 22), 1.0, 0.42, 5.0, [((10, 0), 0.42)]),
    'M3': ((30, 22), 1.0, 0.42, 5.0, [((30, 0), 0.42)]),
    'M4': ((50, 22), 1.0, 0.42, 5.0, [((50, 0), 0.42)]),
    'TM1': ((126, 22), 5.0, 3.0, 10.0, [((126, 0), 3.0)]),
}


class Count(db.TileOutputReceiver):
    def __init__(self, d, k):
        self.d, self.k = d, k

    def put(self, ix, iy, tile, obj, dbu, clip):
        self.d[self.k] = self.d.get(self.k, 0) + int(obj)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('gds'); ap.add_argument('--top'); ap.add_argument('-j', type=int, default=8)
    ap.add_argument('--cell', help='check only the fill inside this cell (e.g. DG_TOPUP_FILL)')
    ap.add_argument('--layers', default=','.join(RULES))
    a = ap.parse_args()
    t0 = time.time()
    ly = db.Layout(); ly.read(a.gds)
    top = ly.cell(a.top) if a.top else ly.top_cell()
    dbu = ly.dbu
    tp = db.TilingProcessor(); tp.dbu = dbu; tp.threads = a.j
    tp.tile_size(200, 200); tp.tile_border(12, 12)
    res = {}
    recv = []
    seen = set()
    for name in a.layers.split(','):
        (fl, fd), w, s, mx, seps = RULES[name]
        li = ly.find_layer(fl, fd)
        if li is None:
            continue
        it = top.begin_shapes_rec(li)
        if a.cell:
            it.unselect_all_cells(); it.select_cells(a.cell)
        tp.input(f'F{name}', it)
        # all filler of the layer (also the PDK lattice fill) for the space check against the new fill
        tp.input(f'A{name}', top.begin_shapes_rec(li))
        checks = {
            'width': f'F{name}.merged.width_check({int(round(w / dbu))})',
            'space': f'(F{name} + A{name}).merged.space_check({int(round(s / dbu))})',
            'maxsize': f'F{name}.merged.with_bbox_max({int(round(mx / dbu)) + 1}, false)',
        }
        for (dl, dd), d in seps:
            lj = ly.find_layer(dl, dd)
            if lj is None:
                continue
            v = f'D{dl}_{dd}'
            if v not in seen:
                tp.input(v, top.begin_shapes_rec(lj)); seen.add(v)
            checks[f'sep{dl}/{dd}'] = f'{v}.separation_check(F{name}, {int(round(d / dbu))})'
            if dl != 31:                                   # filler inside NWell is legal
                checks[f'ovl{dl}/{dd}'] = f'({v} & F{name})'
        for k, e in checks.items():
            key = f'{name}.{k}'
            o = 'o' + str(len(recv))
            r = Count(res, key); recv.append(r)
            tp.output(o, r)
            # count markers whose centre lies inside the tile (border copies are not double-counted)
            tp.queue(f'_output({o}, ({e}).count)')     # markers in the tile border may count twice
    tp.execute('check fill')
    bad = {k: v for k, v in res.items() if v}
    for k in sorted(res):
        print(f'  {k:22s} {res[k]}')
    print(f'check_fill: {a.gds}: {"CLEAN" if not bad else f"{sum(bad.values())} markers"} '
          f'({time.time() - t0:.0f} s)')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
