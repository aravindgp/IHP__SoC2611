#!/usr/bin/env python3
"""Nets whose global-route guides (OpenROAD guide file: name, '(', 'x0 y0 x1 y1 layer' lines, ')') on the macro-blocked
layers cross a footprint box, minus the nets of a strip list. These keep stale guides through a moved macro: the
detailed router re-routes them into the macro when it rips them up (d1/d2: dp_sink3 net3511, dp_sink2 net203).
usage: guides_crossing_footprint.py <guides.txt> <strip.txt> x0 y0 x1 y1 <out_nets.txt> [layers=Metal1,Metal2,Metal3,Metal4]"""
import sys

guides, strip = sys.argv[1], sys.argv[2]
B = [float(v) for v in sys.argv[3:7]]
out = sys.argv[7]
layers = set((sys.argv[8] if len(sys.argv) > 8 else 'Metal1,Metal2,Metal3,Metal4').split(','))
stripped = set(l.split()[0] for l in open(strip) if l.strip())
cross = {}
net = None
for l in open(guides):
    p = l.split()
    if not p:
        continue
    if len(p) == 1 and p[0] not in '()':
        net = p[0]
    elif len(p) == 5 and net is not None and p[4] in layers:
        x0, y0, x1, y1 = (float(v) for v in p[:4])
        if x1 > B[0] and x0 < B[2] and y1 > B[1] and y0 < B[3]:
            cross[net] = cross.get(net, 0) + 1
new = sorted(n for n in cross if n not in stripped)
open(out, 'w').write(''.join(n + '\n' for n in new))
print(f'# nets with guides on {sorted(layers)} inside {B}: {len(cross)}; of them stripped {len(cross) - len(new)}, NOT stripped {len(new)} -> {out}')
for n in new[:12]:
    print(' ', cross[n], n)
