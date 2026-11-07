#!/usr/bin/env python3
"""Density top-up fill for IHP SG13CMOS5L, run AFTER fill_tiled.py (the PDK lattice fill).

Why: the PDK fill recipes place fixed-size squares on a fixed lattice (Metal 3.5x3.5/4x4 um at
5/6 um pitch, else 1x1 um at 2.5 um pitch; Activ 3.4x3.4 at 5 um).  Between routed wires and std-cell
rows the free space is irregular, so most of it stays empty: on the rehearsal chip 212 density windows
failed (MnFil.h, AFil.g2) plus the global M2.j and GFil.g.  This script fills what the lattice left,
with shapes that follow the free space:

  free  = seal-ring interior - macro outlines (--macros, never fill inside the SRAMs)
          - every exclusion of the PDK recipe for that layer (drawn shapes sized by the rule distance,
            existing filler sized by the filler space, nofill / NoMetFiller, NWell/PWell:block edge bands)
  free -= cut grid (lines of the filler space, every --pitch um)  -> each piece fits in pitch-space um
  fill  = opening of free by the min. filler width (size(-w/2).size(+w/2))  -> width >= min width;
          pieces with any Euclidean width/space/notch marker left (staircases) are dropped

Rules (SG13CMOS5L layout rules rev 0.1 + KLayout decks):
  Metal(n) 1-4 filler: width 1.0..5.0 (MFil.a1/a2), space 0.42 (MFil.b), to Metal(n) 0.42 (MFil.c).
  Activ filler: width 1.0..5.0, space 0.42, to Activ 0.42 (used: 1.1, covers Cont on Activ), to
                Cont/GatPoly 1.1, to NWell edge 1.0, to PWell:block edge 1.5 (AFil.a/a1/b/c/c1/d/i).
  TopMetal1 filler: width 5..10, space 3.0, to TopMetal1 3.0 (TM1Fil.a/a1/b/c); cut grid 13 um.
  GatPoly filler: width 0.7..5.0, space 0.8, to Activ/GatPoly/Cont/pSD/nSD:block/SalBlock 1.1,
                  to NWell edge 1.1 (GFil.a/b/c/d/e).  New GatPoly fill also keeps 0.2 um off Activ:filler
                  (no partial overlap -> GFil.j end cap cannot be violated).
All distances get +10 nm margin.  Every piece is axis-parallel (Manhattan) on the 5 nm grid.
Macro outlines (--macros) are kept free on Activ/GatPoly/M1-M4 with the layer's largest rule distance
and their internals are not read at all (SRAMs: 38-47 % dense on every layer they use, no fill rule
allows filling inside them); TopMetal1 is filled over them (the RM_IHPSG13 SRAMs have no TM1).

Implementation: one KLayout TilingProcessor pass (multi-threaded, hierarchical input read once).
Tile edges sit on the cut-grid lines, so no piece is split by a tile edge.  New shapes go into a cell
DG_TOPUP_FILL (datatype 22 of each layer) instantiated in the top cell.

usage: fill_topup.py <in_filled.gds> <out.gds> [--layers M1,M2,M3,M4,TM1,Activ,GatPoly] [-j 12]
                     [--macros 'RM_IHPSG13_.*'] [--pitch 5.0] [--tile 520] [--top TOP]
                     [--fill-only fill.gds]
Verify: check_fill.py <out> (filler width/space/size), density_fast.py <out> (all density rules).
Rehearsal chip (2 Nov): 23 min at -j 12 next to the DRT, 4.2 GB, 3.9 M shapes, GDS 0.82 -> 1.13 GB.
"""
import argparse
import math
import time
from pathlib import Path

import klayout.db as db

M = 0.01   # margin added to every rule distance (um)

# block entries: (layer, dt, distance_um, mode)   mode 'size' = shape sized by distance,
#                                                  'band' = edge band +-distance (NWell, PWell:block)
SPECS = {
    'Activ': dict(target=(1, 22), width=1.0, space=0.42, block=[
        # Cont (10^8 shapes in the std cells) is not read: every contact sits on Activ or GatPoly
        # (Cnt.c/d enclosure), so Activ and GatPoly sized by 1.1 (AFil.c) cover it.
        (1, 0, 1.1, 'size'), (1, 20, 0.42, 'size'), (1, 22, 0.42, 'size'),
        (5, 0, 1.1, 'size'), (5, 22, 0.42, 'size'), (1, 23, 0.0, 'size'),
        (31, 0, 1.0, 'band'), (46, 21, 1.5, 'band')]),
    'GatPoly': dict(target=(5, 22), width=0.7, space=0.8, block=[
        (1, 0, 1.1, 'size'), (5, 0, 1.1, 'size'), (14, 0, 1.1, 'size'),        # Cont: see Activ
        (7, 21, 1.1, 'size'), (28, 0, 1.1, 'size'), (5, 22, 0.8, 'size'), (1, 22, 0.2, 'size'),
        (5, 23, 0.0, 'size'), (31, 0, 1.1, 'band')]),
}
for _n, _l in (('M1', 8), ('M2', 10), ('M3', 30), ('M4', 50)):
    SPECS[_n] = dict(target=(_l, 22), width=1.0, space=0.42, block=[
        (_l, 0, 0.42, 'size'), (_l, 22, 0.42, 'size'), (_l, 24, 0.42, 'size'), (_l, 23, 0.0, 'size'),
        (160, 0, 0.0, 'size')])
