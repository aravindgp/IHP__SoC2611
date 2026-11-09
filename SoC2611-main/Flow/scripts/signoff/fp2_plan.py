#!/usr/bin/env python3
"""Hand floorplan (run G) for SoC2611 on SG13CMOS5L: macros grouped by the logic that drives them, packed in row
PAIRS whose signal-pin edges (SRAM pins are on the bottom edge in R0) face each other across a STRIP of standard-cell
rows (the logic that drives them sits right at the pins; no row crossing), BB between the pinless backs of
neighbouring pairs, G between macros in a row (vertical escape, kept free of cells by a placement blockage).  Regions per block are given in um
(usable core = core box minus BAND on all sides).  Writes the engine's macro_placements JSON (origin conversion per
orientation), a block summary, and a before/after PNG next to the current (run F7) floorplan.
usage: fp2_plan.py <place_F7.txt> <cellgroups_F7.txt> <out_prefix>"""
import json
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

U = 1000.0
CORE = (340.32, 340.2, 6259.68, 6259.68)
import os
KN = json.loads(os.environ.get('FP_KNOBS', '{}'))      # probe knobs: G BB strip_scale band layout halo pch
BAND = float(KN.get('band', 100.0))     # routing-only band inside the pad ring
BB, G = float(KN.get('BB', 20.0)), float(KN.get('G', 60.0))   # back-to-back gap, in-row gap (vertical escape)
SS = float(KN.get('strip_scale', 1.0))
STRIP = {k: v * SS for k, v in {'PCORE0': 200, 'PCORE1': 200, 'PCORE2': 200, 'PCORE3': 200, 'datapath': 200, 'axi': 100,
         'cpu': 150, 'streams': 120, 'zmem': 150, 'zcore': 0, 'camera': 0}.items()}   # logic strip between pin edges
HALO = float(KN.get('halo', 10.0))      # engine cut_rows halo (area lost around every macro)
LAYOUT = KN.get('layout', 'bands')
PAIRS = bool(KN.get('pairs', True))      # False: every row faces a strip on both sides (no back-to-back pairs)
COLS = int(KN.get('cols', 1))            # sub-columns per region, separated by CW-wide vertical highways
CW = float(KN.get('CW', 150.0))
COLS_BLK = KN.get('cols_blk', {})        # per-block sub-column override, e.g. {'axi': 3}
STRIP_BLK = KN.get('strip_blk', {})      # per-block strip override in um, e.g. {'axi': 100}

src, cg, outp = sys.argv[1:4]

# ---------- inventory ----------
macros = []   # (inst, master, w, h)
for ln in open(src):
    f = ln.split()
    if f[0] == 'MACRO':
        macros.append((f[6], f[5], (int(f[3]) - int(f[1])) / U, (int(f[4]) - int(f[2])) / U, int(f[1]) / U, int(f[2]) / U))


def block_of(n):
    if re.search(r'gen1_pcore_i', n):
        return 'PCORE' + re.search(r'gen_reg\\?\[(\d)\\?\]', n).group(1)
    if n.startswith('soc_i/ztachip_inst/dp_'):
        return 'datapath'
    if n.startswith('soc_i/ztachip_inst/core_i/gen_stream'):
        return 'streams'
    if n.startswith('soc_i/ztachip_inst/core_i'):
        return 'zcore'
    if n.startswith('soc_i/ztachip_inst/'):
        return 'zmem'
    if n.startswith('soc_i/axi_merge') or n.startswith('soc_i/axi_split'):
        return 'axi'
    if n.startswith('soc_i/gen_cpu') or n.startswith('soc_i/tcm_i') or n.startswith('soc_i/uart'):
        return 'cpu'
    if n.startswith('hb_i'):
        return 'hyperbus'
    if 'vstream' in n or 'cam' in n:
        return 'camera'
    return 'misc'


cells = {}
for ln in open(cg):
    f = ln.split()
    b = block_of(f[0])
    c, a = cells.get(b, (0, 0.0))
    cells[b] = (c + int(f[1]), a + float(f[2]) / 1e6)

groups = {}
for m in macros:
    groups.setdefault(block_of(m[0]), []).append(m)

