#!/usr/bin/env python3
"""DGrid-SoC1 pad ring + seal ring generator for IHP SG13CMOS5L (sg13cmos5l_io).

Reads a pad-ring config (padring/padring_qfn64.json) and writes into --outdir:
  padring.gds        empty pad frame: seal ring (die edge), 4 corners, 64 pads, IO fillers,
                     64 bondpads; top cell `--top` (default dgrid_padring).  PDK IO cells merged in.
  bondpad_70x70.gds  CMOS5L bondpad (TopMetal1 + Passiv opening + dfpad, PCell 'bondpad' shape=square,
  bondpad_70x70.lef    stack=nil defaults: Pas_c = 2.1 um passivation enclosure)
  padring.tcl        OpenROAD script placing the SAME ring (make_io_sites/place_pad/place_corners/
                     place_io_fill/place_bondpad) for a chip-level P&R with pads in the netlist
  bond_table.csv     package pin -> pad instance / cell / signal / bondpad centre (bonding diagram input)

Geometry (LibreLane sg13cmos5l_io config + PDK sealring PCell):
  die D x D; seal ring EdgeSeal boundary = die outline (metal ring 32.2..36.4 um from the edge);
  IO row outer edge at edge_spacing (140 um) from the die edge; bondpads 70x70 in the 70..140 um band,
  abutting the pad cell's TopMetal1 'pad' pin (x 5..75, y 0..3 in cell coordinates);
  IO cells 180 um high -> inner edge of the ring at 320 um; core area may start at >= 320 um
  (DGSE uses a 340 um core inset). 16 pads per side, evenly pitched between the corners.

usage: python3 make_padring.py [--config padring/padring_qfn64.json] [--outdir work/padring]
                               [--top dgrid_padring] [--no-sealring]
"""
import argparse
import csv
import json
import os
from pathlib import Path

import klayout.db as db

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
from make_sealring import add_sealring  # noqa: E402

PDK_ROOT = os.environ.get('PDK_ROOT', '/root/.claude/jobs/658ac326/tmp/pdk_root')
IO_GDS = f'{PDK_ROOT}/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/gds/sg13cmos5l_io.gds'
PFX = 'sg13cmos5l_'
FILLER_W = {'sg13cmos5l_Filler10000': 50, 'sg13cmos5l_Filler4000': 20, 'sg13cmos5l_Filler2000': 10,
            'sg13cmos5l_Filler1000': 5, 'sg13cmos5l_Filler400': 2, 'sg13cmos5l_Filler200': 1}
SUPPLIES = {'VDD', 'VSS', 'IOVDD', 'IOVSS'}


def make_bondpad(layout, name, size, pas_c=2.1):
    c = layout.create_cell(name)
    dbu = layout.dbu
    box = db.DBox(0, 0, size, size)
    c.shapes(layout.layer(126, 0)).insert(box.to_itype(dbu))           # TopMetal1
    c.shapes(layout.layer(41, 0)).insert(box.to_itype(dbu))            # dfpad
    c.shapes(layout.layer(9, 0)).insert(box.enlarged(-pas_c, -pas_c).to_itype(dbu))  # Passiv opening
    c.shapes(layout.layer(126, 25)).insert(db.DText('pad', size / 2, size / 2).to_itype(dbu))
    return c


def write_bondpad_lef(path, name, size):
    Path(path).write_text(f"""VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
MACRO {name}
  CLASS COVER ;
  ORIGIN 0 0 ;
  FOREIGN {name} 0 0 ;
  SIZE {size:.3f} BY {size:.3f} ;
  SYMMETRY X Y R90 ;
  PIN pad
    DIRECTION INOUT ;
    USE SIGNAL ;
    PORT
      LAYER TopMetal1 ;
        RECT 0 0 {size:.3f} {size:.3f} ;
    END
  END pad
  OBS
    LAYER TopMetal1 ;
      RECT 0 0 {size:.3f} {size:.3f} ;
  END
END {name}
END LIBRARY
""")


def side_positions(cfg):
    """Return {side: [(along_pos_um, name, cell, inst)]} in increasing along-row coordinate."""
    D = cfg['die'][0]
    e, h, pw = cfg['edge_spacing'], cfg['io_height'], cfg['pad_width']
    row_lo, row_hi = e + h, D - e - h            # between the corner cells
    out = {}
    for side, pads in cfg['sides'].items():
        n = len(pads)
        pitch = int((row_hi - row_lo) / n)       # integer um pitch (IO site = 1 um)
        span = (n - 1) * pitch + pw
        start = row_lo + int((row_hi - row_lo - span) / 2)
        # config order is package order: west top->bottom, south L->R, east B->T, north R->L
        ordered = list(pads) if side in ('south', 'east') else list(reversed(pads))
        lst = []
        for i, (name, cell) in enumerate(ordered):
            inst = f'pad_{side}_{name}' if name in SUPPLIES else f'pad_{name}'
            lst.append((start + i * pitch, name, PFX + cell, inst))
        out[side] = (lst, pitch)
    return out


