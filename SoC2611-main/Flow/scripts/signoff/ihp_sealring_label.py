#!/usr/bin/env python3
"""Check / complete the seal-ring device-registration label (TEXT 63/0) in a release GDS, as IHP audits it.

usage: ihp_sealring_label.py <in.gds[.gz]> <out.gds[.gz]>
The PDK seal ring PCell writes 'Device registration size: x=<w> um ; y=<h> um\\nCalculated area: <a> sq mm';
make_sealring.py wrote only the first line.  This rewrites the label with both lines (area computed correctly in
mm2 -- the PDK formula is off by 1e6, flagged in IHP's audit of Open-Silicon-MPW#77) and saves with the
Open-Silicon-MPW KLayout options (same as ihp_release.py).
"""
import re
import sys

import klayout.db as db

gin, gout = sys.argv[1:3]
ly = db.Layout()
ly.read(gin)
li = ly.find_layer(63, 0)
if li is None:
    sys.exit('no TEXT layer 63/0 in the layout')
found = 0
for c in ly.each_cell():
    for s in list(c.shapes(li).each()):
        if not s.is_text():
            continue
        m = re.match(r'Device registration size: x=([\d.]+) um ; y=([\d.]+) um', s.text_string)
        if not m:
            continue
        w, h = float(m.group(1)), float(m.group(2))
        new = (f'Device registration size: x={w:.1f} um ; y={h:.1f} um\n'
               f'Calculated area: {w * h / 1e6:.2f} sq mm')
        print(f'{c.name}: "{s.text_string}" -> "{new}"')
        s.text_string = new
        found += 1
if found != 1:
    sys.exit(f'expected exactly one registration label, found {found}')
top = ly.top_cells()
if len(top) != 1:
    sys.exit(f'expected a single root cell, found {[t.name for t in top]}')
opt = db.SaveLayoutOptions()
opt.format = 'GDS2'
opt.dbu = 0.001
opt.write_context_info = False
opt.gds2_no_zero_length_paths = True
opt.gds2_libname = 'LIB'
opt.gds2_max_vertex_count = 8000
opt.gds2_max_cellname_length = 32000
opt.gds2_write_timestamps = True
ly.write(gout, opt)
print(f'root {top[0].name}; wrote {gout}')