# ---------- regions (um): name -> (x0, y0, x1, y1, anchor) ----------
X0, Y0, X1, Y1 = CORE[0] + BAND, CORE[1] + BAND, CORE[2] - BAND, CORE[3] - BAND   # 440.3 .. 6159.7
XM = (X0 + X1) / 2                      # 3300
VC = float(KN.get('VC', 60.0))          # channel between blocks
if LAYOUT == 'bands':
    PCH = float(KN.get('pch', 950.0))   # PCORE band height
    YM0, YM1 = Y0 + PCH + VC, Y1 - PCH - VC          # middle band
    DPH = float(KN.get('dph', 2400.0))
    REG = {
        'PCORE0': (X0, Y0, XM - VC / 2, Y0 + PCH, 'bl'),
        'PCORE1': (XM + VC / 2, Y0, X1, Y0 + PCH, 'br'),
        'PCORE2': (X0, Y1 - PCH, XM - VC / 2, Y1, 'tl'),
        'PCORE3': (XM + VC / 2, Y1 - PCH, X1, Y1, 'tr'),
        'datapath': (X0, YM0, XM - VC / 2, YM0 + DPH, 'bl'),
        'streams': (X0, YM0 + DPH + VC, XM - VC / 2, YM0 + DPH + VC + 880, 'bl'),
        'zcore': (X0, YM1 - 340, XM - VC / 2, YM1, 'tl'),
        'zmem': (XM + VC / 2, YM0, X1, YM0 + 620, 'bl'),
        'camera': (XM + VC / 2, YM0 + 640, X1, YM0 + 780, 'bl'),
        'axi': (XM + VC / 2, YM0 + float(KN.get('axi_y0', 800.0)), X1, YM0 + 2500, 'br'),
        'cpu': (XM + VC / 2, YM1 - float(KN.get('cpuh', 1100.0)), X1, YM1, 'tr'),
    }
    chan = [(XM - VC / 2, Y0, XM + VC / 2, Y1), (X0, Y0 + PCH, X1, Y0 + PCH + VC), (X0, Y1 - PCH - VC, X1, Y1 - PCH)]
else:   # 'corners': PCORE squares in the four corners, side blocks between them, datapath/zmem/axi in a centre column
    PW = float(KN.get('pw', 1600.0)); PH = float(KN.get('ph', 1540.0))
    CX0, CX1 = X0 + PW + VC, X1 - PW - VC
    REG = {
        'PCORE0': (X0, Y0, X0 + PW, Y0 + PH, 'bl'),
        'PCORE1': (X1 - PW, Y0, X1, Y0 + PH, 'br'),
        'PCORE2': (X0, Y1 - PH, X0 + PW, Y1, 'tl'),
        'PCORE3': (X1 - PW, Y1 - PH, X1, Y1, 'tr'),
        'streams': (X0, Y0 + PH + VC, X0 + PW, Y0 + PH + VC + 1600, 'bl'),
        'zcore': (X0, Y1 - PH - VC - 820, X0 + PW, Y1 - PH - VC, 'tl'),
        'cpu': (X1 - PW, Y1 - PH - VC - 1800, X1, Y1 - PH - VC, 'tr'),
        'camera': (X1 - PW, Y0 + PH + VC, X1, Y0 + PH + VC + 300, 'bl'),
        'datapath': (CX0, Y0, CX1, Y0 + 2700, 'bl'),
        'zmem': (CX0, Y0 + 2760, CX1, Y0 + 3400, 'bl'),
        'axi': (CX0, Y1 - 2000, CX1, Y1, 'tl'),
    }
    chan = [(X0 + PW, Y0, CX0, Y1), (CX1, Y0, X1 - PW, Y1)]
COL = {'PCORE0': '#e07000', 'PCORE1': '#d6a300', 'PCORE2': '#2e9e63', 'PCORE3': '#3b7dd8', 'datapath': '#8a5fc9',
       'axi': '#c0392b', 'cpu': '#16a085', 'streams': '#7f8c8d', 'zcore': '#2c3e50', 'zmem': '#d35400',
       'camera': '#e84393', 'hyperbus': '#a0522d', 'misc': '#999999'}

# ---------- packer ----------
blockages = []   # (x0, y0, x1, y1) um, hard placement blockages: in-row gaps, highways
placed = []   # (inst, master, x, y, w, h, orient, block)
summary = {}




def pack_rows(items, W):
    """First-fit-decreasing by width into rows of width <= W (mixed heights allowed)."""
    rows = []
    for m in sorted(items, key=lambda m: (-m[2], -m[3], m[0])):
        for r in rows:
            if r['w'] + G + m[2] <= W + 1e-6:
                r['items'].append(m); r['w'] += G + m[2]; r['h'] = max(r['h'], m[3]); break
        else:
            rows.append({'h': m[3], 'w': m[2], 'items': [m]})
    rows.sort(key=lambda r: -r['h'])
    return rows


