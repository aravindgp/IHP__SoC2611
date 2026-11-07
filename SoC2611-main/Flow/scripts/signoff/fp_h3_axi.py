#!/usr/bin/env python3
"""H3 = H with the AXI block's upper rows shifted up by DY um so the 2P 64x32 row's pins (R0, pins down at y 2721)
face the 256x32 row's pins (MX, pins up at y 2661) across 120 um instead of 60 (drtH2 pass-3 wall: 7,551 markers in
the 150 um window at x 3200-3350 y 2600-2750).  Only AXI macros with lly >= YCUT move; the block top must stay
below the CPU block (4072).  usage: fp_h3_axi.py <macros.txt> <H.pl> <out.pl> [YCUT=2700] [DY=60]"""
import sys

mac, src, out = sys.argv[1:4]
YCUT = float(sys.argv[4]) if len(sys.argv) > 4 else 2700.0
DY = float(sys.argv[5]) if len(sys.argv) > 5 else 60.0
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
rows = []
moved = 0
top = 0.0
for l in open(src):
    p = l.split()
    if len(p) != 4:
        continue
    n, x, y, o = p[0], float(p[1]), float(p[2]), p[3]
    if ('axi_' in n) and y >= YCUT and y < 4000:
        y += DY; moved += 1
        top = max(top, y + S[n][1])
    rows.append((n, x, y, o))
# overlap check
bx = [(n, x, y, x + S[n][0], y + S[n][1]) for n, x, y, o in rows]
bad = 0
for i in range(len(bx)):
    for j in range(i + 1, len(bx)):
        a, b = bx[i], bx[j]
        if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]:
            print('OVERLAP', a[0][-40:], b[0][-40:]); bad += 1
cpu_bottom = min(y for n, x, y, o in rows if ('gen_cpu' in n or 'tcm_i' in n) and x > 3300)
with open(out, 'w') as fh:
    for n, x, y, o in rows:
        fh.write('%s %.2f %.2f %s\n' % (n, x, y, o))
print(f'moved {moved} AXI macros up by {DY}; AXI top now {top:.1f}, CPU block bottom {cpu_bottom:.1f}, overlaps {bad}; wrote {out}')
