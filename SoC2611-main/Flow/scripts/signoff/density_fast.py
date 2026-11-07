#!/usr/bin/env python3
"""Fast density check for IHP SG13CMOS5L: the same numbers as the PDK's density.drc, in minutes.

density.drc (libs.tech/klayout/tech/drc/rule_decks) took 16 h on the full 6.6 mm chip because every
800 um window is a separate deep-mode boolean.  This script computes the same quantities with one
multi-threaded KLayout TilingProcessor pass:

  * layers exactly as the deck builds them:
        Activ   = 1/0 + 1/20 + 1/22            GatPoly = 5/0 + 5/22
        Mn      = (n/0 + n/22) - n/24          for Metal1 (8), Metal2 (10), Metal3 (30), Metal4 (50),
                                               TopMetal1 (126)
  * chip area: prBoundary 189/0 if present, else EdgeSeal.boundary 39/4, else the layout extent;
  * local windows: 800 x 800 um (AFil_g_w / MFil_h_w), step 400 um, base grid origin
    bbox.left + (800 - 400) / 2 in tile-step terms, i.e. windows at 0, 400, ...; plus the deck's
    "backup" top row / right column / corner windows flush with the chip edge
    (with_density_backup in density.drc);
  * rules: AFil.g/g1 (global Activ 35..55 %), AFil.g2/g3 (window Activ 25..65 %), GFil.g (global
    GatPoly >= 15 %), M1.j/k (35..60 %), M2-4.j/k (35..60 %), MnFil.h/k (window M1-M4 25..75 %),
    TM1.c/d (global TopMetal1 25..70 %).  Limits are read from the deck's JSON (tech_mod over default).

The merged layer area is computed per grid cell (the GCD of all window edges, 200 um on the 6.6 mm
die) and summed per window; merged area is additive over disjoint cells, so this is exact.

Attribution (--attrib): per cell it also measures the fill share (datatype 22) and the area inside
macro instances (cells matching --macros, default RM_IHPSG13_.*), so every window can be split into
macro / non-macro / fill contributions.

usage: density_fast.py <gds> [--top TOP] [-j 12] [--json out.json] [--csv windows.csv] [--attrib]
                       [--ref density.lyrdb]       # compare with a PDK density.drc report
exit code: 0 = all density rules pass, 1 = violations.
"""
import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import klayout.db as db

TECH = Path(os.environ.get('KLAYOUT_TECH', '/workspace/dgrid_658ac326/tmp/pdk_root/'
                           'ihp-sg13cmos5l/libs.tech/klayout/tech'))

# name: (positive (layer, dt) list, subtracted list)
LAYERS = {
    'Activ': ([(1, 0), (1, 20), (1, 22)], []),
    'GatPoly': ([(5, 0), (5, 22)], []),
    'Metal1': ([(8, 0), (8, 22)], [(8, 24)]),
    'Metal2': ([(10, 0), (10, 22)], [(10, 24)]),
    'Metal3': ([(30, 0), (30, 22)], [(30, 24)]),
    'Metal4': ([(50, 0), (50, 22)], [(50, 24)]),
    'TopMetal1': ([(126, 0), (126, 22)], [(126, 24)]),
}
SHORT = {'Activ': 'A', 'GatPoly': 'G', 'Metal1': 'M1', 'Metal2': 'M2', 'Metal3': 'M3', 'Metal4': 'M4',
         'TopMetal1': 'TM1'}


def drc_rules():
    d = json.loads((TECH / 'drc/rule_decks/sg13cmos5l_tech_default.json').read_text())['drc_rules']
    p = TECH.parent / 'python/sg13cmos5l_pycell_lib/sg13cmos5l_tech_mod.json'
    if p.exists():
        d.update(json.loads(p.read_text()).get('drc_rules', {}))
    return d


def rule_table(r):
    """(rule, layer, kind, lo, hi): kind 'g' global / 'w' window; violation if ratio < lo or > hi."""
    t = [('AFil.g', 'Activ', 'g', r['AFil_g'], None), ('AFil.g1', 'Activ', 'g', None, r['AFil_g1']),
         ('AFil.g2', 'Activ', 'w', r['AFil_g2'], None), ('AFil.g3', 'Activ', 'w', None, r['AFil_g3']),
         ('GFil.g', 'GatPoly', 'g', r['GFil_g'], None),
         ('M1.j', 'Metal1', 'g', r['M1_j'], None), ('M1.k', 'Metal1', 'g', None, r['M1_k'])]
    for n in (2, 3, 4):
        t += [(f'M{n}.j', f'Metal{n}', 'g', r['Mn_j'], None), (f'M{n}.k', f'Metal{n}', 'g', None, r['Mn_k'])]
    for n in (1, 2, 3, 4):
        t += [(f'M{n}Fil.h', f'Metal{n}', 'w', r['MFil_h'], None),
              (f'M{n}Fil.k', f'Metal{n}', 'w', None, r['MFil_k'])]
    t += [('TM1.c', 'TopMetal1', 'g', r['TM1_c'], None), ('TM1.d', 'TopMetal1', 'g', None, r['TM1_d'])]
    return t


