#!/usr/bin/env python3
"""Floorplan picture (SVG) from dump_floorplan.tcl: die, core, pad ring, PDN stripes, every macro coloured by owner
(PCORE 0-3, AXI fabric, CPU, ztachip data path, other), optional dashed outlines of macros at a previous position.
usage: floorplan_svg.py <floorplan.txt> <out.svg> [title] [prev_floorplan.txt]"""
import collections
import re
import sys

src, out = sys.argv[1:3]
title = sys.argv[3] if len(sys.argv) > 3 else 'DGrid-SoC1 floorplan'
prev = sys.argv[4] if len(sys.argv) > 4 else None
S = 0.22  # px per um
PAD = 90


def owner(name):
    m = re.search(r'gen_reg\\?\[(\d)\\?\]_gen1_pcore', name)
    if m:
        return f'PCORE {m.group(1)}'
    n = name.lower()
    if 'gen_stream' in n or 'instr_i' in n or 'dp_' in n:
        return 'ztachip data path'
    if 'axi' in n:
        return 'AXI fabric'
    if 'vex' in n or 'cpu' in n or 'riscv' in n or 'tcm' in n or 'cache' in n:
        return 'CPU'
    if 'ztachip' in n:
        return 'ztachip data path'
    return 'other'


COL = {'PCORE 0': '#e07000', 'PCORE 1': '#d6a300', 'PCORE 2': '#2e9e63', 'PCORE 3': '#3b7dd8', 'AXI fabric': '#8a5fc9',
       'CPU': '#c43f5e', 'ztachip data path': '#4a9bb5', 'other': '#8c98a4'}


def load(path):
    d = dict(die=None, core=None, macros=[], pads=[], pdn=[])
    for ln in open(path):
        p = ln.split()
        if not p:
            continue
        if p[0] == 'DIE':
            d['die'] = [int(v) / 1000 for v in p[1:5]]
        elif p[0] == 'CORE':
            d['core'] = [int(v) / 1000 for v in p[1:5]]
        elif p[0] == 'MACRO':
            d['macros'].append(([int(v) / 1000 for v in p[1:5]], p[5], p[6], p[7]))
        elif p[0] == 'PAD':
            d['pads'].append(([int(v) / 1000 for v in p[1:5]], p[5]))
        elif p[0] == 'PDN':
            d['pdn'].append((p[1], p[2], [int(v) / 1000 for v in p[3:7]]))
    return d


d = load(src)
die = d['die']
W, H = die[2] - die[0], die[3] - die[1]
w, h = int(W * S) + 2 * PAD, int(H * S) + PAD + 150


def px(x):
    return PAD + (x - die[0]) * S


def py(y):
    return PAD + (die[3] - y) * S


s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w + 260}" height="{h}" font-family="sans-serif" font-size="12">',
     f'<rect width="{w + 260}" height="{h}" fill="white"/>',
     f'<text x="{w / 2}" y="30" text-anchor="middle" font-size="20">{title}</text>',
     f'<rect x="{px(die[0])}" y="{py(die[3])}" width="{W * S}" height="{H * S}" fill="#f7f8fb" stroke="#333" stroke-width="1.2"/>']
core = d['core']
if core:
    s.append(f'<rect x="{px(core[0])}" y="{py(core[3])}" width="{(core[2]-core[0]) * S}" height="{(core[3]-core[1]) * S}" fill="none" stroke="#777" stroke-dasharray="4 3"/>')
# PDN stripes (wide rects only)
for net, lay, (x0, y0, x1, y1) in d['pdn']:
    c = '#d9534f' if net == 'VDD' else '#3b7dd8'
    s.append(f'<rect x="{px(x0):.1f}" y="{py(y1):.1f}" width="{max(0.4, (x1-x0) * S):.2f}" height="{max(0.4, (y1-y0) * S):.2f}" fill="{c}" fill-opacity="0.35"/>')
# pads
for (x0, y0, x1, y1), m in d['pads']:
    s.append(f'<rect x="{px(x0):.1f}" y="{py(y1):.1f}" width="{(x1-x0) * S:.2f}" height="{(y1-y0) * S:.2f}" fill="#e8ecf2" stroke="#9aa5b1" stroke-width="0.5"/>')
