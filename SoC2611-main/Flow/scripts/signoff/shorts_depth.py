#!/usr/bin/env python3
"""Depth profile of the power shorts inside one macro: distance from the macro's pin edge (north for MX/R180,
south for R0/MY) in 5 um bins, and how many are on the macro's own nets (pin access) vs foreign nets (crossings).
usage: shorts_depth.py <drc.rpt> <macro_substring> <macros.txt> <place.pl>"""
import collections
import re
import sys

rpt, key, mac, pl = sys.argv[1:5]
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
for l in open(pl):
    p = l.split()
    if len(p) == 4 and key in p[0] and p[0] in S:
        name, x0, y0, o = p[0], float(p[1]), float(p[2]), p[3]
        x1, y1 = x0 + S[p[0]][0], y0 + S[p[0]][1]
pin_north = o in ('MX', 'R180')
own_prefix = name.rsplit('/', 1)[0]   # the macro wrapper hierarchy
print(f'{name.replace("soc_i/", "")} {o} outline {x0:.0f},{y0:.0f}-{x1:.0f},{y1:.0f}  pins {"north" if pin_north else "south"}')
depth = collections.Counter()
own = collections.Counter()
typ = srcs = ''
for l in open(rpt):
    if l.startswith('violation type:'):
        typ = l.split(':', 1)[1].strip()
    elif l.strip().startswith('srcs:'):
        srcs = l
    elif 'bbox' in l and typ == 'Short' and ('net:VDD' in srcs or 'net:VSS' in srcs):
        m = re.search(r'\(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', l)
        if not m:
            continue
        x = (float(m.group(1)) + float(m.group(3))) / 2
        y = (float(m.group(2)) + float(m.group(4))) / 2
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        d = (y1 - y) if pin_north else (y - y0)
        depth[int(d // 5) * 5] += 1
        nets = [s[4:] for s in srcs.split() if s.startswith('net:') and s not in ('net:VDD', 'net:VSS')]
        own['own' if any(n.startswith(own_prefix) for n in nets) else 'foreign'] += 1
print('depth from the pin edge (um bin: shorts):', ' '.join(f'{k}:{v}' for k, v in sorted(depth.items())))
print('own-pin nets vs foreign nets:', dict(own))
