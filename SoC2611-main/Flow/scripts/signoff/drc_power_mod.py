#!/usr/bin/env python3
"""Where do the power shorts sit relative to the TopMetal1 strap grid?  For every Short marker whose srcs include
VDD/VSS, take the marker centre and print the distribution of (y - Y0) mod PITCH per layer (um bins), plus the
x distribution mod XPITCH for the Metal4 pad-to-core stubs.  usage: drc_power_mod.py <drc.rpt> [Y0=341.3] [PITCH=16]
[XPITCH=50] [X0=2.8]"""
import collections
import re
import sys

fn = sys.argv[1]
Y0 = float(sys.argv[2]) if len(sys.argv) > 2 else 341.3
P = float(sys.argv[3]) if len(sys.argv) > 3 else 16.0
XP = float(sys.argv[4]) if len(sys.argv) > 4 else 50.0
X0 = float(sys.argv[5]) if len(sys.argv) > 5 else 2.8
ymod = collections.defaultdict(collections.Counter)
xmod = collections.defaultdict(collections.Counter)
tot = collections.Counter()
typ = None; pw = False
for l in open(fn):
    if l.startswith('violation type:'):
        typ = l.split(':', 1)[1].strip(); pw = False
    elif l.strip().startswith('srcs:'):
        pw = ('net:VDD' in l) or ('net:VSS' in l)
    m = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', l)
    if m and typ == 'Short' and pw:
        x0, y0, x1, y1 = map(float, m.groups()[:4]); lay = m.group(5)
        cy = (y0 + y1) / 2; cx = (x0 + x1) / 2
        ymod[lay][int(((cy - Y0) % P) // 1.0)] += 1
        xmod[lay][int(((cx - X0) % XP) // 2.0) * 2] += 1
        tot[lay] += 1
for lay in sorted(tot):
    print(f'--- {lay}: {tot[lay]} power shorts; (y - {Y0}) mod {P} um, 1 um bins:')
    print('   ' + ' '.join(f'{b}:{ymod[lay][b]}' for b in range(int(P))))
    top = xmod[lay].most_common(6)
    print(f'   x mod {XP} (2 um bins), top: ' + ' '.join(f'{b}:{n}' for b, n in top))
