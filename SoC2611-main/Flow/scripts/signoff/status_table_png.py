#!/usr/bin/env python3
"""Render the final-GDS step list as a clean, phone-portrait PNG: step name + grey detail on the left, a coloured
status pill in a fixed right column.  usage: status_table_png.py <out.png> [title]"""
import sys
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# (step, detail, status)
rows = [
    ('Floorplan H13', 'pockets blocked; GRT overflow 9,522 to 3,061', 'Done'),
    ('Detailed route to the floor', 'H10 complete at 996; H13 snapshots kept', 'Done'),
    ('ECO rounds: shorts inside SRAMs', '687 > 439 > 208 > 165, round D running', 'Running'),
    ('Residual violations to zero', 'total 1,689 after round C', 'Running'),
    ('Antenna repair', 'diodes + re-route; 6,052 > 581 nets in rehearsal', 'Rehearsed'),
    ('Bondpad pins, DEF, Verilog', 'chip_finish, 3 min', 'Done'),
    ('DEF to GDS stream', '60 s, 750 MB; SRAM cells verified', 'Done'),
    ('Seal ring and label', 'make_sealring, label fixed', 'Done'),
    ('Fill and density', 'PDK + top-up fill: 0 density violations', 'Done'),
    ('One GDS file under 100 MB', 'full-fill gzip 155 MB; LFS / xz / two parts', 'Open'),
    ('IHP minimum DRC, waivers', 'needs the closed GDS; hours', 'Pending'),
    ('LVS vs released CDL', 'CDL built (328k inst.); about 7 h', 'Pending'),
    ('Timing report', 'hold/setup not run yet', 'Pending'),
    ('Testbenches, synthesis script', 'repo folders still empty', 'Pending'),
    ('Release v1.1.0 (preliminary)', 'pushed, info.json path fixed', 'Done'),
    ('Final release, hashes, issue #79', 'after closure, DRC and LVS', 'Pending'),
]
colors = {'Done': '#2e7d32', 'Running': '#1565c0', 'Rehearsed': '#6a1b9a', 'Open': '#ef6c00', 'Pending': '#757575'}
title = sys.argv[2] if len(sys.argv) > 2 else 'SoC2611 final GDS: steps'
W, H = 1080, 1920                      # phone portrait, pixels
dpi = 160
fig = plt.figure(figsize=(W / dpi, H / dpi), dpi=dpi)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(H, 0)
ax.axis('off')
ax.text(40, 70, title, fontsize=20, weight='bold', va='center', color='#111111')
ax.text(40, 118, '8 Nov 2026, 21:10 IST', fontsize=12, va='center', color='#666666')
top, bottom = 160, H - 40
n = len(rows)
rh = (bottom - top) / n
x_num, x_text, x_pill, pill_w = 40, 90, W - 40 - 250, 250
for i, (step, detail, st) in enumerate(rows):
    y = top + i * rh
    if i % 2 == 0:
        ax.add_patch(FancyBboxPatch((20, y + 4), W - 40, rh - 8, boxstyle='round,pad=0,rounding_size=10',
                                    fc='#f3f5f7', ec='none', zorder=0))
    ax.text(x_num, y + rh * 0.36, f'{i + 1}', fontsize=13, weight='bold', va='center', color='#9e9e9e')
    ax.text(x_text, y + rh * 0.34, step, fontsize=14, weight='bold', va='center', color='#111111')
    ax.text(x_text, y + rh * 0.70, textwrap.shorten(detail, 58, placeholder='...'), fontsize=10.5, va='center',
            color='#666666')
    c = colors[st]
    ax.add_patch(FancyBboxPatch((x_pill, y + rh * 0.28), pill_w, rh * 0.44, boxstyle='round,pad=0,rounding_size=18',
                                fc=c, ec='none', zorder=1))
    ax.text(x_pill + pill_w / 2, y + rh * 0.50, st.upper(), fontsize=12, weight='bold', va='center', ha='center',
            color='white', zorder=2)
fig.savefig(sys.argv[1], dpi=dpi, facecolor='white')
print('wrote', sys.argv[1])
