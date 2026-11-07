#!/usr/bin/env python3
"""Picture of windowed check_drc maps (drc_grid.tcl logs) over the macro floorplan: left a full-chip map, right a zoom.
usage: drc_grid_picture.py <macros.txt> <place.pl> <full_grid.log> <zoom_grid.log> <out.png> <title>"""
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

mac, pl, full, zoom, out, title = sys.argv[1:7]
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
COL = {'PCORE': '#e0a040', 'dp': '#8a5fc9', 'axi': '#c0392b', 'cpu': '#16a085', 'stream': '#7f8c8d', 'core_i': '#2c3e50',
       'zt': '#d35400', 'cam': '#e84393', 'other': '#999999'}


def own(n):
    if 'pcore' in n: return 'PCORE'
    if '/dp_' in n: return 'dp'
    if 'axi_' in n: return 'axi'
    if 'gen_cpu' in n or 'tcm_i' in n or 'uart' in n: return 'cpu'
    if 'gen_stream' in n: return 'stream'
    if 'core_i/instr' in n: return 'core_i'
    if 'vstream' in n: return 'cam'
    if 'ztachip' in n: return 'zt'
    return 'other'


boxes = []
for l in open(pl):
    p = l.split()
    if len(p) == 4:
        w, h = S[p[0]]
        boxes.append((p[0], float(p[1]), float(p[2]), w, h, p[3]))


def windows(fn):
    return [(int(r[1]), int(r[2]), int(r[3]), int(r[4]), int(r[5])) for r in
            (l.split() for l in open(fn)) if r and r[0] == 'DRC_GRID']


fig, axes = plt.subplots(1, 2, figsize=(17, 8.5))
for ax, fn, (x0, y0, x1, y1), sub in ((axes[0], full, (0, 0, 6600, 6600), 'whole chip, 600 µm windows'),
                                      (axes[1], zoom, (2550, 1950, 3550, 2950), 'zoom, 150 µm windows')):
    ws = windows(fn)
    mx = max(w[4] for w in ws)
    cm = plt.get_cmap('YlOrRd')
    for wx0, wy0, wx1, wy1, n in ws:
        if n:
            ax.add_patch(Rectangle((wx0, wy0), wx1 - wx0, wy1 - wy0, fc=cm(min(1.0, n / mx)), ec='none', zorder=1))
            if (n > 0.08 * mx and ax is axes[0]) or (ax is axes[1] and n > 300):
                ax.text((wx0 + wx1) / 2, (wy0 + wy1) / 2, f'{n:,}', ha='center', va='center', fontsize=7 if ax is axes[0] else 8,
                        color='black', zorder=4)
    for n, x, y, w, h, o in boxes:
        ax.add_patch(Rectangle((x, y), w, h, fill=False, ec=COL[own(n)], lw=0.8 if ax is axes[1] else 0.4, zorder=3))
        if ax is axes[1] and x + w > x0 and x < x1 and y + h > y0 and y < y1:
            py = y + h - 4 if o in ('MX', 'R180') else y
            ax.add_patch(Rectangle((x, py), w, 4, fc='black', ec='none', zorder=4))
    ax.add_patch(Rectangle((340.32, 340.2), 5919.4, 5919.5, fill=False, ec='#333', lw=0.8, zorder=2))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_xlabel('µm'); ax.set_title(sub)
axes[0].add_patch(Rectangle((2550, 1950), 1000, 1000, fill=False, ec='blue', lw=1.5, ls='--', zorder=5))
hs = [Rectangle((0, 0), 1, 1, fill=False, ec=COL[k], lw=2) for k in COL]
axes[1].legend(hs, ['PCORE', 'datapath', 'AXI', 'CPU', 'streams', 'instr', 'ztachip mem', 'camera', 'other'],
               loc='upper left', bbox_to_anchor=(1.01, 1.0), fontsize=8, title='macro owner')
fig.suptitle(title, fontsize=13)
fig.subplots_adjust(left=0.04, right=0.88, top=0.9, bottom=0.08, wspace=0.12)
fig.savefig(out, dpi=100)
print('wrote', out)
