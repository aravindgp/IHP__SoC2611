#!/usr/bin/env python3
"""Floorplan + global-route overflow heat map (100 um bins) for one probe.
usage: fp_cong_picture.py <macros.txt> <place.pl> <congestion.rpt> <out.png> <title>"""
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

mac, pl, rpt, out, title = sys.argv[1:6]
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
COL = {'PCORE0': '#e07000', 'PCORE1': '#d6a300', 'PCORE2': '#2e9e63', 'PCORE3': '#3b7dd8', 'datapath': '#8a5fc9',
       'axi': '#c0392b', 'cpu': '#16a085', 'streams': '#7f8c8d', 'zcore': '#2c3e50', 'zmem': '#d35400',
       'camera': '#e84393', 'misc': '#999999'}


def block_of(n):
    n = n.replace('\\', '')
    if 'gen1_pcore_i' in n:
        return 'PCORE' + re.search(r'gen_reg\[(\d)', n).group(1)
    if n.startswith('soc_i/ztachip_inst/dp_'):
        return 'datapath'
    if n.startswith('soc_i/ztachip_inst/core_i/gen_stream'):
        return 'streams'
    if n.startswith('soc_i/ztachip_inst/core_i'):
        return 'zcore'
    if n.startswith('soc_i/ztachip_inst/'):
        return 'zmem'
    if n.startswith('soc_i/axi_'):
        return 'axi'
    if n.startswith('soc_i/gen_cpu') or n.startswith('soc_i/tcm_i') or n.startswith('soc_i/uart'):
        return 'cpu'
    if 'vstream' in n or 'cam' in n:
        return 'camera'
    return 'misc'


boxes = []
for l in open(pl):
    p = l.split()
    if len(p) == 4:
        w, h = S[p[0]]
        boxes.append((p[0], float(p[1]), float(p[2]), w, h, p[3]))
B = 100.0
n = int(6600 / B)
grid = np.zeros((n, n))
tot = 0
for b in open(rpt, errors='replace').read().split('violation type:')[1:]:
    m = re.search(r'overflow:(\d+)', b)
    bb = re.search(r'bbox = \(([\d.]+), ([\d.]+)\)', b)
    if m and bb:
        ov = int(m.group(1)); tot += ov
        grid[int(float(bb.group(2)) // B), int(float(bb.group(1)) // B)] += ov

fig, axes = plt.subplots(1, 2, figsize=(16, 8.2))
for ax in axes:
    ax.add_patch(Rectangle((140, 140), 6320, 6320, fc='#e8ecf0', ec='none'))
    ax.add_patch(Rectangle((340.32, 340.2), 5919.4, 5919.5, fc='white', ec='#333', lw=0.8))
    ax.add_patch(Rectangle((440, 440), 5720, 5720, fill=False, ec='#1f5fbf', lw=1, ls='--'))
    ax.set_xlim(0, 6600); ax.set_ylim(0, 6600); ax.set_aspect('equal'); ax.set_xlabel('µm')
for nme, x, y, w, h, o in boxes:
    axes[0].add_patch(Rectangle((x, y), w, h, fc=COL[block_of(nme)], ec='#222', lw=0.4, alpha=0.9))
    py = y + h - 6 if o in ('MX', 'R180') else y
    axes[0].add_patch(Rectangle((x, py), w, 6, fc='black', ec='none'))
axes[0].set_title(f'{len(boxes)} SRAMs by owner (black edge = pin side)')
im = axes[1].imshow(np.ma.masked_where(grid == 0, grid), origin='lower', extent=[0, 6600, 0, 6600], cmap='YlOrRd',
                    interpolation='nearest', alpha=0.95, zorder=2)
for nme, x, y, w, h, o in boxes:
    axes[1].add_patch(Rectangle((x, y), w, h, fill=False, ec='#555', lw=0.4, zorder=3))
axes[1].set_title(f'global-route overflow per 100 µm bin (report holds {tot:,} of the total)')
fig.colorbar(im, ax=axes[1], fraction=0.035, pad=0.02, label='overflow')
hs = [Rectangle((0, 0), 1, 1, fc=COL[b]) for b in COL]
axes[0].legend(hs, list(COL), loc='upper left', bbox_to_anchor=(0.0, -0.08), ncol=6, fontsize=8, frameon=False)
fig.suptitle(title, fontsize=14)
fig.subplots_adjust(left=0.04, right=0.98, top=0.9, bottom=0.12, wspace=0.1)
fig.savefig(out, dpi=100)
print('wrote', out)
