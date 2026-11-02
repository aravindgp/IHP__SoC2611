#!/usr/bin/env python3
"""Cut a DRC test window out of a chip GDS around the first instance of a cell (hierarchy kept).

usage: clip_window.py <in.gds> <top> <cell_name> <out.gds> [margin_um=60] [nth=0]
Writes top cell 'clip_<cell_name>'.  Use it to re-check a full-chip DRC marker in context in minutes
(drc_capped.sh <out.gds> clip_<cell> ... -- --table=<t>).
"""
import sys
import klayout.db as db

gin, top_name, cell, gout = sys.argv[1:5]
margin = float(sys.argv[5]) if len(sys.argv) > 5 else 60.0
nth = int(sys.argv[6]) if len(sys.argv) > 6 else 0
ly = db.Layout()
ly.read(gin)
top = ly.cell(top_name)
hits = [i for i in top.each_inst() if i.cell.name == cell]
if len(hits) <= nth:
    sys.exit(f'{cell}: {len(hits)} instance(s) in {top_name}')
box = hits[nth].dbbox()
win = box.enlarged(margin, margin)
ci = ly.clip(top.cell_index(), win)
ly.rename_cell(ci, f'clip_{cell}')
opt = db.SaveLayoutOptions()
opt.select_cell(ci)
ly.write(gout, opt)
print(f'{cell} #{nth} at {box}; window {win} -> {gout} (top clip_{cell})')
