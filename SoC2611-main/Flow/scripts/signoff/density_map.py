#!/usr/bin/env python3
"""Standard-cell density map from dump_density.tcl output (100 um bins, cell area / available row area).
Left: all placed cells + all macros.  Right: cells of the four PCOREs only (their register-file SRAMs sit on the west edge, far from the logic).
usage: density_map.py <place.txt> <out.png> [title] [bin_um=100]
Measured regions (dashed): whole core, PCORE logic box (5-95th percentile of all PCORE cells), west strip."""
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

src, out = sys.argv[1], sys.argv[2]
title = sys.argv[3] if len(sys.argv) > 3 else 'SoC2611: measured standard-cell density'
BIN = float(sys.argv[4]) if len(sys.argv) > 4 else 100.0
U = 1000.0  # dbu per um

rows, macros, pads, cells = [], [], [], []
die = core = None
with open(src) as fh:
    for ln in fh:
        f = ln.split()
        k = f[0]
        if k == 'C':
            cells.append((int(f[1]), int(f[2]), int(f[3]), int(f[4]), f[5]))
        elif k == 'ROW':
            rows.append(tuple(int(v) / U for v in f[1:5]))
        elif k == 'MACRO':
            macros.append((tuple(int(v) / U for v in f[1:5]), f[5], f[6]))
        elif k == 'PAD':
            pads.append(tuple(int(v) / U for v in f[1:5]))
        elif k == 'DIE':
            die = tuple(int(v) / U for v in f[1:5])
        elif k == 'CORE':
            core = tuple(int(v) / U for v in f[1:5])

cx = np.array([c[0] for c in cells]) / U
cy = np.array([c[1] for c in cells]) / U
cw = (np.array([c[2] for c in cells]) - np.array([c[0] for c in cells])) / U
ch = (np.array([c[3] for c in cells]) - np.array([c[1] for c in cells])) / U
own = np.array([c[4] for c in cells])
carea = cw * ch
ccx, ccy = cx + cw / 2, cy + ch / 2

W, H = die[2], die[3]
nx, ny = int(np.ceil(W / BIN)), int(np.ceil(H / BIN))
xe, ye = np.arange(nx + 1) * BIN, np.arange(ny + 1) * BIN


def clip_area(bb):
    """Exact area of box bb (x0,y0,x1,y1 um) in every bin -> (ny, nx) array."""
    x0, y0, x1, y1 = bb
    ox = np.clip(np.minimum(xe[1:], x1) - np.maximum(xe[:-1], x0), 0, None)
    oy = np.clip(np.minimum(ye[1:], y1) - np.maximum(ye[:-1], y0), 0, None)
    return np.outer(oy, ox)


row_area = np.zeros((ny, nx))
for r in rows:
    row_area += clip_area(r)
macro_area = np.zeros((ny, nx))
for bb, _, _ in macros:
    macro_area += clip_area(bb)
avail = np.clip(row_area - macro_area, 0, None)


def cell_density(mask):
    a, _, _ = np.histogram2d(ccy[mask], ccx[mask], bins=[ye, xe], weights=carea[mask])
    with np.errstate(divide='ignore', invalid='ignore'):
        d = np.where(avail > 0.02 * BIN * BIN, a / avail, np.nan)
    return a, d


def region_stats(a, x0, y0, x1, y1):
    """Cell area / available area inside a um box (bin resolution)."""
    ix = (xe[:-1] >= x0 - 1e-6) & (xe[1:] <= x1 + 1e-6)
    iy = (ye[:-1] >= y0 - 1e-6) & (ye[1:] <= y1 + 1e-6)
    sel = np.ix_(iy, ix)
    return a[sel].sum(), avail[sel].sum()


a_all, d_all = cell_density(np.ones(len(cells), bool))
m0 = own != '-'
a_p0, d_p0 = cell_density(m0)

# measured regions
p0x0, p0x1 = np.percentile(ccx[m0], [5, 95]) if m0.any() else (0, 0)
p0y0, p0y1 = np.percentile(ccy[m0], [5, 95]) if m0.any() else (0, 0)
p0box = (np.floor(p0x0 / BIN) * BIN, np.floor(p0y0 / BIN) * BIN, np.ceil(p0x1 / BIN) * BIN, np.ceil(p0y1 / BIN) * BIN)
# west strip: core edge .. first macro column (any macro whose xMin < core.x + 150)
west = [bb for bb, _, _ in macros if bb[0] < core[0] + 150]
wx1 = min(bb[0] for bb in west) if west else core[0] + 100
westbox = (core[0], core[1], wx1, core[3])
p0_macros = [bb for bb, _, n in macros if re.search(r'gen_reg\\?\[\d\\?\]_gen1_pcore', n)]

