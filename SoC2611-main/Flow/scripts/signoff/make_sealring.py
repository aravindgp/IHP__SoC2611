#!/usr/bin/env python3
"""IHP SG13CMOS5L seal ring generator (pure klayout.db, no PCell runtime needed).

Geometry is a 1:1 port of the PDK PCell
  $PDK_ROOT/ihp-sg13cmos5l/libs.tech/klayout/python/sg13cmos5l_pycell_lib/ihp/sealring_code.py
(class sealring, M1-M4-TM1 stack, edgeBox 25 um, Seal_k corner).  The official driver
libs.tech/klayout/tech/scripts/sealring.py needs the SG13_dev PCell library, which in turn needs
the pycell4klayout-api submodule ("cni"); that submodule is empty in this PDK checkout, so we
re-implement the same shapes here.  The EdgeSeal boundary (39/4) is the die outline.

usage (standalone):
  python3 make_sealring.py --width 6600 --height 6600 -o sealring.gds [--top sealring_top]
as module:
  from make_sealring import add_sealring; add_sealring(layout, cell, width_um, height_um)
"""
import argparse
from pathlib import Path
import klayout.db as db

# GDS layer numbers (sg13cmos5l.map / drc layers_def.drc)
L = {
    'Activ': (1, 0), 'pSD': (14, 0), 'EdgeSeal': (39, 0), 'EdgeSeal.boundary': (39, 4),
    'Metal1': (8, 0), 'Metal2': (10, 0), 'Metal3': (30, 0), 'Metal4': (50, 0),
    'TopMetal1': (126, 0), 'Cont': (6, 0), 'Via1': (19, 0), 'Via2': (29, 0), 'Via3': (49, 0),
    'TopVia1': (125, 0), 'Passiv': (9, 0), 'TEXT': (63, 0),
}
EDGE_BOX = 25.0          # sealring_complete_edgeBox
CNT_A, VN_A, TV1_A = 0.16, 0.19, 0.42


def _rot(name):
    return {'R0': 0, 'R90': 1, 'R180': 2,
            'R270': 3}[name]


def sealring_shapes(l_total, w_total):
    """Return {layer: [DBox|DPolygon]} for a seal ring whose EdgeSeal boundary is
    (0,0)-(l_total,w_total) in um (l = X, w = Y)."""
    edgeBox = EDGE_BOX
    l, w = l_total, w_total
    maxMetalWidth = 4.2
    maxMetalLength = maxMetalWidth * 2
    corner_width = 4.2
    metalOffset = 3 + corner_width + edgeBox
    viaOffset = 5.1 + corner_width + edgeBox
    corner_length = corner_width * 2
    corner_steps = 4
    corner_end = 28.2 + edgeBox
    corner_startx = 0 + corner_end - (corner_end - corner_width * (corner_steps + 1))
    corner_starty = 0
    metal_startx = corner_end - (corner_end - maxMetalWidth * (corner_steps + 1)) + metalOffset

    layers = ['Activ', 'pSD', 'EdgeSeal', 'Metal1', 'Metal2', 'Metal3', 'Metal4', 'TopMetal1']
    vias = ['Cont', 'Via1', 'Via2', 'Via3', 'TopVia1']
    group = []          # (layer, DPolygon) of the lower-left corner, copied to the 3 others
    out = {}

    def add(layer, shape):
        out.setdefault(layer, []).append(db.DPolygon(shape) if isinstance(shape, db.DBox) else shape)

    def gen_corner(sx, sy, cw, cl, steps, cend, off):
        items = []
        for cnt in range(steps):
            items.append(db.DBox(sx - cw * (cnt + 1), sy + off + (cl - cw) * cnt,
                                 sx - cw * cnt, sy + cl + off + (cl - cw) * cnt))
        items.append(db.DBox(sx - cw * (steps + 1), sy + off + (cl - cw) * steps,
                             sx - cw * steps, cend))
        return items

    # Passiv corner
    group.append(('Passiv', db.DBox(corner_startx + edgeBox, corner_starty + edgeBox,
                                    corner_end + edgeBox, corner_width + edgeBox)))
    for b in gen_corner(corner_startx + edgeBox, corner_starty + edgeBox, corner_width,
                        corner_length, corner_steps, corner_end, 0):
        group.append(('Passiv', b))
    # metal corners
    for layer in layers:
        for b in gen_corner(metal_startx, corner_starty, maxMetalWidth, maxMetalLength,
                            corner_steps, corner_end, metalOffset):
            group.append((layer, b))
    # via corners
    for layer in vias:
        viaWidth = CNT_A if layer == 'Cont' else TV1_A if layer == 'TopVia1' else VN_A
        viaLength = 4.2
        via_startx = (corner_end - (corner_end - maxMetalWidth * (corner_steps + 1))
                      + metalOffset - maxMetalWidth / 2 - 0.1)
        base = db.DBox(via_startx, viaOffset, via_startx + viaWidth, viaOffset + viaLength)
        group.append((layer, base))
        for cnt in range(1, corner_steps + 1):
            t1 = db.DTrans(1, False,
                           2 * viaOffset + viaLength * cnt + viaWidth - 0.1, -viaLength * (cnt - 1))
            group.append((layer, base.transformed(t1)))
            t2 = db.DTrans(0, False, -maxMetalWidth * (cnt - 1),
                           maxMetalWidth * (cnt - 1) - 0.1)
            group.append((layer, base.transformed(t2)))
        group.append((layer, db.DBox(via_startx, viaOffset - 0.1, corner_end,
                                     viaOffset - 0.1 + viaWidth)))
        group.append((layer, db.DBox(viaOffset - 0.1, corner_end - maxMetalWidth / 2 - 0.1,
                                     viaOffset - 0.1 + viaWidth, corner_end)))

    for layer, b in group:
        add(layer, b)
        for rot, dx, dy in (('R180', l, w), ('R90', l, 0), ('R270', 0, w)):
            add(layer, db.DPolygon(b).transformed(db.DTrans(_rot(rot), False, dx, dy)))

    # straight lines
    for b in (db.DBox(edgeBox, corner_end, corner_width + edgeBox, w - corner_end),
              db.DBox(corner_end, edgeBox, l - corner_end, corner_width + edgeBox),
              db.DBox(l - edgeBox, corner_end, l - corner_width - edgeBox, w - corner_end),
              db.DBox(corner_end, w - edgeBox, l - corner_end, w - corner_width - edgeBox)):
        add('Passiv', b)
    for layer in layers:
        for b in (db.DBox(metalOffset, corner_end, metalOffset + corner_width, w - corner_end),
                  db.DBox(corner_end, metalOffset, l - corner_end, metalOffset + corner_width),
                  db.DBox(l - metalOffset, corner_end, l - corner_width - metalOffset, w - corner_end),
                  db.DBox(corner_end, w - metalOffset, l - corner_end, w - corner_width - metalOffset)):
            add(layer, b)
    for layer in vias:
        vw = CNT_A if layer == 'Cont' else TV1_A if layer == 'TopVia1' else VN_A
        for b in (db.DBox(viaOffset - 0.1, corner_end, viaOffset + vw - 0.1, w - corner_end),
                  db.DBox(corner_end, viaOffset - 0.1, l - corner_end, viaOffset + vw - 0.1),
                  db.DBox(l - viaOffset + 0.1, corner_end, l - vw - viaOffset + 0.1, w - corner_end),
                  db.DBox(corner_end, w - viaOffset + 0.1, l - corner_end, w - vw - viaOffset + 0.1)):
            add(layer, b)
    add('EdgeSeal.boundary', db.DBox(0, 0, l, w))
    return out


