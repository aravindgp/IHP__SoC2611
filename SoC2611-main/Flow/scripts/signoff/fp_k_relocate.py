#!/usr/bin/env python3
"""Probe K: the proven automatic placement (h25_lvl1, 49.5k GRT overflow) with ONLY the west-column macros
(llx < XW) relocated into its open areas; everything else untouched.
  - PCORE register files (416.64 x 118.78): one row above the PCORE SRAM rows, MX (pins up into the PCORE logic)
  - stream lookups (236.8 x 110.38) + AXI 64x16 tiles (236.8 x 64.36): rows of 4 in the open centre block
    (x 2890..4190, y 3440..5590), R0 with 120 um channels (pins down into each channel)
usage: fp_k_relocate.py <macros.txt> <in.pl> <out.pl> [XW=400]"""
import sys

mac, src, out = sys.argv[1:4]
XW = float(sys.argv[4]) if len(sys.argv) > 4 else 400.0
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
keep, move = [], []
for l in open(src):
    p = l.split()
    if len(p) != 4:
        continue
    n, x, y, o = p[0], float(p[1]), float(p[2]), p[3]
    (move if x < XW else keep).append([n, x, y, o])
print('kept', len(keep), 'relocating', len(move))
rf = sorted([m for m in move if 'pcore' in m[0]], key=lambda m: m[0])
st = sorted([m for m in move if 'stream' in m[0]], key=lambda m: m[0])
ax = sorted([m for m in move if m not in rf and m not in st], key=lambda m: m[0])
print('  register files', len(rf), 'stream lookups', len(st), 'other', len(ax))
G = 60.0
# 1. register-file row above the PCORE SRAM rows: find the top of the kept macros in x 440..3300, y < 2000
top = max(m[2] + S[m[0]][1] for m in keep if m[1] < 3300 and m[2] < 1800)
y_rf = top + 100.0
x = 600.0
for m in rf:
    w, h = S[m[0]]
    m[1], m[2], m[3] = x, y_rf, 'MX'
    x += w + G
print('  RF row at y %.1f..%.1f, x 600..%.1f (top of PCORE rows %.1f)' % (y_rf, y_rf + 118.78, x - G, top))
# 2. streams + axi tiles in the centre block, rows of 4, pins down into 120 um channels
items = st + ax
x0, y0, x1, y1 = 2890.0, 3440.0, 4190.0, 5590.0
CH = 120.0
y = y0 + CH
rowh = 0
col = 0
for m in items:
    w, h = S[m[0]]
    if col == 4 or x0 + col * (w + G) + w > x1:
        y += rowh + CH; col = 0; rowh = 0
    m[1], m[2], m[3] = x0 + col * (w + G), y, 'R0'
    rowh = max(rowh, h); col += 1
print('  centre block rows up to y %.1f (limit %.1f)' % (y + rowh, y1))
allm = keep + move
# validation: inside box, overlaps with 20 um clearance
bad = 0
bx = [(m[0], m[1], m[2], m[1] + S[m[0]][0], m[2] + S[m[0]][1]) for m in allm]
for b in bx:
    if b[1] < 340.32 or b[2] < 340.2 or b[3] > 6259.68 or b[4] > 6259.68:   # core box (edge macros of the proven placement stay)
        print('OUTSIDE', b[0][-40:], b[1:]); bad += 1
for i in range(len(bx)):
    for j in range(i + 1, len(bx)):
        a, b = bx[i], bx[j]
        if a[1] < b[3] + 20 and b[1] < a[3] + 20 and a[2] < b[4] + 20 and b[2] < a[4] + 20:
            print('OVERLAP/<20um', a[0][-40:], b[0][-40:]); bad += 1
with open(out, 'w') as fh:
    for m in allm:
        fh.write('%s %.2f %.2f %s\n' % (m[0], m[1], m[2], m[3]))
print('wrote', out, 'macros', len(allm), 'problems', bad)