ca_all, av_all = a_all.sum(), avail.sum()
ca_p0box, av_p0box = region_stats(a_all, *p0box)
cp0_in, _ = region_stats(a_p0, *p0box)
wa, wav = region_stats(a_all, *westbox)
# PCORE 0 share of its own cells inside its box, and distance from box to its SRAMs
p0_sram_x1 = max(bb[2] for bb in p0_macros) if p0_macros else wx1

fig, axes = plt.subplots(1, 2, figsize=(20, 9.6), gridspec_kw={'width_ratios': [1, 1]})
cmap = plt.get_cmap('YlOrRd').copy()
cmap.set_bad('#fffde7')


def draw(ax, d, sub, boxes, show_p0_macros):
    im = ax.imshow(d, origin='lower', extent=[0, nx * BIN, 0, ny * BIN], cmap=cmap, vmin=0, vmax=1.0,
                   interpolation='nearest')
    for bb in pads:
        ax.add_patch(Rectangle((bb[0], bb[1]), bb[2] - bb[0], bb[3] - bb[1], fc='#e8ecf0', ec='none'))
    for bb, m, n in macros:
        hot = show_p0_macros and re.search(r'gen_reg\\?\[\d\\?\]_gen1_pcore', n)
        ax.add_patch(Rectangle((bb[0], bb[1]), bb[2] - bb[0], bb[3] - bb[1],
                               fc='#f6b26b' if hot else '#d9dee4', ec='#e07000' if hot else '#5c6670',
                               lw=1.0 if hot else 0.5))
    for (x0, y0, x1, y1), col, lab in boxes:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=col, ls='--', lw=1.8))
        ax.text(x0 + 15, y1 - 20, lab, color=col, fontsize=10, va='top', fontweight='bold')
    ax.add_patch(Rectangle((core[0], core[1]), core[2] - core[0], core[3] - core[1], fill=False, ec='#333', lw=0.6))
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
    ax.set_xlabel('µm'); ax.set_ylabel('µm'); ax.set_title(sub)
    return im


im = draw(axes[0], d_all, f'All placed standard cells ({len(cells):,}) + all {len(macros)} macros',
          [(p0box, '#1f5fbf', 'PCORE 0-3 logic'), (westbox, '#1f5fbf', '')], False)
draw(axes[1], d_p0, f'PCORE 0-3 cells only ({m0.sum():,}); the PCORE SRAMs ({len(p0_macros)}) highlighted',
     [(p0box, '#1f5fbf', 'PCORE 0-3 logic (5-95 %)'), (westbox, '#1f5fbf', '')], True)
cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02, extend='max')
cb.set_label('Cell area / available row area')

foot = (f"PCORE logic box {p0box[0]:.0f}-{p0box[2]:.0f} × {p0box[1]:.0f}-{p0box[3]:.0f} µm: "
        f"{ca_p0box / 1e6:.3f} mm² cells / {av_p0box / 1e6:.3f} mm² available = {100 * ca_p0box / max(av_p0box, 1):.1f}% "
        f"(PCORE cells are {100 * cp0_in / max(ca_p0box, 1):.0f}% of the cell area in it)\n"
        f"West strip x {westbox[0]:.0f}-{westbox[2]:.0f} µm (core edge to SRAM column): "
        f"{100 * wa / max(wav, 1):.1f}%  |  Whole core: {ca_all / 1e6:.3f} mm² / {av_all / 1e6:.3f} mm² = "
        f"{100 * ca_all / av_all:.1f}%  |  West column (x = {westbox[2]:.0f} µm): {len(west)} SRAMs, "
        f"{sum(1 for bb in west if bb in p0_macros)} of them PCORE register files, logic box starts at x = {p0box[0]:.0f} µm"
        f"  |  {BIN:.0f} µm bins; blue dashed boxes define measured regions")
fig.suptitle(title, fontsize=15)
fig.text(0.5, 0.02, foot, ha='center', fontsize=10)
fig.subplots_adjust(left=0.05, right=0.9, top=0.88, bottom=0.12, wspace=0.12)
fig.savefig(out, dpi=110)
print(f"DENSITY_MAP wrote {out}")
print(foot)
