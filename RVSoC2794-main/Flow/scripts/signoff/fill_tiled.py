#!/usr/bin/env python3
"""Tiled density fill for IHP SG13CMOS5L with the PDK's own fill recipes.

The PDK's batch fill (libs.tech/klayout/tech/scripts/filler.py running the
sg13cmos5l_filler_{ActGatP,Metal}.lym DRC macros flat on the whole layout) needed >9 GB on the
empty 6.6 mm pad-ring frame (killed).  This driver runs the SAME macro bodies tile by tile:

  * each tile is a separate `klayout -b` process: input clipped to tile + margin (exclusions
    that size shapes by <= 1.5 um see their neighbours), fill region restricted to the tile
    (EdgeSeal.holes -> TILE = seal-ring interior & tile), fill lattice anchored at the global origin so
    tiles join seamlessly;
  * each tile writes only its fill cells/instances; the tiles are merged into the input layout
    (same fill-cell names -> one cell each) and written to the output GDS.

usage: fill_tiled.py <in.gds> <out.gds> [--top TOP] [--tile 1000] [--margin 20] [-j 2]
                     [--no-activ] [--no-metal] [--keep]
Run from python3 (klayout.db module) with `klayout` on PATH; env from signoff/env.sh.
"""
import argparse
import concurrent.futures as cf
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import klayout.db as db

TECH = Path(os.environ.get('KLAYOUT_TECH', '/root/.claude/jobs/658ac326/tmp/pdk_root/'
                           'ihp-sg13cmos5l/libs.tech/klayout/tech'))
MACROS = {'ActGatP': TECH / 'macros' / 'sg13cmos5l_filler_ActGatP.lym',
          'Metal': TECH / 'macros' / 'sg13cmos5l_filler_Metal.lym'}


def macro_body(path):
    txt = Path(path).read_text()
    body = re.search(r'<text>(.*)</text>', txt, re.S).group(1)
    for a, b in (('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'), ('&apos;', "'"), ('&amp;', '&')):
        body = body.replace(a, b)
    n = body.count('EdgeSeal.holes')
    assert n >= 1, f'{path}: no EdgeSeal.holes to restrict'
    return body.replace('EdgeSeal.holes', 'TILE'), n


def tile_script(bodies, box, margin, frame, dbu):
    """frame: db.Region (dbu) = inside of the seal ring (EdgeSeal.holes of the whole chip)."""
    x1, y1, x2, y2 = box
    n = lambda v: int(round(v / dbu))
    reg = frame & db.Region(db.Box(n(x1), n(y1), n(x2), n(y2)))
    ins = '\n'.join(f'TILE.data.insert(RBA::Polygon::from_s("{p}"))' for p in reg.each())
    head = f"""
source($input, $topcell)
target($output, $outtop)
clip({x1 - margin}, {y1 - margin}, {x2 + margin}, {y2 + margin})
flat
TILE = polygon_layer
{ins}
"""
    return head + '\n'.join(bodies)


def presplit(ly, top, box, margin, path):
    """Write the layout clipped to box + margin (hierarchy kept) to path; return the clipped top cell name.
    Each tile process then reads only its own area instead of the whole chip GDS."""
    x1, y1, x2, y2 = box
    ci = ly.clip(top.cell_index(), db.DBox(x1 - margin, y1 - margin, x2 + margin, y2 + margin))
    opt = db.SaveLayoutOptions(); opt.select_cell(ci)
    ly.write(path, opt)
    name = ly.cell(ci).name
    ly.cell(ci).prune_cell()
    return name


# Fill-only SRAM abstraction: inside a macro, fill is never placed, so the fill recipes only need to see
# the macro as occupied.  Flattening the bit-cell arrays was the whole cost of a tile (2 Nov: 15-21 GB,
# >22 min per 1 mm tile on the full chip; 491 M GatPoly polygons from 298 RM_IHPSG13 macros).
ABSTRACT_KEEP = {125, 126}                       # TopVia1, TopMetal1: real wires/pins over the macro stay
ABSTRACT_FILL = [(1, 0), (5, 0), (8, 0), (10, 0), (30, 0), (50, 0)]   # Activ GatPoly Metal1-4: solid outline


def abstract_macros(ly, pattern):
    rx = re.compile(pattern)
    done = 0
    for c in list(ly.each_cell()):
        if not rx.match(c.name):
            continue
        box = c.bbox()
        for li in ly.layer_indexes():
            if ly.get_info(li).layer not in ABSTRACT_KEEP:
                c.shapes(li).clear()
        c.clear_insts()
        for ln, dt in ABSTRACT_FILL:
            c.shapes(ly.layer(ln, dt)).insert(box)
        done += 1
    ly.cleanup()
    return done