def add_sealring(layout, cell, width, height, x0=0.0, y0=0.0, cell_name='sealring'):
    """Create a 'sealring' cell (merged polygons per layer) and instantiate it in `cell`
    with its EdgeSeal boundary lower-left corner at (x0, y0) um."""
    sr = layout.create_cell(cell_name)
    dbu = layout.dbu
    for layer, shapes in sealring_shapes(width, height).items():
        li = layout.layer(*L[layer])
        reg = db.Region()
        for s in shapes:
            reg.insert(s.to_itype(dbu))
        reg.merge()
        sr.shapes(li).insert(reg)
    cell.insert(db.CellInstArray(sr.cell_index(), db.Trans(db.Vector(round(x0 / dbu), round(y0 / dbu)))))
    sr.shapes(layout.layer(*L['TEXT'])).insert(db.DText(
        f"Device registration size: x={width:.1f} um ; y={height:.1f} um", 5.0, 5.0).to_itype(dbu))
    return sr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--width', type=float, required=True, help='die width incl. sealring (um)')
    ap.add_argument('--height', type=float, required=True)
    ap.add_argument('--top', default='sealring_top',
                    help='top cell name; with --input: name of the new top wrapping the input top')
    ap.add_argument('--input', help='existing chip GDS (die origin at 0,0): the seal ring is added '
                    'around its top cell; if --top equals the input top, it is inserted in place')
    ap.add_argument('-o', '--output', required=True)
    a = ap.parse_args()
    ly = db.Layout()
    ly.dbu = 0.001
    if a.input:
        ly.read(a.input)
        tops = list(ly.top_cells())
        assert len(tops) == 1, f'input has {len(tops)} top cells'
        old = tops[0]
        if a.top == old.name or a.top == 'sealring_top':
            top = old
        else:
            top = ly.create_cell(a.top)
            top.insert(db.CellInstArray(old.cell_index(), db.Trans()))
        bb = old.dbbox()
        if bb.left < 0 or bb.bottom < 0 or bb.right > a.width or bb.top > a.height:
            print(f"WARNING: input bbox {bb} exceeds die 0,0..{a.width},{a.height}")
    else:
        top = ly.create_cell(a.top)
    add_sealring(ly, top, a.width, a.height)
    Path(a.output).resolve().parent.mkdir(parents=True, exist_ok=True)
    ly.write(a.output)
    print(f"wrote {a.output} top={top.name} {a.width}x{a.height} um")


if __name__ == '__main__':
    main()