def stack(block, rows, x0, x1, y0, y1, anchor, boxes):
    """Stack rows from the anchor edge.  PAIRS: lower row MX (pins up) + STRIP + upper row R0 (pins down), BB between
    pairs.  Single rows: every row gets a STRIP on its pin side and the next row's back after BB... simplified to
    row / STRIP / row / STRIP with pins alternating so each strip is faced by the pins of exactly one row."""
    LS = float(STRIP_BLK.get(block, STRIP[block]))
    up = anchor in ('bl', 'br')
    y = y0 if up else y1
    for i, r in enumerate(rows):
        first_of_pair = (i % 2 == 0)
        if i > 0:
            if PAIRS:
                step = LS if not first_of_pair else BB
            else:
                step = LS
            y = y + step if up else y - step
        ry = y if up else y - r['h']
        y = y + r['h'] if up else y - r['h']
        if PAIRS:
            lower = first_of_pair if up else not first_of_pair
        else:
            lower = True          # single rows: pins always face the strip above (MX); blocks anchored top get R0
            if not up:
                lower = False
        orient = 'MX' if lower else 'R0'
        x = x0 if anchor in ('bl', 'tl') else x1 - r['w']
        for k, m in enumerate(sorted(r['items'], key=lambda m: -m[3])):
            boxes.append((m[0], m[1], x, ry, m[2], m[3], orient, block))
            if k < len(r['items']) - 1:
                blockages.append((x + m[2], ry, x + m[2] + G, ry + r['h']))
            x += m[2] + G


def pack(block, items, region):
    x0, y0, x1, y1, anchor = region
    boxes = []
    ncols = int(COLS_BLK.get(block, COLS))
    if ncols > 1:
        # split the region into ncols sub-columns with CW highways; distribute macros round-robin by area
        cw = ((x1 - x0) - (ncols - 1) * CW) / ncols
        cols = [[] for _ in range(ncols)]
        area = [0.0] * ncols
        for m in sorted(items, key=lambda m: -(m[2] * m[3])):
            j = area.index(min(area)); cols[j].append(m); area[j] += m[2] * m[3]
        nrows = 0
        for j in range(ncols):
            cx0 = x0 + j * (cw + CW)
            rows = pack_rows(cols[j], cw)
            nrows = max(nrows, len(rows))
            stack(block, rows, cx0, cx0 + cw, y0, y1, anchor, boxes)
            if j < ncols - 1:
                blockages.append((cx0 + cw, y0, cx0 + cw + CW, y1))
    else:
        rows = pack_rows(items, x1 - x0)
        nrows = len(rows)
        stack(block, rows, x0, x1, y0, y1, anchor, boxes)
    placed.extend(boxes)
    bx0 = min(b[2] for b in boxes); bx1 = max(b[2] + b[4] for b in boxes)
    by0 = min(b[3] for b in boxes); by1 = max(b[3] + b[5] for b in boxes)
    marea = sum(b[4] * b[5] for b in boxes) / 1e6
    halo_area = sum((b[4] + 2 * HALO) * (b[5] + 2 * HALO) for b in boxes) / 1e6
    rarea = (x1 - x0) * (y1 - y0) / 1e6
    c, carea = cells.get(block, (0, 0.0))
    summary[block] = dict(n=len(boxes), rows=nrows, bbox=(bx0, by0, bx1, by1), macro_mm2=marea, region_mm2=rarea,
                          cells=c, cell_mm2=carea, free_mm2=rarea - halo_area,
                          density=carea / max(rarea - halo_area, 1e-9), fits=(by1 <= y1 + 1e-6 and by0 >= y0 - 1e-6))


for b, items in groups.items():
    if b in REG:
        pack(b, items, REG[b])
    else:
        print('UNASSIGNED block', b, len(items))

# ---------- outputs ----------
def origin(x, y, w, h, o):
    return {'R0': (x, y), 'MX': (x, y + h), 'MY': (x + w, y), 'R180': (x + w, y + h)}[o]


def esc(p):
    return p.replace('\\', '').replace('[', '\\[').replace(']', '\\]')


pl = []
for inst, master, x, y, w, h, o, b in placed:
    ox, oy = origin(x, y, w, h, o)
    pl.append(f"{esc(inst)}:{ox:.3f}:{oy:.3f}:{o}")
json.dump({'macro_placements': pl}, open(outp + '_placements.json', 'w'), indent=0)
ring = [(CORE[0], CORE[1], CORE[2], Y0), (CORE[0], Y1, CORE[2], CORE[3]), (CORE[0], Y0, X0, Y1), (X1, Y0, CORE[2], Y1)]
with open(outp + '_blockages.txt', 'w') as fh:
    fh.write(';'.join(f'{a:.1f} {b:.1f} {c:.1f} {d:.1f}' for a, b, c, d in ring + chan + blockages))
print('blockages', len(ring + chan + blockages))

# overlap check
for i in range(len(placed)):
    a = placed[i]
    for j in range(i + 1, len(placed)):
        b = placed[j]
        if a[2] < b[2] + b[4] and b[2] < a[2] + a[4] and a[3] < b[3] + b[5] and b[3] < a[3] + a[5]:
            print('OVERLAP', a[0][-40:], b[0][-40:])
    if a[2] < X0 - 1e-6 or a[3] < Y0 - 1e-6 or a[2] + a[4] > X1 + 1e-6 or a[3] + a[5] > Y1 + 1e-6:
        print('OUTSIDE', a[7], a[0][-50:], a[2], a[3])

