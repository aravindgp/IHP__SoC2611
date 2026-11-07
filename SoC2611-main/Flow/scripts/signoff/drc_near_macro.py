#!/usr/bin/env python3
"""For the Short markers that involve VDD/VSS (or all markers with --all), histogram the distance from the marker
centre to the nearest macro outline (negative = inside a macro), per layer, and name the macro owners.
usage: drc_near_macro.py <drc.rpt> <macros.txt> <place.pl> [--all]"""
import collections
import re
import sys

fn, mac, pl = sys.argv[1:4]
allm = '--all' in sys.argv
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
boxes = []
for l in open(pl):
    p = l.split()
    if len(p) == 4:
        w, h = S[p[0]]
        boxes.append((p[0], float(p[1]), float(p[2]), float(p[1]) + w, float(p[2]) + h))


def dist(cx, cy):
    best = 1e9; who = None
    for n, x0, y0, x1, y1 in boxes:
        dx = max(x0 - cx, 0, cx - x1); dy = max(y0 - cy, 0, cy - y1)
        d = (dx * dx + dy * dy) ** 0.5
        if dx == 0 and dy == 0:
            d = -min(cx - x0, x1 - cx, cy - y0, y1 - cy)
        if d < best:
            best = d; who = n
    return best, who


H = collections.defaultdict(collections.Counter)
own = collections.defaultdict(collections.Counter)
typ = None; pw = False
for l in open(fn):
    if l.startswith('violation type:'):
        typ = l.split(':', 1)[1].strip(); pw = False
    elif l.strip().startswith('srcs:'):
        pw = ('net:VDD' in l) or ('net:VSS' in l)
    m = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', l)
    if m and typ == 'Short' and (pw or allm):
        x0, y0, x1, y1 = map(float, m.groups()[:4]); lay = m.group(5)
        d, who = dist((x0 + x1) / 2, (y0 + y1) / 2)
        if d < 0:
            b = 'in<2' if -d < 2 else 'in<5' if -d < 5 else 'in<10' if -d < 10 else 'in>=10'
        else:
            b = '<2' if d < 2 else '<5' if d < 5 else '<10' if d < 10 else '<20' if d < 20 else '<50' if d < 50 else '>=50'
        H[lay][b] += 1
        if d < 5:
            own[lay][who.split('/')[1] if who.startswith('soc_i/') else who[:30]] += 1
for lay in sorted(H):
    print(f'--- {lay}: {sum(H[lay].values())} markers; depth inside / distance outside the nearest macro outline (um): ' +
          ' '.join(f'{k}:{H[lay][k]}' for k in ('in>=10', 'in<10', 'in<5', 'in<2', '<2', '<5', '<10', '<20', '<50', '>=50')))
    print('    macros (<5 um) by block: ' + ', '.join(f'{k} {v}' for k, v in own[lay].most_common(6)))