# TopMetal1 filler: width 5..10 (TM1Fil.a/a1), space 3.0 (TM1Fil.b), to TopMetal1 3.0 (TM1Fil.c).
# The RM_IHPSG13 SRAMs have no TopMetal1 (GDS and LEF), and the PDK TM1 recipe already fills over them,
# so TM1 is the one layer that may be filled over the macro outlines (over_macros).
SPECS['TM1'] = dict(target=(126, 22), width=5.0, space=3.0, pitch=13.0, over_macros=True, block=[
    (126, 0, 3.0, 'size'), (126, 22, 3.0, 'size'), (126, 24, 3.0, 'size'), (126, 23, 0.0, 'size'),
    (160, 0, 0.0, 'size')])


def seal_frame(ly, top):
    li = ly.find_layer(39, 0)
    es = db.Region(top.begin_shapes_rec(li)).merged() if li is not None else db.Region()
    if es.is_empty():          # clip / test layouts without a seal ring: fill the whole extent
        print('[topup] WARNING: no EdgeSeal (39/0); filling the layout bbox (test clips only)')
        return db.Region(top.bbox())
    frame = db.Region()
    for p in es.each():
        for h in range(p.holes()):
            frame.insert(db.Polygon(list(p.each_point_hole(h))))
    if frame.is_empty():       # clip with an open piece of seal ring: everything off the ring
        print('[topup] WARNING: EdgeSeal has no hole; filling bbox - EdgeSeal (test clips only)')
        return db.Region(top.bbox()) - es
    return frame.merged()


def macro_outlines(ly, top, pattern):
    import re
    rx = re.compile(pattern)
    reg = db.Region()
    for inst in top.each_inst():
        if rx.match(inst.cell.name):
            for t in inst.cell_inst.each_trans():
                reg.insert(inst.cell.bbox().transformed(t))
    return reg.merged()


