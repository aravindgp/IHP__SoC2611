#!/usr/bin/env python3
"""Stage a chip release into an IHP Open-Silicon-MPW IP repository (gen_structure.py layout).

usage: ihp_release.py <ip_repo> <name> <in.gds> <old_top> <chip.v> <chip.cdl> [version=v.1.0.0]
  - GDS: top cell <old_top> renamed to <name>, written to release/<version>/gds/<name>.gds.gz with the KLayout save
    options IHP requires (Open-Silicon-MPW fig/klayout_save.png): GDS2, dbu 0.001, no PCell/library context,
    zero-length paths eliminated (-> BOUNDARY), library LIB, max vertices 8000, max cell name length 32000.
  - Netlists: module / .SUBCKT <old_top> renamed to <name> -> release/<version>/netlist/<name>.v.gz and <name>.cdl.gz
  - doc/info.json: release paths point at the files (the CI resolves release.gds / release.netlist from it).
"""
import gzip
import json
import re
import sys
from pathlib import Path

import klayout.db as db

repo, name, gin, old_top, vin, cin = sys.argv[1:7]
ver = sys.argv[7] if len(sys.argv) > 7 else 'v.1.0.0'
rel = Path(repo) / 'release' / ver
(rel / 'gds').mkdir(parents=True, exist_ok=True)
(rel / 'netlist').mkdir(parents=True, exist_ok=True)

ly = db.Layout()
ly.read(gin)
top = ly.cell(old_top)
if top is None:
    sys.exit(f'{gin}: no cell {old_top}')
if ly.cell(name) is not None:
    sys.exit(f'{gin}: a cell named {name} already exists')
top.name = name
opt = db.SaveLayoutOptions()
opt.format = 'GDS2'
opt.dbu = 0.001
opt.scale_factor = 1.0
opt.write_context_info = False
opt.gds2_no_zero_length_paths = True
opt.gds2_libname = 'LIB'
opt.gds2_max_vertex_count = 8000
opt.gds2_max_cellname_length = 32000
opt.gds2_write_timestamps = True
opt.select_cell(top.cell_index())
gout = rel / 'gds' / f'{name}.gds.gz'
ly.write(str(gout), opt)
print(f'GDS  {gout} ({gout.stat().st_size / 1e6:.1f} MB), top {name}, dbu {ly.dbu}')

v = Path(vin).read_text()
v, nv = re.subn(rf'^(\s*module\s+){re.escape(old_top)}\b', rf'\g<1>{name}', v, flags=re.M)
with gzip.open(rel / 'netlist' / f'{name}.v.gz', 'wt') as fh:
    fh.write(v)   # .gz: GitHub rejects files > 100 MB (chip CDL 121 MB, Verilog 143 MB; ~6 MB each gzipped)
c = Path(cin).read_text()
c, nc = re.subn(rf'^(\.SUBCKT\s+){re.escape(old_top)}\b', rf'\g<1>{name}', c, flags=re.M | re.I)
with gzip.open(rel / 'netlist' / f'{name}.cdl.gz', 'wt') as fh:
    fh.write(c)
print(f'NET  {name}.v.gz (module renamed {nv}x), {name}.cdl.gz (.SUBCKT renamed {nc}x)')
if nv != 1 or nc != 1:
    sys.exit('expected exactly one top module / subckt to rename')

ij = Path(repo) / 'doc' / 'info.json'
info = json.loads(ij.read_text())
info['top_cell_name'] = name
info['name'] = name
info['unique_id'] = ''.join(ch for ch in name if ch.isdigit())[-4:] or info.get('unique_id', '')
info['release'] = {'version': ver, 'gds': f'release/{ver}/gds/{name}.gds.gz',
                   'netlist': f'release/{ver}/netlist/{name}.cdl.gz', 'doc': f'release/{ver}/doc'}
ij.write_text(json.dumps(info, indent=2) + '\n')
print(f'INFO {ij}: release paths set')
