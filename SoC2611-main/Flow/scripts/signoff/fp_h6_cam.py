#!/usr/bin/env python3
"""H6 = H4 with the 4 camera FIFO macros (vstream) put back into the slot east of the dp highway: x from the H3
placement, y and orientation given (default y 1960, MX: pins on top face the AXI MX row bottom at 2140 across 61 um;
the macro bodies block cells and M1-M4 in the slot as the H3 camera row did).
usage: fp_h6_cam.py <macros.txt> <H4.pl> <H3.pl> <out.pl> [Y=1960] [ORI=MX]"""
import sys

mac, src, ref, out = sys.argv[1:5]
Y = float(sys.argv[5]) if len(sys.argv) > 5 else 1960.0
ORI = sys.argv[6] if len(sys.argv) > 6 else 'MX'
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}


def read(fn):
    return [[p[0], float(p[1]), float(p[2]), p[3]] for p in (l.split() for l in open(fn)) if len(p) == 4]


rows = read(src)
refx = {m[0]: m[1] for m in read(ref) if 'vstream' in m[0]}
n = 0
for m in rows:
    if 'vstream' in m[0]:
        m[1], m[2], m[3] = refx[m[0]], Y, ORI; n += 1
        print(f'cam {m[0][-40:]} -> x {m[1]:.1f}..{m[1] + S[m[0]][0]:.1f} y {Y:.1f}..{Y + S[m[0]][1]:.1f} {ORI}')
with open(out, 'w') as fh:
    for m in rows:
        fh.write('%s %.2f %.2f %s\n' % (m[0], m[1], m[2], m[3]))
print(f'wrote {out}: {len(rows)} macros, {n} camera macros moved')
