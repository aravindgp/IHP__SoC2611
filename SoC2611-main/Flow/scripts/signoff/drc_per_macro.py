#!/usr/bin/env python3
"""Per-macro count of the Metal4/TopMetal1 Short markers (VDD/VSS involved) whose centre lies inside a macro outline.
usage: drc_per_macro.py <drc.rpt> <macros.txt> <place.pl> [top=25]"""
import collections
import re
import sys

fn, mac, pl = sys.argv[1:4]
top = int(sys.argv[4]) if len(sys.argv) > 4 else 25
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
P = {}
for l in open(pl):
    p = l.split()
    if len(p) == 4 and p[0] in S:
        P[p[0]] = (float(p[1]), float(p[2]), float(p[1]) + S[p[0]][0], float(p[2]) + S[p[0]][1])
cnt = collections.Counter()
nets = collections.defaultdict(set)
typ = ''
srcs = ''
for l in open(fn):
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
        lay = m.group(5)
        if lay not in ('Metal4', 'TopMetal1'):
            continue
        for n, (x0, y0, x1, y1) in P.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                cnt[(n, lay)] += 1
                for s in srcs.split():
                    if s.startswith('net:') and s not in ('net:VDD', 'net:VSS'):
                        nets[(n, lay)].add(s[4:])
                break
print(f'{sum(cnt.values())} power shorts inside macros ({len(cnt)} macro/layer pairs)')
for (n, lay), c in cnt.most_common(top):
    print(f'{c:5d} {lay:9s} nets={len(nets[(n, lay)]):3d} {n.replace("soc_i/", "")} @ {P[n][0]:.0f},{P[n][1]:.0f}')
