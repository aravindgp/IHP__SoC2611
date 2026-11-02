#!/usr/bin/env python3
"""Merge cell CDLs, keeping the first definition of every .SUBCKT (the SRAM CDLs each repeat the
shared RSC_IHPSG13_* cells).  Applies 's/ lvsres / res_metal1 /' (sg13g2 SRAM resistor naming).
usage: merge_cell_cdl.py out.cdl in1.cdl [in2.cdl ...]"""
import re
import sys

out, ins = sys.argv[1], sys.argv[2:]
seen = set()
res = ['* merged cell CDL (merge_cell_cdl.py): ' + ' '.join(i.split('/')[-1] for i in ins)]
dup = 0
pfix = 0
for f in ins:
    keep = True
    move_ptap = False
    for line in open(f, errors='replace'):
        line = line.rstrip('\n').replace(' lvsres ', ' res_metal1 ')
        # PDK bug (sg13cmos5l_io.cdl, IOPadInOut*): "XI3 net2 iovss pad ptap1 / sg13cmos5l_Clamp_N15N15D"
        # followed by "XR0 vss sub! A=..." -- the ptap1 model name slipped onto the previous line.
        m = re.match(r'^(X\S+\s.*?)\s+ptap1\s+/\s+(\S+)\s*$', line)
        if m:
            line = f'{m.group(1)} / {m.group(2)}'; move_ptap = True; pfix += 1
        elif move_ptap and re.match(r'^XR\S*\s+\S+\s+sub!\s+A=', line):
            line = re.sub(r'sub!\s+A=', 'sub! ptap1 A=', line, count=1); move_ptap = False
        m = re.match(r'\s*\.SUBCKT\s+(\S+)', line, re.I)
        if m:
            keep = m.group(1) not in seen
            seen.add(m.group(1))
            if not keep:
                dup += 1
        if keep:
            res.append(line)
        if re.match(r'\s*\.ENDS', line, re.I):
            keep = True
open(out, 'w').write('\n'.join(res) + '\n')
print(f'merge_cell_cdl: {len(seen)} subckts, {dup} duplicate definitions dropped, {pfix} misplaced ptap1 fixed')
