#!/usr/bin/env python3
"""H4 = H3 with the AXI block (soc_i/axi_merge*, soc_i/axi_split*) replaced by the planner's 3-sub-column packing
(85 um pin strips, y from 2140) and the 4 camera FIFO macros moved to one MX row above PCORE1 (y CAM_Y, x from 3480).
usage: fp_h4_merge.py <macros.txt> <H3.pl> <planner_axi.pl> <out.pl> [CAM_Y=1240]"""
import sys

mac, src, axi_pl, out = sys.argv[1:5]
CAM_Y = float(sys.argv[5]) if len(sys.argv) > 5 else 1240.0
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}


def is_axi(n):
    return n.startswith('soc_i/axi_merge') or n.startswith('soc_i/axi_split')


def read(fn):
    return [[p[0], float(p[1]), float(p[2]), p[3]] for p in (l.split() for l in open(fn)) if len(p) == 4]


h3 = read(src)
axi_new = {m[0]: m for m in read(axi_pl) if is_axi(m[0])}
rows = []
n_axi = 0
for m in h3:
    if is_axi(m[0]):
        rows.append(axi_new[m[0]]); n_axi += 1
    else:
        rows.append(m)
cam = [m for m in rows if 'vstream' in m[0]]
x = 3480.0
for m in sorted(cam, key=lambda m: -S[m[0]][0]):
    m[1], m[2], m[3] = x, CAM_Y, 'MX'
    x += S[m[0]][0] + 60.0
axi_top = max(m[2] + S[m[0]][1] for m in rows if is_axi(m[0]))
axi_bot = min(m[2] for m in rows if is_axi(m[0]))
cpu_bottom = min(m[2] for m in rows if ('gen_cpu' in m[0] or 'tcm_i' in m[0]) and m[1] > 3300)
print(f'AXI {n_axi} macros replaced: y {axi_bot:.0f}..{axi_top:.0f}; CPU bottom {cpu_bottom:.0f}; camera row y {CAM_Y} x 3480..{x - 60:.0f}')
bx = [(m[0], m[1], m[2], m[1] + S[m[0]][0], m[2] + S[m[0]][1]) for m in rows]
bad = 0
for i in range(len(bx)):
    for j in range(i + 1, len(bx)):
        a, b = bx[i], bx[j]
        if a[1] < b[3] + 20 and b[1] < a[3] + 20 and a[2] < b[4] + 20 and b[2] < a[4] + 20:
            print('OVERLAP/<20um', a[0][-45:], b[0][-45:]); bad += 1
for b in bx:
    if b[1] < 440 or b[2] < 440 or b[3] > 6160 or b[4] > 6160:
        print('OUTSIDE', b[0][-45:]); bad += 1
with open(out, 'w') as fh:
    for m in rows:
        fh.write('%s %.2f %.2f %s\n' % (m[0], m[1], m[2], m[3]))
print(f'wrote {out}: {len(rows)} macros, problems {bad}')