def deck_windows(bbox, size, step):
    """Window lower-left corners exactly as density.drc with_density_backup() builds them (um)."""
    w, h = bbox.width(), bbox.height()
    ox = bbox.left + ((size - step) / 2 if w >= size else 0)
    oy = bbox.bottom + ((size - step) / 2 if h >= size else 0)
    nx = max(1 + math.floor((w - size) / step), 1)
    ny = max(1 + math.floor((h - size) / step), 1)
    # the tiling origin is the centre-cell origin; the window = step tile + (size-step)/2 border
    brd = (size - step) / 2
    xs = [ox + i * step - brd for i in range(nx)]
    ys = [oy + j * step - brd for j in range(ny)]
    wins = {(x, y) for x in xs for y in ys}
    need_top = h > size + (ny - 1) * step
    need_right = w > size + (nx - 1) * step
    top_y = oy + max(h - size, 0) - brd
    right_x = ox + max(w - size, 0) - brd
    if need_top:
        for i in range(max(2, nx)):
            wins.add((ox + i * step - brd, top_y))
    if need_right:
        for j in range(max(2, ny)):
            wins.add((right_x, oy + j * step - brd))
    if (need_top and w > size) or (need_right and h > size):
        for j in range(2):
            wins.add((right_x, top_y + j * step))
    out = []
    for x, y in sorted(wins):
        b = db.DBox(x, y, x + size, y + size) & bbox     # tile_boundary + select_inside(chip bbox)
        if not b.empty() and b.width() > 0 and b.height() > 0 and \
                x >= bbox.left - 1e-6 and y >= bbox.bottom - 1e-6 and \
                x + size <= bbox.right + 1e-6 and y + size <= bbox.top + 1e-6:
            out.append(b)
    return out


class Recv(db.TileOutputReceiver):
    def __init__(self, store, key):
        self.store, self.key = store, key

    def put(self, ix, iy, tile, obj, dbu, clip):
        self.store[(self.key, ix, iy)] = float(obj) * dbu * dbu


def chip_region(ly, top):
    for ln, dt, name in ((189, 0, 'prBoundary'), (39, 4, 'EdgeSeal.boundary')):
        li = ly.find_layer(ln, dt)
        if li is not None:
            r = db.Region(top.begin_shapes_rec(li)).merged()
            if not r.is_empty():
                return r, name
    return db.Region(top.bbox()), 'extent'


def macro_region(ly, top, pattern):
    """Outlines of the macro instances placed directly in the top cell (DEF-streamed chips are flat)."""
    rx = re.compile(pattern)
    reg = db.Region()
    n = 0
    for inst in top.each_inst():
        c = inst.cell
        if rx.match(c.name):
            for t in inst.cell_inst.each_trans():
                reg.insert(c.bbox().transformed(t))
                n += 1
    return reg.merged(), n


def macro_instances(ly, top, pattern):
    rx = re.compile(pattern)
    out = []
    for inst in top.each_inst():
        if rx.match(inst.cell.name):
            for t in inst.cell_inst.each_trans():
                out.append((inst.cell.cell_index(), t))
    return out


def layer_region(ly, it_factory, name):
    """Merged deck layer from an iterator factory it_factory(layer_index) -> RecursiveShapeIterator."""
    pos, neg = LAYERS[name]
    p, n = db.Region(), db.Region()
    for lst, reg in ((pos, p), (neg, n)):
        for ln, dt in lst:
            li = ly.find_layer(ln, dt)
            if li is not None:
                reg.insert(it_factory(li))
    return (p - n) if not n.is_empty() else p.merged()


_G = {}   # fork-shared state for the macro workers


