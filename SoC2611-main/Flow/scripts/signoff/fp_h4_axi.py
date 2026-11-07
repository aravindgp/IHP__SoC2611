#!/usr/bin/env python3
"""H4 = H3 with EVERY pin-facing strip of the AXI block widened to >= STRIP um (H had 60 um; the dp/AXI seam column
stays the slowest part of drtH3), paid for by moving the 4 camera FIFO macros into the free row above PCORE1
(y ~1240) and using the gap below the CPU block.  AXI rows are walked bottom-up; a strip is the space between an MX
row (pins up) and the R0 row (pins down) above it; the cumulative shift moves everything above.
usage: fp_h4_axi.py <macros.txt> <H3.pl> <out.pl> [STRIP=100] [CAM_Y=1240]"""
import sys
from collections import defaultdict

mac, src, out = sys.argv[1:4]
STRIP = float(sys.argv[4]) if len(sys.argv) > 4 else 100.0
CAM_Y = float(sys.argv[5]) if len(sys.argv) > 5 else 1240.0
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
rows = []
for l in open(src):
    p = l.split()
    if len(p) == 4:
        rows.append([p[0], float(p[1]), float(p[2]), p[3]])
# 1. camera macros -> one MX row above PCORE1 (x from 3480), widest first
cam = [m for m in rows if 'vstream' in m[0]]
x = 3480.0
for m in sorted(cam, key=lambda m: -S[m[0]][0]):
    m[1], m[2], m[3] = x, CAM_Y, 'MX'
    x += S[m[0]][0] + 60.0
print(f'camera row: {len(cam)} macros at y {CAM_Y}, x 3480..{x - 60:.0f}')
# 2. AXI rows (x > 3300, y 2000..4000) grouped by lly
axi = [m for m in rows if 'axi_' in m[0] and m[1] > 3300 and 2000 < m[2] < 4000]
byrow = defaultdict(list)
for m in axi:
    byrow[round(m[2], 1)].append(m)
ys = sorted(byrow)
shift = 0.0
prev_top = None; prev_orient = None
widened = 0
for y in ys:
    items = byrow[y]
    orient = items[0][3]
    top = max(y + S[m[0]][1] for m in items)
    if prev_top is not None and prev_orient == 'MX' and orient == 'R0':
        strip = (y + shift) - prev_top
        if strip < STRIP - 1e-6:
            shift += STRIP - strip; widened += 1
    for m in items:
        m[2] = y + shift
    prev_top = top + shift; prev_orient = orient
axi_top = max(m[2] + S[m[0]][1] for m in axi)
cpu_bottom = min(m[2] for m in rows if ('gen_cpu' in m[0] or 'tcm_i' in m[0]) and m[1] > 3300)
print(f'AXI: {len(ys)} rows, {widened} strips widened to {STRIP}, total shift {shift:.0f}; AXI top {axi_top:.1f}, CPU bottom {cpu_bottom:.1f}')
# 3. checks
bx = [(m[0], m[1], m[2], m[1] + S[m[0]][0], m[2] + S[m[0]][1]) for m in rows]
bad = 0
for i in range(len(bx)):
    for j in range(i + 1, len(bx)):
        a, b = bx[i], bx[j]
        if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]:
            print('OVERLAP', a[0][-45:], b[0][-45:]); bad += 1
for b in bx:
    if b[1] < 440 or b[2] < 440 or b[3] > 6160 or b[4] > 6160:
        print('OUTSIDE', b[0][-45:]); bad += 1
if axi_top > cpu_bottom - 60:
    print(f'AXI top {axi_top:.0f} too close to CPU bottom {cpu_bottom:.0f}'); bad += 1
with open(out, 'w') as fh:
    for m in rows:
        fh.write('%s %.2f %.2f %s\n' % (m[0], m[1], m[2], m[3]))
print(f'wrote {out}, problems {bad}')