def cut_grid(box, pitch, gap):
    """Lines of width gap centred on every multiple of pitch (dbu), covering box."""
    g = db.Region()
    h = gap // 2
    x = (box.left // pitch) * pitch
    while x <= box.right + pitch:
        g.insert(db.Box(x - h, box.bottom - pitch, x + gap - h, box.top + pitch))
        x += pitch
    y = (box.bottom // pitch) * pitch
    while y <= box.top + pitch:
        g.insert(db.Box(box.left - pitch, y - h, box.right + pitch, y + gap - h))
        y += pitch
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input'); ap.add_argument('output')
    ap.add_argument('--top')
    ap.add_argument('--layers', default='M1,M2,M3,M4,TM1,Activ,GatPoly')
    ap.add_argument('--macros', default='RM_IHPSG13_.*', help='cells whose outline is never filled ("" = none)')
    ap.add_argument('--pitch', type=float, default=5.0,
                    help='cut-grid pitch for Activ/GatPoly/M1-M4 = max. piece size + space (<= 5.4); TM1 uses 13')
    ap.add_argument('--tile', type=float, default=520.0, help='tile size (um, multiple of every pitch)')
    ap.add_argument('-j', type=int, default=12)
    ap.add_argument('--fill-only', help='also write only the new fill (top + DG_TOPUP_FILL) to this GDS')
    ap.add_argument('--shrink', default='', help='LAYER=um,... pull the new pieces back from the free-space edge by um '
                    '(less fill; e.g. M4=0.5 if M4.k / M4Fil.k (max 60 / 75 %%) would fail)')
    a = ap.parse_args()
    t0 = time.time()
    ly = db.Layout(); ly.read(a.input)
    top = ly.cell(a.top) if a.top else ly.top_cell()
    dbu = ly.dbu
    print(f'[topup] read {a.input} in {time.time() - t0:.0f} s', flush=True)
    frame = seal_frame(ly, top)
    mac = macro_outlines(ly, top, a.macros) if a.macros else db.Region()
    import re
    rx = re.compile(a.macros) if a.macros else None
    # The macro interiors are never filled, so their (flattened: 10^8-10^9 polygons) shapes are not read at
    # all; instead the outline is kept out by the largest rule distance of the layer.
    macro_cis = sorted({i.cell.cell_index() for i in top.each_inst() if rx and rx.match(i.cell.name)})
    print(f'[topup] frame {frame.bbox().to_dtype(dbu)}, macro outlines {mac.count()} '
          f'({mac.area() * dbu * dbu / 1e6:.2f} mm2)', flush=True)
    names = [n.strip() for n in a.layers.split(',') if n.strip()]
    shrink = {k: float(v) for k, v in (x.split('=') for x in a.shrink.split(',') if x)}
    pitches = {n: int(round(SPECS[n].get('pitch', a.pitch) / dbu)) for n in names}
    lcm = 1
    for p in pitches.values():
        lcm = lcm * p // math.gcd(lcm, p)
    tile = int(round(a.tile / dbu))
    assert tile % lcm == 0, f'--tile must be a multiple of {lcm * dbu:g} um (all cut-grid pitches)'
    fb = frame.bbox()
    ox = (fb.left // lcm) * lcm      # tile edges lie on every layer's cut-grid lines
    oy = (fb.bottom // lcm) * lcm
    nx = -(-(fb.right - ox) // tile); ny = -(-(fb.top - oy) // tile)

    out = db.Layout(); out.dbu = dbu
    otop = out.create_cell(top.name)
    ofill = out.create_cell('DG_TOPUP_FILL')
    otop.insert(db.CellInstArray(ofill.cell_index(), db.Trans()))

    tp = db.TilingProcessor()
    tp.dbu = dbu
    tp.tile_origin(ox * dbu, oy * dbu)
    tp.tile_size(tile * dbu, tile * dbu)
    tp.tiles(nx, ny)
    tp.tile_border(6.0, 6.0)
    tp.threads = a.j
    tp.var('frame', frame)
    seen = set()
    keep = []
    for name in names:
        sp = SPECS[name]
        gap = int(round((sp['space'] + M) / dbu / 2)) * 2      # even, 5 nm grid when space+M is
        keep.append(cut_grid(fb, pitches[name], gap))   # the processor does not own var objects
        tp.var(f'grid_{name}', keep[-1])
        terms = []
        for ln, dt, d, mode in sp['block']:
            v = f'L{ln}_{dt}'
            li = ly.find_layer(ln, dt)
            if li is None:
                continue
            if v not in seen:
                it = top.begin_shapes_rec(li)
                if macro_cis:
                    it.unselect_cells(macro_cis)
                tp.input(v, it)
                seen.add(v)
            dd = int(round((d + M) / dbu)) if d > 0 else 0
            if mode == 'band':
                terms.append(f'({v}.sized({dd}) - {v}.sized({-dd}))')
            else:
                terms.append(f'{v}.sized({dd})' if dd else v)
        blk = ' + '.join(terms) if terms else 'Region.new()'
        h = int(round(sp['width'] / dbu / 2))
        shr = int(round(shrink.get(name, 0.0) / dbu / 5)) * 5       # 5 nm grid
        tl = out.layer(*sp['target'])
        tp.output(f'o_{name}', out, ofill.cell_index(), tl)
        dmax = int(round((max(d for _, _, d, _ in sp['block']) + M) / dbu))
        keep.append(mac.sized(dmax))
        tp.var(f'mac_{name}', keep[-1])
        nomac = '' if sp.get('over_macros') else f' - mac_{name}'
        # The opening guarantees the min. width only in the square (Chebyshev) metric; staircase pieces
        # can be narrower diagonally, and a removed neck can leave two parts closer than the space.
        # Every piece that has a Euclidean width / space / notch marker is dropped.
        wd = int(round(sp['width'] / dbu))
        sd = int(round(sp['space'] / dbu))
        tp.queue(f'var free = (_tile & frame){nomac} - ({blk}) - grid_{name}; '
                 f'var r = free.sized({-h - shr}).sized({h}) & _tile; '
                 f'var bad = r.width_check({wd}).polygons(1) + r.space_check({sd}).polygons(1); '
                 f'_output(o_{name}, r - r.interacting(bad))')
    t1 = time.time()
    tp.execute('density top-up fill')
    print(f'[topup] tiles ({nx}x{ny} of {a.tile:g} um, {a.j} threads) in {time.time() - t1:.0f} s', flush=True)
    for name in names:
        li = out.find_layer(*SPECS[name]['target'])
        r = db.Region(ofill.shapes(li))
        print(f'[topup]   {name:8s} {SPECS[name]["target"]}: {r.count():9d} shapes '
              f'{r.area() * dbu * dbu / 1e6:8.3f} mm2 added', flush=True)
    tmp = Path(a.fill_only) if a.fill_only else Path(a.output).with_suffix('.topup_only.gds')
    out.write(str(tmp))
    ly.read(str(tmp))          # merges: same top name -> DG_TOPUP_FILL instance added to the top
    ly.write(a.output)
    if not a.fill_only:
        tmp.unlink()
    print(f'[topup] wrote {a.output}; total {time.time() - t0:.0f} s', flush=True)


if __name__ == '__main__':
    main()
