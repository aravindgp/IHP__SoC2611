#!/usr/bin/env python3
"""LVS view of the chip: IO cells reduced to their metal (devices removed), CDL IO subckts emptied.

The open CMOS5L KLayout LVS deck does not match IHP's own IO cells even standalone (measured:
sg13cmos5l_IOPadIn vs sg13cmos5l_io.cdl -> DCNDiode/DCPDiode/LevelDown NoMatch, split cathode pins,
sub! handling).  IO cells are IHP-qualified hard IP, so the chip LVS checks everything AROUND them:
core netlist, pad-to-core wiring, pad<->bondpad, pad-ring rails and pad<->core-ring power straps.
  GDS: inside every cell of the IO library (and their sub-cells) keep only Metal1-4, TopMetal1, the
       via layers between them, and the pin/text layers; all FEOL (Activ, GatPoly, implants, wells,
       Cont, ...) is deleted -> no devices, real metal connectivity of rails and pins.
  CDL: the IO subckts keep their pin lists, bodies are emptied.
usage: make_lvs_view.py <in.gds> <out.gds> <in.cdl> <out.cdl> [lib.gds ...]
  lib.gds: libraries whose cells are reduced to metal (default: the sg13cmos5l_io GDS).  Pass the
  RM_IHPSG13_*.gds files as well to treat the SRAM macros the same way (--srams in run_signoff.sh).
"""
import re
import sys
import klayout.db as db

gin, gout, cin, cout = sys.argv[1:5]
libs = sys.argv[5:] or \
    ['/root/.claude/jobs/658ac326/tmp/pdk_root/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/gds/sg13cmos5l_io.gds']
KEEP_LAYERS = {8, 19, 10, 29, 30, 49, 50, 125, 126}          # Metal1 Via1 Metal2 Via2 Metal3 Via3 Metal4 TopVia1 TopMetal1
io_cells, io_tops = set(), set()
for lib in libs:
    iol = db.Layout(); iol.read(lib)
    io_cells |= {c.name for c in iol.each_cell()}
    io_tops |= {c.name for c in iol.top_cells()}

ly = db.Layout(); ly.read(gin)
nstrip = 0
for c in ly.each_cell():
    if c.name not in io_cells:
        continue
    for li in ly.layer_indexes():
        if ly.get_info(li).layer not in KEEP_LAYERS:
            c.shapes(li).clear()
    nstrip += 1
ly.write(gout)
print(f'make_lvs_view: stripped FEOL in {nstrip} IO-library cells -> {gout}')

# IO sub-cells (LevelDown, clamps, diodes, ...) are referenced only by the IO tops: drop them, else
# they become extra top circuits in the schematic
cdl_txt = open(cin).read()
io_sub = {n for n in re.findall(r'^\s*\.SUBCKT\s+(\S+)', cdl_txt, re.I | re.M) if n in io_cells and n not in io_tops}
out, skip, nempty, drop = [], False, 0, False
for line in cdl_txt.splitlines(True):
    m = re.match(r'\s*\.SUBCKT\s+(\S+)', line, re.I)
    if m and m.group(1) in io_sub:
        drop = True; continue
    if drop:
        if re.match(r'\s*\.ENDS', line, re.I):
            drop = False
        continue
    if m and m.group(1) in io_tops:
        out.append(line); skip = True; nempty += 1; continue
    if skip:
        if re.match(r'\s*\.ENDS', line, re.I):
            out.append(line); skip = False
        elif line.startswith('*'):
            out.append(line)
        continue
    out.append(line)
open(cout, 'w').write(''.join(out))
print(f'make_lvs_view: emptied {nempty} IO subckts, dropped {len(io_sub)} IO sub-cell subckts -> {cout}')
