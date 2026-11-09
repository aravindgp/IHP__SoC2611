# Remove fill (datatype 22 of Metal1-4 / TopMetal1) within a square at each die corner.  The IHP minimum deck flags
# MFil.c / TM1Fil.c (fill to metal 0.42 / 3.0 um) only there: the inner pad-ring corner has a 45-degree chamfer and
# the fill generators' Manhattan keep-out leaves a fill-square corner too close to it.
#  - top-up fill (shapes in the single-instance DG_TOPUP_FILL cell): the shapes are deleted;
#  - PDK fill (shared *_FILL_CELL cells placed as single instances): the instances overlapping the corner are deleted.
# usage: klayout -b -r fill_corner_clean.py -rd gds=<in.gds> -rd out=<out.gds> [-rd top=TOP] [-rd die=6600] [-rd box=300]
#        [-rd dry=1]
import pya

gds = globals().get('gds'); out = globals().get('out'); die = float(globals().get('die', 6600)); bx = float(globals().get('box', 300))
dry = str(globals().get('dry', '0')) == '1'
ly = pya.Layout(); ly.read(gds)
topname = globals().get('top')
top = ly.cell(topname) if topname else ly.top_cell()
dbu = ly.dbu
corners = [pya.Box(0, 0, bx / dbu, bx / dbu), pya.Box((die - bx) / dbu, 0, die / dbu, bx / dbu),
           pya.Box(0, (die - bx) / dbu, bx / dbu, die / dbu), pya.Box((die - bx) / dbu, (die - bx) / dbu, die / dbu, die / dbu)]
layers = [(8, 22), (10, 22), (30, 22), (50, 22), (126, 22)]
lis = [ly.find_layer(ln, dt) for (ln, dt) in layers]
lis = [li for li in lis if li is not None]

def is_fill_cell(cell):
    """a cell whose shapes are only fill datatype-22 shapes (and that has no children)"""
    if cell.child_cells() > 0: return False
    for li in range(ly.layers()):
        if not ly.is_valid_layer(li): continue
        if cell.shapes(li).is_empty(): continue
        info = ly.get_info(li)
        if info.datatype != 22: return False
    return True

nshape = 0; ninst = 0; skipped = 0
# 1. shapes directly in single-instance cells (top-up fill cell, or the top cell)
for li in lis:
    todo = {}
    for box in corners:
        it = top.begin_shapes_rec_overlapping(li, box)
        while not it.at_end():
            ci = it.cell_index(); cell = ly.cell(ci)
            single = ci == top.cell_index() or sum(1 for _ in cell.each_parent_inst()) == 1
            if single: todo.setdefault(ci, set()).add(it.shape())
            it.next()
    for ci, shapes in todo.items():
        if not dry:
            for s in shapes: s.delete()
        nshape += len(shapes)
        print(f'layer {ly.get_info(li)}: {len(shapes)} fill shapes removed in {ly.cell(ci).name}')
# 2a. array instances of fill cells overlapping a corner: explode them into single instances first (an array may
#     extend far beyond the corner, so it must not be deleted whole)
#     (off by default: the verified run, singles + top-up shapes only, already cleared the MFil.c / TM1Fil.c markers)
nexp = 0
if str(globals().get('explode', '0')) == '1':
    for box in corners:
        it = top.begin_instances_rec_overlapping(box)
        arrs = []
        while not it.at_end():
            inst = it.current_inst_element().inst()
            if inst.is_regular_array() and is_fill_cell(ly.cell(inst.cell_index)): arrs.append(inst)
            it.next()
        for inst in arrs:
            if not dry: inst.explode()
            nexp += 1
print(f'FILL_CORNER_CLEAN arrays exploded: {nexp}')
# 2b. instances of shared fill cells overlapping a corner
for box in corners:
    it = top.begin_instances_rec_overlapping(box)
    dels = []
    while not it.at_end():
        inst = it.current_inst_element().inst()
        cell = ly.cell(inst.cell_index)
        # only instances that lie entirely inside the corner box: a chip-wide fill cell (DG_TOPUP_FILL) also
        # matches is_fill_cell and overlaps every corner, and must never be deleted whole
        ib = it.trans() * inst.bbox() if hasattr(it, 'trans') else inst.bbox()
        if is_fill_cell(cell) and ib.inside(box):
            if inst.is_regular_array(): skipped += 1
            else: dels.append(inst)
        it.next()
    for inst in dels:
        if not dry: inst.delete()
    ninst += len(dels)
print(f'FILL_CORNER_CLEAN shapes={nshape} instances={ninst} array_instances_skipped={skipped} (dry={dry})')
if not dry and out:
    opt = pya.SaveLayoutOptions(); opt.format = 'GDS2'; opt.dbu = dbu
    ly.write(out, opt)
    print('wrote', out)
