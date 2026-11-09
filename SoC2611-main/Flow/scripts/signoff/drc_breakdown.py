#!/usr/bin/env python3
"""Breakdown of a TritonRoute DRC report: kinds, kind/layer, kind/class/location (supply, vs macro instance,
signal-signal; inside a macro outline or not), the elbow square share, 500 um hotspots.
usage: drc_breakdown.py <drc.rpt> <macros.txt> <place.pl> [ex0 ey0 ex1 ey1]"""
import collections
import re
import sys

rpt, mac_f, pl_f = sys.argv[1:4]
E = [float(v) for v in sys.argv[4:8]] if len(sys.argv) > 7 else [2800, 2900, 2850, 2950]
wh = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac_f) if len(l.split()) == 4}
macs = []
for l in open(pl_f):
    p = l.split()
    if len(p) == 4 and p[0] in wh:
        w, h = wh[p[0]]; macs.append((float(p[1]), float(p[2]), float(p[1]) + w, float(p[2]) + h))
def inside(x, y): return any(a <= x <= c and b <= y <= d for a, b, c, d in macs)
txt = open(rpt, errors='replace').read()
kinds = collections.Counter(); lay = collections.Counter(); cat = collections.Counter(); cells = collections.Counter()
elbow = 0; nets = set(); elbow_nets = set()
for b in txt.split('violation type:')[1:]:
    kind = b.split('\n')[0].strip(); kinds[kind] += 1
    m = re.search(r'srcs:(.*)', b); bb = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', b)
    if not bb: continue
    x = (float(bb.group(1)) + float(bb.group(3))) / 2; y = (float(bb.group(2)) + float(bb.group(4))) / 2; layer = bb.group(5)
    lay[(kind, layer)] += 1
    srcs = m.group(1).split() if m else []
    ns = [s[4:] for s in srcs if s.startswith('net:')]
    sup = [s for s in ns if re.fullmatch(r'(?i)(vdd\w*|vss\w*)', s.split('/')[-1])]
    where = 'in-macro' if inside(x, y) else 'outside'
    k = 'supply' if sup else ('vs-macro-inst' if any(s.startswith('inst:') for s in srcs) else ('signal-signal' if len(ns) >= 2 else 'other'))
    cat[(kind, k, where)] += 1
    cells[(int(x // 500) * 500, int(y // 500) * 500)] += 1
    for s in ns:
        if s not in sup: nets.add(s)
    if E[0] <= x <= E[2] and E[1] <= y <= E[3]:
        elbow += 1
        for s in ns:
            if s not in sup: elbow_nets.add(s)
print(f'# {rpt}')
print('total markers', sum(kinds.values()), '| kinds', dict(kinds))
print(f'elbow square {E}: {elbow} markers on {len(elbow_nets)} nets; distinct nets overall {len(nets)}')
print('by kind/class/location:')
for k, v in cat.most_common(): print(f'  {v:5d} {k}')
print('by kind/layer:')
for k, v in lay.most_common(): print(f'  {v:5d} {k}')
print('hotspots (500 um cells):', cells.most_common(8))