# DEF orientation -> KLayout fixpoint transformation code (same mapping as KLayout's DEF reader)
DEF_ORIENT = {'N': db.DTrans.R0, 'W': db.DTrans.R90, 'S': db.DTrans.R180, 'E': db.DTrans.R270,
              'FN': db.DTrans.M90, 'FW': db.DTrans.M45, 'FS': db.DTrans.M0, 'FE': db.DTrans.M135}
# Orientations exactly as OpenROAD's pad placer (make_io_sites/place_pad/place_corners) uses them
SIDE_ORIENT = {'south': 'N', 'north': 'FS', 'east': 'W', 'west': 'FW'}
CORNER_ORIENT = {'sw': 'N', 'se': 'FN', 'ne': 'S', 'nw': 'FS'}


def def_trans(orient, llx, lly, w, h):
    """DTrans placing a cell with LEF size w x h (origin 0,0) in DEF style: orientation, then the
    lower-left of the oriented box at (llx, lly)."""
    r = DEF_ORIENT[orient]
    bb = db.DBox(0, 0, w, h).transformed(r)
    return db.DTrans(llx - bb.left, lly - bb.bottom) * r


def row_ll(side, pos, D, e, h):
    """DEF lower-left of a row cell whose along-row coordinate starts at pos."""
    return {'south': (pos, e), 'north': (pos, D - e - h),
            'east': (D - e - h, pos), 'west': (e, pos)}[side]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', default=str(HERE / 'padring' / 'padring_qfn64.json'))
    ap.add_argument('--outdir', default=str(HERE / 'work' / 'padring'))
    ap.add_argument('--top', default='dgrid_padring')
    ap.add_argument('--no-sealring', action='store_true')
    ap.add_argument('--portmap', help='pad -> core port map JSON (padring/portmap_qfn64.json); writes '
                    'pad_connect.tcl for chip_integrate.tcl')
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    D, Dy = cfg['die']
    assert D == Dy, 'square die only'
    e, h, pw = cfg['edge_spacing'], cfg['io_height'], cfg['pad_width']
    bp = cfg['bondpad']; bpn, bps = bp['name'], bp['size']; bpo = bp['offset']

    ly = db.Layout(); ly.dbu = 0.001
    ly.read(IO_GDS)                                  # brings all sg13cmos5l_* IO cells
    top = ly.create_cell(a.top)
    bond = make_bondpad(ly, bpn, bps)
    # standalone bondpad GDS + LEF
    bl = db.Layout(); bl.dbu = 0.001; make_bondpad(bl, bpn, bps); bl.write(str(out / f'{bpn}.gds'))
    write_bondpad_lef(out / f'{bpn}.lef', bpn, bps)

    def inst(cellname, t):
        c = ly.cell(cellname)
        assert c is not None, cellname
        top.insert(db.DCellInstArray(c.cell_index(), t))

    # corners (Corner R0 = SW: outer die corner at the cell origin), OpenROAD orientations
    for k, (llx, lly) in {'sw': (e, e), 'se': (D - e - h, e), 'ne': (D - e - h, D - e - h),
                          'nw': (e, D - e - h)}.items():
        inst(cfg['corner'], def_trans(CORNER_ORIENT[k], llx, lly, h, h))

    sides = side_positions(cfg)
    fillers = sorted(cfg['fillers'], key=lambda f: -FILLER_W[f])
    rows = []
    nfill = 0
    for side, (lst, pitch) in sides.items():
        cursor = e + h
        segs = []
        ori = SIDE_ORIENT[side]
        for pos, name, cell, iname in lst:
            segs.append((cursor, pos)); cursor = pos + pw
            t = def_trans(ori, *row_ll(side, pos, D, e, h), pw, h)
            inst(cell, t)
            # bondpad: box (offset, offset+size) in pad-cell coordinates, same orientation as the pad
            bbox = db.DBox(bpo[0], bpo[1], bpo[0] + bps, bpo[1] + bps).transformed(t)
            top.insert(db.DCellInstArray(bond.cell_index(), def_trans(ori, bbox.left, bbox.bottom, bps, bps)))
            bc = bbox.center()
            rows.append(dict(side=side, along=pos, name=name, cell=cell, inst=iname, bx=bc.x, by=bc.y))
        segs.append((cursor, D - e - h))
        for lo, hi in segs:
            x = lo
            while hi - x > 1e-6:
                f = next(f for f in fillers if FILLER_W[f] <= hi - x + 1e-6)
                inst(f, def_trans(ori, *row_ll(side, x, D, e, h), FILLER_W[f], h))
                x += FILLER_W[f]; nfill += 1
    if not a.no_sealring:
        add_sealring(ly, top, D, D)
    # drop unused IO library cells from the output
    used = set(top.called_cells()) | {top.cell_index()}
    for ci in [c.cell_index() for c in ly.each_cell() if c.cell_index() not in used]:
        if ly.is_valid_cell_index(ci) and ly.cell(ci).is_top():
            ly.delete_cell_rec(ci)
    gds = out / 'padring.gds'
    ly.write(str(gds))

    # bond table in package-pin order (config order)
    pin = 0
    byname = {(r['side'], r['inst']): r for r in rows}
    with open(out / 'bond_table.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['pkg_pin', 'side', 'signal', 'pad_cell', 'instance', 'bondpad_x_um', 'bondpad_y_um'])
        for side in ('west', 'south', 'east', 'north'):
            for name, cell in cfg['sides'][side]:
                pin += 1
                iname = f'pad_{side}_{name}' if name in SUPPLIES else f'pad_{name}'
                r = byname[(side, iname)]
                w.writerow([pin, side, name, r['cell'], iname, f"{r['bx']:.1f}", f"{r['by']:.1f}"])

    # Verilog stub: pad instances only (template for the chip-top pad ring; also used by
    # padring/test_padring_openroad.sh).  Core-side pins (p2c/c2p/c2p_en) are left open here.
    sig = [r for r in rows if r['name'] not in SUPPLIES]
    vl = ['// Generated by make_padring.py -- pad instances of the QFN64 ring (core pins open)',
          f'module {a.top} (',
          ',\n'.join(f'    inout {r["name"]}_PAD' for r in sig),
          ');']
    for r in rows:
        if r['name'] in SUPPLIES:
            vl.append(f'  {r["cell"]} {r["inst"]} ();')
        else:
            vl.append(f'  {r["cell"]} {r["inst"]} (.pad({r["name"]}_PAD));')
    vl.append('endmodule')
    (out / 'padring_stub.v').write_text('\n'.join(vl) + '\n')

    # OpenROAD Tcl: exact same placement
    rowname = {'south': 'IO_SOUTH', 'north': 'IO_NORTH', 'east': 'IO_EAST', 'west': 'IO_WEST'}
    tl = [
        '# Generated by HW/asic/signoff/make_padring.py from ' + os.path.basename(a.config) + ' -- do not edit by hand.',
        '# Run after initialize_floorplan (die must be 0 0 %g %g) and before PDN/placement.' % (D, D),
        '# Needs LEFs: sg13cmos5l_io.lef and %s/%s.lef; pad instances named as below in the netlist.' % (out, bpn),
        '# place_pad -location = lower-left of the pad along the row, um from the die origin (verified: DEF == GDS, padring/test_padring_openroad.sh).',
        'add_global_connection -net {VDD} -pin_pattern {^vdd$} -power',
        'add_global_connection -net {VSS} -pin_pattern {^vss$} -ground',
        'add_global_connection -net {IOVDD} -pin_pattern {^iovdd$} -power',
        'add_global_connection -net {IOVSS} -pin_pattern {^iovss$} -ground',
        'make_io_sites -horizontal_site sg13cmos5l_ioSite -vertical_site sg13cmos5l_ioSite '
        '-corner_site sg13cmos5l_cornerSite -offset %g' % e,
    ]
    for side, (lst, pitch) in sides.items():
        tl.append(f'# {side}: pitch {pitch} um')
        for pos, name, cell, iname in lst:
            tl.append(f'place_pad -row {rowname[side]} -location {pos:g} -master {cell} {iname}')
    tl += ['place_corners ' + cfg['corner'],
           'set iofill {%s}' % ' '.join(fillers)]
    for r in rowname.values():
        tl.append(f'place_io_fill -row {r} {{*}}$iofill')
    tl += ['connect_by_abutment',
           f'place_bondpad -bond {bpn} pad_* -offset {{{bpo[0]:g} {bpo[1]:g}}}',
           'remove_io_rows', '']
    (out / 'padring.tcl').write_text('\n'.join(tl))
    if a.portmap:
        pm = json.loads(Path(a.portmap).read_text())['pads']
        pl = ['# Generated by make_padring.py --portmap ' + os.path.basename(a.portmap) + ' -- do not edit.',
              '# {instance master pad_signal {pad_pin chip_port ...}}; supplies have an empty pin map',
              'set pad_list {']
        for r in rows:
            pins = {} if r['name'] in SUPPLIES else pm[r['name']]
            pm_s = ' '.join(f'{k} {{{v}}}' for k, v in pins.items())
            pl.append(f"  {{{r['inst']} {r['cell']} {r['name']} {{{pm_s}}}}}")
        pl += ['}', f'set bondpad_master {bpn}', '']
        (out / 'pad_connect.tcl').write_text('\n'.join(pl))
        print(f'      {out}/pad_connect.tcl')
    print(f'wrote {gds} (top {a.top}, die {D} um, {len(rows)} pads, {nfill} fillers); '
          f'pitches {[(s, p) for s, (l, p) in sides.items()]}')
    print(f'      {out}/padring.tcl, bond_table.csv, {bpn}.gds/.lef')


if __name__ == '__main__':
    main()
