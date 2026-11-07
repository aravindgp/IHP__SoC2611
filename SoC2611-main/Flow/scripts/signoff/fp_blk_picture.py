#!/usr/bin/env python3
"""Two floorplan panels from .pl placements, macros coloured by owner, with optional placement-blockage rectangles
(red) per panel and a zoom box.  usage: fp_blk_picture.py <macros.txt> <out.png> <title> <label>=<pl>[:blk.txt] ..."""
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

mac, out, title = sys.argv[1:4]
panels = sys.argv[4:]
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
COL = {'PCORE': '#e0a040', 'dp': '#8a5fc9', 'axi': '#c0392b', 'cpu': '#16a085', 'stream': '#7f8c8d', 'core_i': '#2c3e50',
       'zt': '#d35400', 'cam': '#e84393', 'other': '#999999'}
NAMES = {'PCORE': 'PCORE', 'dp': 'datapath', 'axi': 'AXI', 'cpu': 'CPU', 'stream': 'streams', 'core_i': 'instr',
         'zt': 'ztachip mem', 'cam': 'camera', 'other': 'other'}


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


fig, axs = plt.subplots(1, len(panels), figsize=(8.5 * len(panels), 8.5))
if len(panels) == 1:
    axs = [axs]
for ax, spec in zip(axs, panels):
    label, rest = spec.split('=', 1)
    pl, _, blk = rest.partition(':')
    ax.add_patch(Rectangle((340, 340), 5920, 5920, fill=False, lw=1, ec='black'))
    ax.add_patch(Rectangle((0, 0), 6600, 6600, fill=False, lw=0.8, ec='gray'))
    for l in open(pl):
        p = l.split()
        if len(p) != 4:
            continue
        w, h = S[p[0]]
        x, y = float(p[1]), float(p[2])
        o = own(p[0])
        ax.add_patch(Rectangle((x, y), w, h, fc=COL[o], ec='black', lw=0.3, alpha=0.75))
        pin_y = y if p[3] in ('R0', 'MY') else y + h   # SRAM pins on the south edge in R0
        ax.plot([x, x + w], [pin_y, pin_y], color='black', lw=1.0)
    nb = 0
    if blk:
        for r in open(blk).read().replace(';', '\n').split('\n'):
            q = r.split()
            if len(q) == 4:
                x0, y0, x1, y1 = map(float, q)
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='red', ec='red', alpha=0.45, lw=1.5, hatch='//'))
                nb += 1
    ax.set_xlim(0, 6600); ax.set_ylim(0, 6600); ax.set_aspect('equal')
    ax.set_title(f'{label}' + (f'  ({nb} placement blockages, red)' if nb else ''))
    ax.set_xlabel('um')
handles = [Rectangle((0, 0), 1, 1, fc=COL[k], ec='black', lw=0.3) for k in COL]
axs[-1].legend(handles, [NAMES[k] for k in COL], loc='upper left', bbox_to_anchor=(1.01, 1.0), fontsize=9, title='macro owner')
fig.suptitle(title)
fig.tight_layout()
fig.savefig(out, dpi=110)
print('wrote', out)
