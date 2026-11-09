#!/usr/bin/env python3
"""Grok's checks on the d1 guide test: the markers in the elbow square and whether guided nets / guide boxes run
through it; history and strip class of the nets behind the remaining power markers; macros next to those markers.
usage: check_two_nets.py <lift_dir> <macros.txt> <net substring> [<net substring> ...]"""
import re
import sys

D, MAC = sys.argv[1], sys.argv[2]
SUBS = sys.argv[3:]
E = (2800, 2900, 2850, 2950)


def load(p):
    out = []
    for b in open(p, errors='replace').read().split('violation type:')[1:]:
        kind = b.split('\n')[0].strip()
        m = re.search(r'srcs:(.*)', b)
        bb = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', b)
        if not bb:
            continue
        srcs = m.group(1).split() if m else []
        out.append((kind, bb.group(5), tuple(float(bb.group(i)) for i in (1, 2, 3, 4)), srcs))
    return out


g = load(D + '/d1g_drc.rpt')
guided = [l.strip() for l in open(D + '/d1_pwr_nets.txt') if l.strip()]
print('== elbow square markers on d1g')
for k, l, bb, s in g:
    x = (bb[0] + bb[2]) / 2; y = (bb[1] + bb[3]) / 2
    if E[0] <= x <= E[2] and E[1] <= y <= E[3]:
        ns = [t[4:] for t in s if t.startswith('net:')]
        print(' ', k, l, bb, [(n[-40:], 'GUIDED' if n in guided else '') for n in ns])
print('== guide boxes touching the elbow square (+5um)')
for l in open(D + '/guides_d1pwr.txt'):
    p = l.split(); n = p[0]; x0, y0, x1, y1 = map(float, p[2:6])
    if x1 >= E[0] - 5 and x0 <= E[2] + 5 and y1 >= E[1] - 5 and y0 <= E[3] + 5:
        print(' ', n[-45:], p[1], x0, y0, x1, y1)
print('== power markers on d1g and their nets')
pm = []
for k, l, bb, s in g:
    if any(re.fullmatch(r'net:(?i:vdd\w*|vss\w*)', t) for t in s):
        print(' ', k, l, bb, ' '.join(t[-60:] for t in s)); pm.append((bb, s))
print('== the named nets in the d1 report (before guides)')
d = load(D + '/d1_drc.rpt')
for k, l, bb, s in d:
    if any(any(sub in t for sub in SUBS) for t in s):
        print(' ', k, l, bb, ' '.join(t[-50:] for t in s))
print('== strip classes')
for f in ('d1_strip.txt', 'd2_strip.txt'):
    for l in open(D + '/' + f):
        if any(sub in l for sub in SUBS):
            print(' ', f, l.strip()[-140:])
print('== macros within 6 um of the power markers')
wh = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(MAC) if len(l.split()) == 4}
for l in open(D + '/d1_place.pl'):
    p = l.split()
    if len(p) != 4 or p[0] not in wh:
        continue
    x, y = float(p[1]), float(p[2]); w, h = wh[p[0]]
    for bb, s in pm:
        mx = (bb[0] + bb[2]) / 2; my = (bb[1] + bb[3]) / 2
        if x - 6 <= mx <= x + w + 6 and y - 6 <= my <= y + h + 6:
            print(' ', (mx, my), p[0][-60:], p[3], 'box', x, y, round(x + w, 2), round(y + h, 2))
