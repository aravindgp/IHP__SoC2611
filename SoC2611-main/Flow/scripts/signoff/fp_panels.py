#!/usr/bin/env python3
"""Side-by-side floorplan panels from engine macro_placements JSONs (origin + orient) or MPL .pl files (lower-left),
macros coloured by owner block.  usage: fp_panels.py <macros.txt> <out.png> <title> <label>=<file.json|.pl> ..."""
import json
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

mac, out, title = sys.argv[1:4]
panels = [a.split('=', 1) for a in sys.argv[4:]]
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
CORE = (340.32, 340.2, 6259.68, 6259.68)
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


def boxes(fn):
    res = []
    if fn.endswith('.pl'):
        for ln in open(fn):
            p = ln.split()
            if len(p) != 4:
                continue
            n, x, y, o = p[0], float(p[1]), float(p[2]), p[3]
            w, h = S[n]
            res.append((n, x, y, w, h, o))
    else:
        for e in json.load(open(fn))['macro_placements']:
            n, ox, oy, o = e.rsplit(':', 3)
            w, h = S[n]
            ox, oy = float(ox), float(oy)
            x = ox - (w if o in ('MY', 'R180') else 0)
            y = oy - (h if o in ('MX', 'R180') else 0)
            res.append((n, x, y, w, h, o))
    return res


fig, axes = plt.subplots(1, len(panels), figsize=(7.2 * len(panels), 8))
if len(panels) == 1:
    axes = [axes]
for ax, (lab, fn) in zip(axes, panels):
    ax.add_patch(Rectangle((140, 140), 6320, 6320, fc='#e8ecf0', ec='none'))
    ax.add_patch(Rectangle((CORE[0], CORE[1]), CORE[2] - CORE[0], CORE[3] - CORE[1], fc='white', ec='#333', lw=0.8))
    ax.add_patch(Rectangle((440, 440), 5720, 5720, fill=False, ec='#1f5fbf', lw=1, ls='--'))
    bx = boxes(fn)
    for n, x, y, w, h, o in bx:
        ax.add_patch(Rectangle((x, y), w, h, fc=COL[block_of(n)], ec='#222', lw=0.4, alpha=0.85))
        py = y + h - 6 if o in ('MX', 'R180') else y
        ax.add_patch(Rectangle((x, py), w, 6, fc='black', ec='none'))
    ax.set_xlim(0, 6600); ax.set_ylim(0, 6600); ax.set_aspect('equal'); ax.set_xlabel('µm')
    ax.set_title(f'{lab}  ({len(bx)} SRAMs)')
hs = [Rectangle((0, 0), 1, 1, fc=COL[b]) for b in COL]
axes[-1].legend(hs, list(COL), loc='upper left', bbox_to_anchor=(1.01, 1.0), fontsize=9, title='owner')
fig.suptitle(title, fontsize=14)
fig.subplots_adjust(left=0.03, right=0.93, top=0.88, bottom=0.08, wspace=0.12)
fig.savefig(out, dpi=100)
print('wrote', out)
