#!/usr/bin/env python3
"""Nets to strip and re-route after a macro shift: every net in a Short marker that involves a macro instance or a
supply net, or that lies inside a window; nets listed in an exclude file (e.g. the explicitly guided ones) are kept.
usage: overlap_nets.py <drc.rpt> x0 y0 x1 y1 [exclude_guides.txt] > nets.txt"""
import re
import sys

rpt = sys.argv[1]; x0, y0, x1, y1 = [float(v) for v in sys.argv[2:6]]
excl = set()
if len(sys.argv) > 6:
    for l in open(sys.argv[6]):
        p = l.split()
        if p: excl.add(p[0])
nets = set(); why = {'macro': 0, 'supply': 0, 'window': 0}
for b in open(rpt, errors='replace').read().split('violation type:')[1:]:
    if b.split('\n')[0].strip() != 'Short': continue
    m = re.search(r'srcs:(.*)', b); bb = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)', b)
    if not m or not bb: continue
    srcs = m.group(1).split()
    ns = [s[4:] for s in srcs if s.startswith('net:')]
    sup = [s for s in ns if re.fullmatch(r'(?i)(vdd\w*|vss\w*)', s.split('/')[-1])]
    sig = [s for s in ns if s not in sup]
    cx = (float(bb.group(1)) + float(bb.group(3))) / 2; cy = (float(bb.group(2)) + float(bb.group(4))) / 2
    take = None
    if any(s.startswith('inst:') for s in srcs): take = 'macro'
    elif sup: take = 'supply'
    elif x0 <= cx <= x1 and y0 <= cy <= y1: take = 'window'
    if take:
        why[take] += 1
        for s in sig:
            if s not in excl: nets.add(s)
for n in sorted(nets): print(n)
print(f'# {len(nets)} nets to re-route; markers by reason {why}; excluded {len(excl)} guided nets', file=sys.stderr)
