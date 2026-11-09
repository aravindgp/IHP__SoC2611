#!/usr/bin/env python3
"""All signal nets with markers inside a box of a DRC report, with marker counts; writes the net list (one per line)
for the next strip / guide step.  usage: nets_in_box.py <drc.rpt> x0 y0 x1 y1 <out_nets.txt>"""
import collections
import re
import sys

rpt = sys.argv[1]; B = [float(v) for v in sys.argv[2:6]]; out = sys.argv[6]
nets = collections.Counter(); n = 0
for b in open(rpt, errors='replace').read().split('violation type:')[1:]:
    m = re.search(r'srcs:(.*)', b)
    bb = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', b)
    if not bb:
        continue
    x = (float(bb.group(1)) + float(bb.group(3))) / 2; y = (float(bb.group(2)) + float(bb.group(4))) / 2
    if not (B[0] <= x <= B[2] and B[1] <= y <= B[3]):
        continue
    n += 1
    for s in (m.group(1).split() if m else []):
        if s.startswith('net:') and not re.fullmatch(r'(?i)(vdd\w*|vss\w*)', s[4:].split('/')[-1]):
            nets[s[4:]] += 1
open(out, 'w').write(''.join(k + '\n' for k, _ in nets.most_common()))
print(f'# {rpt}: {n} markers in {B} on {len(nets)} nets -> {out}')
for k, v in nets.most_common(10):
    print(f'  {v:4d} {k[-70:]}')
