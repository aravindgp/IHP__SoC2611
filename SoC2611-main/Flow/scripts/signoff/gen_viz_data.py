#!/usr/bin/env python3
"""Data file for the H10-vs-H12 explainer page: macros of both placements (um, owner), placement blockages, the
global-route guide boxes inside each macro (from guides_in_macros pair dumps), and 600 um DRC windows.
usage: gen_viz_data.py <macros.txt> <H10.pl> <H12.pl> <blk.txt> <H10_pairs.txt> <H12_pairs.txt> <H10_grid.log> <out.js>"""
import collections
import json
import sys

mac, pl10, pl12, blk, p10, p12, g10, out = sys.argv[1:9]
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}


def own(n):
    if 'pcore' in n: return 'PCORE'
    if '/dp_' in n: return 'datapath'
    if 'axi_' in n: return 'AXI'
    if 'gen_cpu' in n or 'tcm_i' in n or 'uart' in n: return 'CPU'
    if 'gen_stream' in n: return 'streams'
    if 'core_i/instr' in n: return 'instr'
    if 'vstream' in n: return 'camera'
    if 'ztachip' in n: return 'ztachip mem'
    return 'other'


def short(n):
    p = n.replace('soc_i/', '').split('/')
    return '/'.join(p[:2] + [p[-1]]) if len(p) > 3 else n


def read(fn):
    d = {}
    for l in open(fn):
        p = l.split()
        if len(p) == 4:
            d[p[0]] = (float(p[1]), float(p[2]), p[3])
    return d


def pairs(fn):
    c = collections.Counter()
    try:
        for l in open(fn):
            p = l.split()
            if len(p) == 3:
                c[p[2]] += int(p[0])
    except FileNotFoundError:
        pass
    return c


h10, h12 = read(pl10), read(pl12)
c10, c12 = pairs(p10), pairs(p12)
macros = []
for i, n in enumerate(sorted(h10)):
    w, h = S[n]
    x0, y0, o0 = h10[n]
    x1, y1, o1 = h12.get(n, h10[n])
    macros.append(dict(i=i, n=short(n), o=own(n), w=round(w, 1), h=round(h, 1),
                       a=[round(x0, 1), round(y0, 1), o0], b=[round(x1, 1), round(y1, 1), o1],
                       g10=c10.get(n, 0), g12=c12.get(n, 0), moved=(abs(x0 - x1) > 1 or abs(y0 - y1) > 1)))
blks = [[float(v) for v in r.split()] for r in open(blk).read().replace(';', '\n').split('\n') if len(r.split()) == 4]
grid = []
for l in open(g10):
    p = l.split()
    if p and p[0] == 'DRC_GRID':
        grid.append([int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5])])
data = dict(macros=macros, blockages=blks, grid10=grid, core=[340.3, 340.2, 6259.7, 6259.7], die=[0, 0, 6600, 6600],
            totals=dict(g10=sum(c10.values()), g12=sum(c12.values())))
with open(out, 'w') as fh:
    fh.write('window.FP_DATA = ' + json.dumps(data, separators=(',', ':')) + ';\n')
print(f'wrote {out}: {len(macros)} macros, {sum(1 for m in macros if m["moved"])} moved, '
      f'guide boxes inside macros H10 {data["totals"]["g10"]} H12 {data["totals"]["g12"]}, {len(grid)} windows')