# previous macro positions
if prev:
    pd = load(prev)
    cur = {name: bb for bb, _, _, name in d['macros']}
    moved = 0
    for bb, _, _, name in pd['macros']:
        if name in cur and cur[name] != bb:
            moved += 1
            s.append(f'<rect x="{px(bb[0]):.1f}" y="{py(bb[3]):.1f}" width="{(bb[2]-bb[0]) * S:.2f}" height="{(bb[3]-bb[1]) * S:.2f}" fill="none" stroke="#c00" stroke-width="1" stroke-dasharray="5 3"/>')
# macros
counts = collections.Counter()
for (x0, y0, x1, y1), master, orient, name in d['macros']:
    o = owner(name)
    counts[o] += 1
    c = COL[o]
    s.append(f'<rect x="{px(x0):.1f}" y="{py(y1):.1f}" width="{(x1-x0) * S:.2f}" height="{(y1-y0) * S:.2f}" fill="{c}" fill-opacity="0.55" stroke="{c}" stroke-width="0.8"/>')
    short = master.replace('RM_IHPSG13_', '').replace('_bm_bist', '').replace('_c2', '').replace('_c3', '')
    if (x1 - x0) * S > 48 and (y1 - y0) * S > 14:
        s.append(f'<text x="{px((x0+x1)/2):.1f}" y="{py((y0+y1)/2) + 4:.1f}" text-anchor="middle" font-size="9" fill="#1c2b3a">{short}</text>')
# axes
for v in range(0, int(W) + 1, 1000):
    s.append(f'<text x="{px(v):.1f}" y="{py(die[1]) + 16}" text-anchor="middle" fill="#555">{v}</text>')
    s.append(f'<text x="{px(die[0]) - 8}" y="{py(v) + 4:.1f}" text-anchor="end" fill="#555">{v}</text>')
s.append(f'<text x="{px(W/2):.1f}" y="{py(die[1]) + 34}" text-anchor="middle" fill="#555">um</text>')
# legend
lx, ly = w + 20, PAD
s.append(f'<text x="{lx}" y="{ly - 12}" font-size="13" font-weight="bold">Macros by owner</text>')
for i, (o, c) in enumerate(COL.items()):
    if counts[o]:
        s.append(f'<rect x="{lx}" y="{ly + i * 20}" width="16" height="12" fill="{c}" fill-opacity="0.7"/>')
        s.append(f'<text x="{lx + 22}" y="{ly + i * 20 + 11}">{o}: {counts[o]}</text>')
ly2 = ly + 9 * 20
s.append(f'<rect x="{lx}" y="{ly2}" width="16" height="12" fill="#d9534f" fill-opacity="0.5"/><text x="{lx + 22}" y="{ly2 + 11}">VDD stripes (TM1)</text>')
s.append(f'<rect x="{lx}" y="{ly2 + 20}" width="16" height="12" fill="#3b7dd8" fill-opacity="0.5"/><text x="{lx + 22}" y="{ly2 + 31}">VSS stripes (TM1)</text>')
s.append(f'<rect x="{lx}" y="{ly2 + 40}" width="16" height="12" fill="#e8ecf2" stroke="#9aa5b1"/><text x="{lx + 22}" y="{ly2 + 51}">IO / pad cells: {len(d["pads"])}</text>')
if prev:
    s.append(f'<rect x="{lx}" y="{ly2 + 60}" width="16" height="12" fill="none" stroke="#c00" stroke-dasharray="5 3"/><text x="{lx + 22}" y="{ly2 + 71}">previous position ({moved} moved)</text>')
s.append(f'<text x="{w / 2}" y="{h - 40}" text-anchor="middle" fill="#445">{len(d["macros"])} IHP SRAM macros - {len(d["pads"])} IO cells - {len(d["pdn"])} PDN stripe segments drawn - die {W:.0f} x {H:.0f} um, core {core[0]:.0f}..{core[2]:.0f} um</text>')
s.append(f'<text x="{w / 2}" y="{h - 20}" text-anchor="middle" fill="#445">Placement + power grid done; detailed routing in progress (run F v5); DRC, fill, density pending.</text>')
s.append('</svg>')
open(out, 'w').write('\n'.join(s))
print('wrote', out, dict(counts))