def run_tile(args):
    idx, script, inp, top, out, log, outtop = args
    t0 = time.time()
    r = subprocess.run(['klayout', '-b', '-r', script, '-rd', f'input={inp}', '-rd', f'topcell={top}',
                        '-rd', f'output={out}', '-rd', f'outtop={outtop}'], stdout=open(log, 'w'),
                       stderr=subprocess.STDOUT)
    return idx, r.returncode, time.time() - t0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input'); ap.add_argument('output')
    ap.add_argument('--top'); ap.add_argument('--tile', type=float, default=1000.0)
    ap.add_argument('--margin', type=float, default=20.0)
    ap.add_argument('-j', type=int, default=2)
    ap.add_argument('--no-activ', action='store_true'); ap.add_argument('--no-metal', action='store_true')
    ap.add_argument('--keep', action='store_true', help='keep the per-tile work directory')
    ap.add_argument('--no-presplit', action='store_true', help='each tile reads the whole input GDS (old, slow)')
    ap.add_argument('--abstract-macros', metavar='REGEX',
                    help='fill input: replace matching macro cells by their outline (e.g. "RM_IHPSG13_.*"); '
                         'the fill is merged into the unmodified input')
    ap.add_argument('--only', help='comma list of tiles (e.g. 2_3,0_4) to run; no merge/output (timing tests)')
    a = ap.parse_args()

    ly = db.Layout(); ly.read(a.input)
    top = ly.cell(a.top) if a.top else ly.top_cell()
    bb = top.dbbox()
    out = Path(a.output).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / (out.stem + '_filltiles')
    shutil.rmtree(work, ignore_errors=True); work.mkdir()
    bodies = []
    for k in ('ActGatP', 'Metal'):
        if (k == 'ActGatP' and a.no_activ) or (k == 'Metal' and a.no_metal):
            continue
        body, n = macro_body(MACROS[k])
        bodies.append(body)
        print(f'[fill_tiled] {k}: {MACROS[k].name} ({n} EdgeSeal.holes -> TILE)')
    # fill frame = holes of the merged EdgeSeal ring (39/0) of the whole chip
    li = ly.find_layer(39, 0)
    assert li is not None, 'no EdgeSeal (39/0) in the layout: add the seal ring first (make_sealring.py --input)'
    es = db.Region(top.begin_shapes_rec(li)).merged()
    frame = db.Region()
    for p in es.each():
        for h in range(p.holes()):
            frame.insert(db.Polygon(list(p.each_point_hole(h))))
    frame.merge()
    print(f'[fill_tiled] fill frame (inside seal ring): {frame.bbox().to_dtype(ly.dbu)}')
    if a.abstract_macros:
        t = time.time()
        print(f'[fill_tiled] abstracted {abstract_macros(ly, a.abstract_macros)} macro cells '
              f'({a.abstract_macros}) in {time.time() - t:.0f} s', flush=True)
    jobs = []
    nx = max(1, int(-(-bb.width() // a.tile))); ny = max(1, int(-(-bb.height() // a.tile)))
    for ix in range(nx):
        for iy in range(ny):
            box = (bb.left + ix * a.tile, bb.bottom + iy * a.tile,
                   min(bb.right, bb.left + (ix + 1) * a.tile), min(bb.top, bb.bottom + (iy + 1) * a.tile))
            i = f'{ix}_{iy}'
            s = work / f'tile_{i}.drc'
            if a.only and i not in a.only.split(','):
                continue
            s.write_text(tile_script(bodies, box, a.margin, frame, ly.dbu))
            if a.no_presplit:
                inp, itop = str(Path(a.input).resolve()), top.name
            else:
                inp = str(work / f'tile_{i}_in.gds')
                itop = presplit(ly, top, box, a.margin, inp)
            jobs.append((i, str(s), inp, itop, str(work / f'tile_{i}.gds'), str(work / f'tile_{i}.log'), top.name))
    print(f'[fill_tiled] {len(jobs)} tiles ({nx}x{ny} of {a.tile} um), {a.j} in parallel')
    t0 = time.time(); bad = []
    with cf.ThreadPoolExecutor(max_workers=a.j) as ex:
        for i, rc, dt in ex.map(run_tile, jobs):
            if rc != 0:
                bad.append(i)
            print(f'[fill_tiled]   tile {i}: rc={rc} {dt:.0f} s', flush=True)
    if bad:
        print(f'[fill_tiled] FAILED tiles {bad}; see {work}/tile_*.log'); sys.exit(2)
    if a.only:
        print(f'[fill_tiled] --only: tiles left in {work}, no output written'); return
    # merge: fill cells share names across tiles -> KLayout merges them on read
    if a.abstract_macros:
        ly = db.Layout(); ly.read(a.input)       # merge into the real layout, not the abstracted one
    nfill = 0
    for j in jobs:
        t = db.Layout(); t.read(j[4])
        nfill += sum(1 for _ in t.top_cell().each_inst())
        ly.read(j[4])
    ly.write(str(out))
    print(f'[fill_tiled] wrote {out}: {nfill} fill instances/arrays merged in {time.time() - t0:.0f} s')
    if not a.keep:
        shutil.rmtree(work)


if __name__ == '__main__':
    main()