def _macro_job(job):
    """Area of one deck layer of one macro master, per global grid cell, for every instance of it.
    Subtracts the overlap with the non-macro shapes (routing on macro pins) so the sum stays exact."""
    ci, name = job
    ly, top, insts, macro_cis, cell, ox, oy = (_G[k] for k in ('ly', 'top', 'insts', 'macro_cis', 'cell', 'ox', 'oy'))
    c = ly.cell(ci)
    master = layer_region(ly, lambda li: c.begin_shapes_rec(li), name)
    mb = c.bbox()
    res = {}
    for ici, t in insts:
        if ici != ci:
            continue
        ti = t.inverted()
        g0 = ti * db.Point(ox, oy)                       # global grid origin in master coordinates
        x0 = g0.x + ((mb.left - g0.x) // cell) * cell
        y0 = g0.y + ((mb.bottom - g0.y) // cell) * cell
        nxp = -(-(mb.right - x0) // cell); nyp = -(-(mb.top - y0) // cell)
        gb = mb.transformed(t)

        def nonmac(li, gb=gb):
            it = top.begin_shapes_rec_touching(li, gb)
            it.unselect_cells(macro_cis)
            return it
        ovl = (layer_region(ly, nonmac, name) & db.Region(gb)).transformed(ti) & master
        ras = master.rasterize(db.Point(x0, y0), db.Vector(cell, cell), nxp, nyp)
        rov = ovl.rasterize(db.Point(x0, y0), db.Vector(cell, cell), nxp, nyp) if not ovl.is_empty() else None
        for j in range(nyp):
            for i in range(nxp):
                a = ras[j][i] - (rov[j][i] if rov else 0.0)
                if a == 0:
                    continue
                ctr = t * db.Point(x0 + i * cell + cell // 2, y0 + j * cell + cell // 2)
                k = ((ctr.x - ox) // cell, (ctr.y - oy) // cell)
                res[k] = res.get(k, 0.0) + a
    return name, res


def run(gds, top_name=None, threads=12, attrib=False, macros='RM_IHPSG13_.*', layers=None, quiet=False,
        macro_split=True):
    """macro_split: macros (hard macros, e.g. SRAMs) are measured once per master and instance from
    their own merged shapes (hierarchically, in -j processes) instead of being flattened in every tile;
    the tiles then only see the non-macro shapes.  Exact: merged(all) = nonmac + mac - (nonmac & mac)."""
    t0 = time.time()
    ly = db.Layout()
    ly.read(gds)
    top = ly.cell(top_name) if top_name else ly.top_cell()
    dbu = ly.dbu
    t_read = time.time() - t0
    chip, chip_src = chip_region(ly, top)
    chip_area = chip.area() * dbu * dbu
    cb = chip.bbox().to_dtype(dbu)
    r = drc_rules()
    rules = rule_table(r)
    wsize = r['MFil_h_w']
    assert r['AFil_g_w'] == wsize, 'Activ and metal window sizes differ; extend the script'
    wins = deck_windows(cb, wsize, 0.5 * wsize)
    edges_x = {round(b.left - cb.left, 6) for b in wins} | {round(b.right - cb.left, 6) for b in wins} | {cb.width()}
    edges_y = {round(b.bottom - cb.bottom, 6) for b in wins} | {round(b.top - cb.bottom, 6) for b in wins} | {cb.height()}
    g = 0
    for e in edges_x | edges_y:
        g = math.gcd(g, int(round(e / dbu)))
    while g > 200000 and g % 2 == 0:      # >= 2x2 tiles (a single tile means "no tiling": _tile = nil)
        g //= 2
    cell = g * dbu
    nx, ny = int(round(cb.width() / cell)), int(round(cb.height() / cell))

    tp = db.TilingProcessor()
    tp.dbu = dbu
    tp.tile_origin(cb.left, cb.bottom)
    tp.tile_size(cell, cell)
    tp.tiles(nx, ny)
    tp.threads = threads
    tp.var('chip', chip)
    store = {}
    receivers = []
    names = layers or list(LAYERS)
    mreg = None
    insts = macro_instances(ly, top, macros) if macros else []
    macro_cis = sorted({ci for ci, _ in insts})
    split = macro_split and bool(insts)
    if attrib or split:
        mreg, nmac = macro_region(ly, top, macros)
        tp.var('mac', mreg)
    for name in names:
        pos, neg = LAYERS[name]
        terms = []
        for ln, dt in pos + neg:
            li = ly.find_layer(ln, dt)
            v = f'L{ln}_{dt}'
            if li is None:
                continue
            it = top.begin_shapes_rec(li)
            if split:
                it.unselect_cells(macro_cis)
            tp.input(v, it)
            terms.append(((ln, dt) in pos, (ln, dt), v))
        p = [v for isp, _, v in terms if isp]
        n = [v for isp, _, v in terms if not isp]
        if not p:
            expr = 'Region.new()'
        else:
            expr = '(' + ' + '.join(p) + ')'
            if n:
                expr = f'({expr} - ({" + ".join(n)}))'
        key = SHORT[name]
        outs = [(key, f'({expr} & _tile & chip).area')]
        if attrib:
            fl = [v for isp, ld, v in terms if isp and ld[1] == 22]
            if fl:
                outs += [(key + '_f', f'(({" + ".join(fl)}) & _tile & chip).area')]
            if not split:
                outs += [(key + '_m', f'({expr} & _tile & chip & mac).area')]
        for k, e in outs:
            rc = Recv(store, k)
            receivers.append(rc)
            tp.output(k, rc)
            tp.queue(f'_output({k}, {e})')
    if attrib:
        rc = Recv(store, 'macarea')
        receivers.append(rc)
        tp.output('macarea', rc)
        tp.queue('_output(macarea, (_tile & chip & mac).area)')
    rc = Recv(store, 'cellarea')
    receivers.append(rc)
    tp.output('cellarea', rc)
    tp.queue('_output(cellarea, (_tile & chip).area)')
    t1 = time.time()
    tp.execute('density')
    t_tp = time.time() - t1
    t_mac = 0.0
    if split:
        import multiprocessing as mp
        t2 = time.time()
        ox, oy = int(round(cb.left / dbu)), int(round(cb.bottom / dbu))
        _G.update(ly=ly, top=top, insts=insts, macro_cis=macro_cis, cell=int(round(cell / dbu)), ox=ox, oy=oy)
        jobs = [(ci, n) for ci in macro_cis for n in names]
        jobs.sort(key=lambda j: -ly.cell(j[0]).bbox().area())          # big masters first
        with mp.get_context('fork').Pool(threads) as pool:
            for name, res in pool.imap_unordered(_macro_job, jobs):
                k = SHORT[name]
                for (i, j), a in res.items():
                    a *= dbu * dbu
                    store[(k, i, j)] = store.get((k, i, j), 0.0) + a
                    store[(k + '_m', i, j)] = store.get((k + '_m', i, j), 0.0) + a
        t_mac = time.time() - t2

    def wsum(key, b):
        i0 = int(round((b.left - cb.left) / cell)); i1 = int(round((b.right - cb.left) / cell))
        j0 = int(round((b.bottom - cb.bottom) / cell)); j1 = int(round((b.top - cb.bottom) / cell))
        return sum(store.get((key, i, j), 0.0) for i in range(i0, i1) for j in range(j0, j1))

    res = {'gds': str(gds), 'top': top.name, 'chip_source': chip_src, 'chip_area_um2': chip_area,
           'cell_um': cell, 'n_windows': len(wins), 'time_read_s': round(t_read, 1),
           'time_tiles_s': round(t_tp, 1), 'time_macros_s': round(t_mac, 1), 'macro_split': split, 'threads': threads, 'global': {}, 'windows': [], 'violations': []}
    for name in names:
        k = SHORT[name]
        a = sum(v for (kk, _, _), v in store.items() if kk == k)
        res['global'][name] = {'area_um2': a, 'ratio': a / chip_area}
        if attrib:
            for suf, lab in (('_m', 'in_macros_um2'), ('_f', 'fill_um2')):
                res['global'][name][lab] = sum(v for (kk, _, _), v in store.items() if kk == k + suf)
            res['global'][name]['macro_outline_um2'] = sum(v for (kk, _, _), v in store.items() if kk == 'macarea')
    for b in wins:
        wa = wsum('cellarea', b)
        row = {'bbox': [b.left, b.bottom, b.right, b.top], 'area_um2': wa}
        for name in names:
            k = SHORT[name]
            row[k] = wsum(k, b) / wa
            if attrib:
                row[k + ':fill'] = wsum(k + '_f', b) / wa
                row[k + ':mac'] = wsum(k + '_m', b) / wa
        if attrib:
            row['mac_frac'] = wsum('macarea', b) / wa
        res['windows'].append(row)
    for rule, lname, kind, lo, hi in rules:
        if lname not in names:
            continue
        k = SHORT[lname]
        if kind == 'g':
            v = res['global'][lname]['ratio']
            if (lo is not None and v < lo) or (hi is not None and v > hi):
                res['violations'].append({'rule': rule, 'ratio': v, 'limit': lo if lo is not None else hi})
        else:
            for w in res['windows']:
                v = w[k]
                if (lo is not None and v < lo) or (hi is not None and v > hi):
                    res['violations'].append({'rule': rule, 'ratio': v, 'limit': lo if lo is not None else hi,
                                              'bbox': w['bbox']})
    res['rules'] = [list(x) for x in rules if x[1] in names]
    res['time_total_s'] = round(time.time() - t0, 1)
    return res


def summary(res):
    L = [f"density_fast: {res['gds']} top={res['top']} chip={res['chip_source']} "
         f"{res['chip_area_um2']:.0f} um2, {res['n_windows']} windows/layer, grid {res['cell_um']:g} um, "
         f"read {res['time_read_s']} s + tiles {res['time_tiles_s']} s + macros {res.get('time_macros_s', 0)} s ({res['threads']} threads)"]
    L.append('global: ' + '  '.join(f"{n} {v['ratio'] * 100:.3f}%" for n, v in res['global'].items()))
    per = {}
    for v in res['violations']:
        per.setdefault(v['rule'], []).append(v['ratio'])
    for rule, lname, kind, lo, hi in res['rules']:
        k = SHORT[lname]
        if kind == 'w':
            vals = [w[k] for w in res['windows']]
            ext = f"window min {min(vals) * 100:.2f}% max {max(vals) * 100:.2f}%"
        else:
            ext = f"global {res['global'][lname]['ratio'] * 100:.3f}%"
        lim = f">= {lo * 100:g}%" if lo is not None else f"<= {hi * 100:g}%"
        v = per.get(rule, [])
        st = 'PASS' if not v else f"FAIL x{len(v)} ({min(v) * 100:.2f}-{max(v) * 100:.2f}%)"
        L.append(f"  {rule:9s} {lim:8s} {ext:36s} {st}")
    L.append(f"TOTAL {len(res['violations'])} density violations")
    return '\n'.join(L)


def parse_lyrdb(path):
    t = Path(path).read_text()
    out = []
    for it in re.findall(r'<item>.*?</item>', t, re.S):
        cat = re.search(r"<category>'?([^<']*)'?</category>", it).group(1)
        m = re.search(r'window_bbox_um\s*: \(([-\d.]+),([-\d.]+)\) - \(([-\d.]+),([-\d.]+)\)', it)
        rr = re.search(r'ratio_percent\s*: ([\d.]+)', it)
        out.append((cat, tuple(round(float(x), 3) for x in m.groups()) if m else None,
                    float(rr.group(1)) if rr else None))
    return out


def compare(res, ref):
    mine = {(v['rule'], tuple(round(x, 3) for x in v['bbox']) if 'bbox' in v else None): v['ratio'] * 100
            for v in res['violations']}
    theirs = {(c, b): r for c, b, r in parse_lyrdb(ref)}
    only_m = sorted(set(mine) - set(theirs), key=str)
    only_t = sorted(set(theirs) - set(mine), key=str)
    both = set(mine) & set(theirs)
    dif = [abs(mine[k] - theirs[k]) for k in both if theirs[k] is not None]
    L = [f"compare vs {ref}: {len(both)} common, {len(only_m)} only here, {len(only_t)} only in lyrdb; "
         f"max |ratio diff| {max(dif) if dif else 0:.4f} %-points"]
    L += [f"  only here: {k} {mine[k]:.3f}%" for k in only_m]
    L += [f"  only lyrdb: {k} {theirs[k]}" for k in only_t]
    return '\n'.join(L), not only_m and not only_t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('gds')
    ap.add_argument('--top')
    ap.add_argument('-j', type=int, default=12)
    ap.add_argument('--json')
    ap.add_argument('--csv', help='per-window ratios')
    ap.add_argument('--attrib', action='store_true', help='also fill share and macro share per window')
    ap.add_argument('--macros', default='RM_IHPSG13_.*', help='hard-macro cells (regex; "" = none)')
    ap.add_argument('--no-macro-split', action='store_true',
                    help='flatten the macros in every tile too (slow reference mode, ~1 h on the full chip)')
    ap.add_argument('--layers', help='comma list subset of ' + ','.join(LAYERS))
    ap.add_argument('--ref', help='PDK density.drc lyrdb to compare against')
    a = ap.parse_args()
    res = run(a.gds, a.top, a.j, a.attrib, a.macros, a.layers.split(',') if a.layers else None,
              macro_split=not a.no_macro_split)
    print(summary(res))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
    if a.csv:
        keys = [k for k in res['windows'][0] if k not in ('bbox',)]
        with open(a.csv, 'w') as f:
            f.write('x0,y0,x1,y1,' + ','.join(keys) + '\n')
            for w in res['windows']:
                f.write(','.join(f'{x:g}' for x in w['bbox']) + ',' + ','.join(f'{w[k]:.5f}' for k in keys) + '\n')
    if a.ref:
        txt, same = compare(res, a.ref)
        print(txt)
    sys.exit(1 if res['violations'] else 0)


if __name__ == '__main__':
    main()
