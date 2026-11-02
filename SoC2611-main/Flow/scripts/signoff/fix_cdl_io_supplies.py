#!/usr/bin/env python3
"""Post-process verilog2cdl output for the pad ring: connect IO-cell iovdd/iovss pins (verilog2cdl
leaves them NC_n: write_verilog carries no supply pins) to IOVDD/IOVSS, and add IOVDD/IOVSS to the
top subckt ports.  Pin positions come from the cell CDL .SUBCKT lines.
usage: fix_cdl_io_supplies.py <cells.cdl> <top.cdl> <top> <out.cdl>"""
import re
import sys

cells, src, top, out = sys.argv[1:5]
pins = {}
for line in open(cells):
    m = re.match(r'\.SUBCKT\s+(\S+)\s+(.*)', line, re.I)
    if m:
        pins[m.group(1)] = m.group(2).split()
SUP = {'iovdd': 'IOVDD', 'iovss': 'IOVSS'}
lines = open(src).read().split('\n')
# join continuation lines
joined = []
for l in lines:
    if l.startswith('+') and joined:
        joined[-1] += ' ' + l[1:].strip()
    else:
        joined.append(l)
nfix = 0
res = []
for l in joined:
    m = re.match(r'\.SUBCKT\s+' + re.escape(top) + r'\s', l, re.I)
    if m:
        toks = l.split()
        for s in ('IOVDD', 'IOVSS'):
            if s not in toks:
                toks.append(s)
        l = ' '.join(toks)
    elif l[:1] in ('X', 'x'):
        toks = l.split()
        cell = toks[-1]
        if cell in pins and any(p in SUP for p in pins[cell]):
            conns = toks[1:-1]
            if len(conns) == len(pins[cell]):
                for i, p in enumerate(pins[cell]):
                    if p in SUP and conns[i] != SUP[p]:
                        conns[i] = SUP[p]; nfix += 1
                l = ' '.join([toks[0]] + conns + [cell])
    res.append(l)
open(out, 'w').write('\n'.join(res))
print(f'fix_cdl_io_supplies: {nfix} iovdd/iovss connections set, IOVDD/IOVSS ports on {top}')
