#!/usr/bin/env python3
"""For the nets that have Short markers inside one macro (from a check_drc report), check whether their global-route
guides overlap that macro's outline on any layer: do the detailed-route shorts inside the macro come from guides
that enter it, or does the detailed router enter without a guide?
usage: shorts_vs_guides.py <drc.rpt> <route.guide> <macro_substring> <macros.txt> <place.pl> [margin_um=0]"""
import collections
import re
import sys

rpt, guide, key, mac, pl = sys.argv[1:6]
margin = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
box = None
for l in open(pl):
    p = l.split()
    if len(p) == 4 and key in p[0] and p[0] in S:
        box = (float(p[1]), float(p[2]), float(p[1]) + S[p[0]][0], float(p[2]) + S[p[0]][1])
        name = p[0]
if box is None:
    sys.exit(f'no macro matching {key}')
x0, y0, x1, y1 = box
print(f'macro {name.replace("soc_i/", "")} outline {x0:.0f},{y0:.0f} - {x1:.0f},{y1:.0f}')
nets = collections.Counter()
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
        if x0 <= x <= x1 and y0 <= y <= y1:
            for s in srcs.split():
                if s.startswith('net:') and s not in ('net:VDD', 'net:VSS'):
                    nets[s[4:]] += 1
print(f'{sum(nets.values())} power shorts inside it on {len(nets)} nets')
# guides of those nets overlapping the (shrunk) outline, per layer
ix0, iy0, ix1, iy1 = x0 - margin, y0 - margin, x1 + margin, y1 + margin
per_net = collections.defaultdict(collections.Counter)
cur = None
want = set(nets)
with open(guide) as fh:
    for l in fh:
        if l[0] == '(':
            continue
        if l[0] == ')':
            cur = None
            continue
        p = l.split()
        if len(p) == 1:
            cur = p[0] if p[0] in want else None
        elif cur and len(p) == 5:
            gx0, gy0, gx1, gy1 = (float(v) / 1000.0 for v in p[:4])
            if gx0 < ix1 and gx1 > ix0 and gy0 < iy1 and gy1 > iy0:
                per_net[cur][p[4]] += 1
with_g = [n for n in nets if per_net[n]]
print(f'nets whose guides overlap the outline (margin {margin:+.0f} um): {len(with_g)} of {len(nets)}')
lay = collections.Counter()
for n in with_g:
    lay.update(per_net[n])
print('  guide boxes overlapping, per layer:', dict(lay))
print('nets with shorts but NO guide overlapping the outline:')
for n, c in nets.most_common():
    if not per_net[n]:
        print(f'  {c:4d} {n.replace("soc_i/", "")}')
