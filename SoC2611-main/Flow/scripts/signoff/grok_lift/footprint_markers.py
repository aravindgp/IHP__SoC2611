#!/usr/bin/env python3
"""Markers inside / along a box (default: slice[27]'s new footprint +1 um) of one or more DRC reports:
(kind, layer, class) counts, the y-rows they sit on, and the nets with most markers.
usage: footprint_markers.py x0 y0 x1 y1 <drc.rpt> [<drc.rpt> ...]"""
import collections
import re
import sys

B = [float(v) for v in sys.argv[1:5]]
for rpt in sys.argv[5:]:
    c = collections.Counter(); rows = collections.Counter(); nets = collections.Counter(); edge = collections.Counter()
    for b in open(rpt, errors='replace').read().split('violation type:')[1:]:
        kind = b.split('\n')[0].strip()
        m = re.search(r'srcs:(.*)', b)
        bb = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', b)
        if not bb:
            continue
        x = (float(bb.group(1)) + float(bb.group(3))) / 2; y = (float(bb.group(2)) + float(bb.group(4))) / 2
        if not (B[0] <= x <= B[2] and B[1] <= y <= B[3]):
            continue
        srcs = m.group(1).split() if m else []
        ns = [s[4:] for s in srcs if s.startswith('net:')]
        sup = [s for s in ns if re.fullmatch(r'(?i)(vdd\w*|vss\w*)', s.split('/')[-1])]
        k = 'supply' if sup else ('vs-inst' if any(s.startswith('inst:') for s in srcs) else ('obstruction' if any(s.startswith('obstruction') for s in srcs) else 'signal-signal'))
        c[(kind, bb.group(5), k)] += 1
        rows[round(y, 0)] += 1
        for s in ns:
            if s not in sup:
                nets[s[-55:]] += 1
        if B[1] <= y <= B[1] + 2:
            edge[(kind, bb.group(5), k)] += 1
    print(f'# {rpt}: {sum(c.values())} markers in box {B}')
    for k, v in c.most_common(12):
        print(f'  {v:5d} {k}')
    print('  bottom 2 um strip:', dict(edge))
    print('  rows (y rounded):', sorted(rows.items())[:14])
    print('  top nets:', nets.most_common(8))
