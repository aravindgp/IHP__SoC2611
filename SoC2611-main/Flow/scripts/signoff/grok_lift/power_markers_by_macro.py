#!/usr/bin/env python3
"""Where the supply markers (net vs VDD/VSS) of a DRC report sit: per macro instance (containing outline, or 'outside'),
and how many lie within 3 um of the macro's pin edge (south for R0/MY, north for MX/R180).
usage: power_markers_by_macro.py <drc.rpt> <macros.txt> <place.pl> [top=12]"""
import collections
import re
import sys

rpt, mac_f, pl_f = sys.argv[1:4]; top = int(sys.argv[4]) if len(sys.argv) > 4 else 12
wh = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac_f) if len(l.split()) == 4}
macs = []
for l in open(pl_f):
    p = l.split()
    if len(p) == 4 and p[0] in wh:
        w, h = wh[p[0]]; macs.append((p[0], float(p[1]), float(p[2]), float(p[1]) + w, float(p[2]) + h, p[3]))
per = collections.Counter(); pin_edge = collections.Counter(); layers = collections.Counter(); nets = set(); n = 0
for b in open(rpt, errors='replace').read().split('violation type:')[1:]:
    m = re.search(r'srcs:(.*)', b)
    bb = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', b)
    if not (m and bb):
        continue
    srcs = m.group(1).split()
    if not any(re.fullmatch(r'net:(?i:vdd\w*|vss\w*)', s) for s in srcs):
        continue
    n += 1; layers[bb.group(5)] += 1
    for s in srcs:
        if s.startswith('net:') and not re.fullmatch(r'net:(?i:vdd\w*|vss\w*)', s):
            nets.add(s[4:])
    x = (float(bb.group(1)) + float(bb.group(3))) / 2; y = (float(bb.group(2)) + float(bb.group(4))) / 2
    hit = 'outside'
    for name, x0, y0, x1, y1, ori in macs:
        if x0 - 0.5 <= x <= x1 + 0.5 and y0 - 0.5 <= y <= y1 + 0.5:
            hit = name[-48:] + ' ' + ori
            edge = y1 if ori in ('MX', 'R180') else y0
            if abs(y - edge) <= 3:
                pin_edge[hit] += 1
            break
    per[hit] += 1
print(f'# {rpt.split("/")[-1]}: {n} supply markers on {len(nets)} nets; layers {dict(layers)}')
for k, v in per.most_common(top):
    print(f'  {v:4d} (pin edge {pin_edge[k]:3d})  {k}')