tot_m = sum(s['macro_mm2'] for s in summary.values())
with open(outp + '_summary.txt', 'w') as fh:
    for b, s in summary.items():
        line = (f"{b:9s} n={s['n']:3d} rows={s['rows']:2d} bbox=({s['bbox'][0]:.0f},{s['bbox'][1]:.0f})-({s['bbox'][2]:.0f},"
                f"{s['bbox'][3]:.0f}) macro={s['macro_mm2']:.2f} region={s['region_mm2']:.2f} cells={s['cells']:6d} "
                f"cell={s['cell_mm2']:.2f} free={s['free_mm2']:.2f} est.density={100 * s['density']:.0f}% "
                f"{'OK' if s['fits'] else 'DOES NOT FIT'}")
        print(line); fh.write(line + '\n')
    fh.write(f"macros placed {len(placed)} of {len(macros)}; macro area {tot_m:.2f} mm2\n")
print(f"placed {len(placed)} of {len(macros)} macros")

# ---------- picture: before / after ----------
pads = []
for ln in open(src):
    f = ln.split()
    if f[0] == 'PAD':
        pads.append(tuple(int(v) / U for v in f[1:5]))

fig, axes = plt.subplots(1, 2, figsize=(22, 11))


def frame(ax, title):
    for bb in pads:
        ax.add_patch(Rectangle((bb[0], bb[1]), bb[2] - bb[0], bb[3] - bb[1], fc='#e8ecf0', ec='none'))
    ax.add_patch(Rectangle((CORE[0], CORE[1]), CORE[2] - CORE[0], CORE[3] - CORE[1], fill=False, ec='#333', lw=0.8))
    ax.set_xlim(0, 6600); ax.set_ylim(0, 6600); ax.set_aspect('equal'); ax.set_xlabel('µm'); ax.set_ylabel('µm')
    ax.set_title(title)


frame(axes[0], 'BEFORE: run F7 (automatic macro placer, halo 25): 298 SRAMs')
for inst, master, w, h, x, y in macros:
    b = block_of(inst)
    axes[0].add_patch(Rectangle((x, y), w, h, fc=COL[b], ec='#222', lw=0.4, alpha=0.85))
axes[0].add_patch(Rectangle((CORE[0], 365), 60, 5875, fill=False, ec='red', lw=2, ls='--'))
axes[0].text(CORE[0] + 70, 3300, 'west strip:\nall traffic to\n28 SRAMs\nthrough 58 µm', color='red', fontsize=9, va='center')

frame(axes[1], f'AFTER (proposed, layout {LAYOUT}, G={G:.0f} BB={BB:.0f} strips x{SS}): blocks by owner, pins facing logic strips, {BAND:.0f} µm band')
axes[1].add_patch(Rectangle((X0, Y0), X1 - X0, Y1 - Y0, fill=False, ec='#1f5fbf', lw=1.2, ls='--'))
for a, b_, c, d in ring + chan:
    axes[1].add_patch(Rectangle((a, b_), c - a, d - b_, fc='#dfe7f3', ec='none'))
for b, (x0, y0, x1, y1, a) in REG.items():
    axes[1].add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=COL[b], lw=0.8, ls=':'))
for inst, master, x, y, w, h, o, b in placed:
    axes[1].add_patch(Rectangle((x, y), w, h, fc=COL[b], ec='#222', lw=0.4, alpha=0.85))
    # pin edge marker
    py = y + h - 6 if o == 'MX' else y
    axes[1].add_patch(Rectangle((x, py), w, 6, fc='black', ec='none'))
for b, s in summary.items():
    x0, y0, x1, y1 = s['bbox']
    axes[1].text((x0 + x1) / 2, (y0 + y1) / 2, f"{b}\n{s['n']} SRAMs", ha='center', va='center', fontsize=9,
                 color='white', fontweight='bold', bbox=dict(fc='black', alpha=0.4, lw=0))
hs = [Rectangle((0, 0), 1, 1, fc=COL[b]) for b in COL]
axes[1].legend(hs, list(COL), loc='upper left', bbox_to_anchor=(1.01, 1.0), fontsize=9, title='macro owner')
fig.suptitle('SoC2611 (DSOC2610) floorplan: current vs proposed  (black edge = SRAM signal-pin side)', fontsize=15)
fig.subplots_adjust(left=0.04, right=0.9, top=0.9, bottom=0.07, wspace=0.15)
fig.savefig(outp + '_before_after.png', dpi=100)
print('wrote', outp + '_before_after.png')
