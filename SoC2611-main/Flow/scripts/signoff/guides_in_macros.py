#!/usr/bin/env python3
"""Count global-route guide boxes per layer whose centre lies inside a macro outline (from a .pl placement), and
list the macros / nets with the most such boxes.  usage: guides_in_macros.py <route.guide> <macros.txt> <place.pl>
[margin_um=0]  (guide file format: net name, '(' , 'x0 y0 x1 y1 layer' lines in DBU or um, ')')"""
import bisect
import collections
import sys

gf, mac, pl = sys.argv[1:4]
margin = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
boxes = []
for l in open(pl):
    p = l.split()
    if len(p) == 4:
        w, h = S[p[0]]
        boxes.append((float(p[1]) - margin, float(p[2]) - margin, float(p[1]) + w + margin, float(p[2]) + h + margin, p[0]))
boxes.sort()
xs = [b[0] for b in boxes]


def inside(cx, cy):
    i = bisect.bisect_right(xs, cx)
    for b in boxes[max(0, i - 40):i]:
        if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]:
            return b[4]
    return None


per_layer = collections.Counter(); per_layer_in = collections.Counter()
per_macro = collections.Counter(); per_net = collections.Counter()
pairs = collections.Counter()   # (net, macro) -> M4 boxes inside
dump = sys.argv[5] if len(sys.argv) > 5 else None
net = None; scale = None
with open(gf) as fh:
    for l in fh:
        p = l.split()
        if not p:
            continue
        if len(p) == 1 and p[0] not in ('(', ')'):
            net = p[0]; continue
        if len(p) == 5:
            x0, y0, x1, y1 = map(float, p[:4]); lay = p[4]
            if scale is None:
                scale = 1000.0 if max(x1, y1) > 20000 else 1.0
            cx = (x0 + x1) / 2 / scale; cy = (y0 + y1) / 2 / scale
            per_layer[lay] += 1
            who = inside(cx, cy)
            if who:
                per_layer_in[lay] += 1
                if lay in ('Metal1', 'Metal2', 'Metal3', 'Metal4'):
                    per_macro[who] += 1; per_net[net] += 1
                    if lay == 'Metal4':
                        pairs[(net, who)] += 1
print('guide boxes per layer (inside macro outline / total):')
for lay in sorted(per_layer):
    print(f'  {lay:10s} {per_layer_in[lay]:8d} / {per_layer[lay]}')
print('macros with the most M1-M4 guide boxes inside:')
for k, v in per_macro.most_common(8):
    print(f'  {v:6d}  {k}')
print(f'nets with M1-M4 guides inside macros: {len(per_net)}; top:')
for k, v in per_net.most_common(8):
    print(f'  {v:6d}  {k}')
if dump:
    with open(dump, 'w') as fh:
        for (n, m), v in sorted(pairs.items(), key=lambda kv: -kv[1]):
            fh.write(f'{v} {n} {m}\n')
    print(f'wrote {dump}: {len(pairs)} (net, macro) pairs with Metal4 guides inside')
