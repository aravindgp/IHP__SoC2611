# KLayout batch script: for the cells whose name matches a pattern, print shape count, child-instance count and how
# many times the cell is instantiated; flags EMPTY cells (no shapes and no children) that are still referenced.
# usage: klayout -b -r gds_cell_check.py -rd gds=<file.gds> -rd pat=BITKIT
import pya
import re

ly = pya.Layout()
ly.read(gds)
pat = re.compile(pat)
hits = 0
for c in ly.each_cell():
    if not pat.search(c.name):
        continue
    shapes = sum(c.shapes(li).size() for li in ly.layer_indexes())
    kids = c.child_instances()
    parents = c.parent_cells()
    flag = 'EMPTY' if (shapes == 0 and kids == 0) else 'ok'
    print(f'CELLCHK {flag} {c.name} shapes={shapes} children={kids} parents={parents}')
    hits += 1
print(f'CELLCHK done {hits} cells matching, top cells: {[ly.cell(i).name for i in ly.each_top_cell()]}')
