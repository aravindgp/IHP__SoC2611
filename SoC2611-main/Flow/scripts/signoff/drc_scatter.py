#!/usr/bin/env python3
"""Scatter of the Short markers of a check_drc report over the macro outlines of a placement: power shorts (VDD/VSS
involved) in red, other shorts in blue; optional zoom window.
usage: drc_scatter.py <drc.rpt> <macros.txt> <place.pl> <out.png> <title> [x0 y0 x1 y1]"""
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

fn, mac, pl, out, title = sys.argv[1:6]
win = [float(v) for v in sys.argv[6:10]] if len(sys.argv) >= 10 else None
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
P = {}
for l in open(pl):
    p = l.split()
    if len(p) == 4 and p[0] in S:
        P[p[0]] = (float(p[1]), float(p[2]), S[p[0]][0], S[p[0]][1], p[3])
pw, ot = [], []
typ = ''
srcs = ''
for l in open(fn):
    if l.startswith('violation type:'):
        typ = l.split(':', 1)[1].strip()
    elif l.strip().startswith('srcs:'):
        srcs = l
    elif 'bbox' in l and typ == 'Short':
        m = re.search(r'\(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', l)
        if not m:
            continue
        x = (float(m.group(1)) + float(m.group(3))) / 2
        y = (float(m.group(2)) + float(m.group(4))) / 2
        (pw if ('net:VDD' in srcs or 'net:VSS' in srcs) else ot).append((x, y))
fig, ax = plt.subplots(figsize=(11, 11) if not win else (10, 10 * (win[3] - win[1]) / (win[2] - win[0])))
for n, (x, y, w, h, o) in P.items():
    ax.add_patch(Rectangle((x, y), w, h, fc='#dddddd', ec='#555555', lw=0.5))
    if win and w > 150 and (x + w > win[0] and x < win[2] and y + h > win[1] and y < win[3]):
        s = n.replace('soc_i/', '').split('/')
        ax.text(x + 3, y + 3, s[-1].split('_u')[0] + ' ' + o + ' (' + '/'.join(s[-3:-1])[-28:] + ')', fontsize=6, va='bottom')
if ot:
    ax.scatter(*zip(*ot), s=1.5, c='#3366cc', label=f'other shorts ({len(ot)})')
if pw:
    ax.scatter(*zip(*pw), s=1.5, c='#cc2200', label=f'shorts with VDD/VSS ({len(pw)})')
ax.add_patch(Rectangle((340, 340), 5920, 5920, fill=False, ec='k', lw=0.8))
ax.set_xlim(*(win[0::2] if win else (0, 6600)))
ax.set_ylim(*(win[1::2] if win else (0, 6600)))
ax.set_aspect('equal')
ax.set_title(title)
ax.legend(loc='upper right', fontsize=8)
plt.tight_layout()
plt.savefig(out, dpi=150)
print(f'wrote {out}: power shorts {len(pw)}, other {len(ot)}')
