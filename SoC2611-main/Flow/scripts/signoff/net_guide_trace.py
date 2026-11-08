#!/usr/bin/env python3
"""For a few nets: their pins (from nets_pins_xy.tcl output, with the planned moves applied) and the y-extent of
their guide boxes per layer inside the x-span of a macro, to see whether the guides cross the macro's y-span.
usage: net_guide_trace.py <route.guide> <nets_pins.log> <moves.txt> <macros.txt> <place.pl> <macro_substring> [n=5]"""
import collections
import sys

guide, log, moves, mac, pl, key = sys.argv[1:7]
n = int(sys.argv[7]) if len(sys.argv) > 7 else 5
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
for l in open(pl):
    p = l.split()
    if len(p) == 4 and key in p[0] and p[0] in S:
        name, x0, y0 = p[0], float(p[1]), float(p[2])
        x1, y1 = x0 + S[p[0]][0], y0 + S[p[0]][1]
print(f'macro {name.replace("soc_i/", "")}: x {x0:.0f}-{x1:.0f} y {y0:.0f}-{y1:.0f}')
mv = {}
for l in open(moves):
    p = l.split()
    if p and p[0] == 'MOVE':
        mv[p[1]] = (float(p[2]), float(p[3]))
pins = collections.defaultdict(list)
for l in open(log):
    p = l.split()
    if p and p[0] == 'PIN':
        x, y = mv.get(p[2], (float(p[3]), float(p[4])))
        pins[p[1]].append((p[2].split('/')[-1][-18:], x, y, p[2] in mv))
sel = [net for net, ps in pins.items() if any(m for _, _, _, m in ps)]
# nets with a moved cell whose other pins are near this macro
sel = [net for net in sel if any(x0 - 300 < x < x1 + 300 and y0 - 400 < y < y1 + 400 for _, x, y, _ in pins[net])][:n]
want = set(sel)
boxes = collections.defaultdict(lambda: collections.defaultdict(list))
cur = None
with open(guide) as fh:
    for l in fh:
        if l[0] == '(':
            continue
        if l[0] == ')':
            cur = None
            continue
        p = l.split()
        if len(p) == 1:
            cur = p[0] if p[0] in want else None
        elif cur and len(p) == 5:
            gx0, gy0, gx1, gy1 = (float(v) / 1000.0 for v in p[:4])
            if gx0 < x1 and gx1 > x0:
                boxes[cur][p[4]].append((gy0, gy1))
for net in sel:
    ys = sorted(set(round(y) for _, _, y, _ in pins[net]))
    moved = [(c, round(x), round(y)) for c, x, y, m in pins[net] if m]
    print(f'\n{net.replace("soc_i/", "")[-70:]}: {len(pins[net])} pins, y values {ys[:12]}, moved {moved}')
    for lay, bs in boxes[net].items():
        inside = [b for b in bs if b[0] < y1 and b[1] > y0]
        print(f'   {lay}: {len(bs)} boxes in the macro x-span, {len(inside)} overlapping its y-span '
              f'{"(y " + str(sorted(set(round(b[0]) for b in inside))[:8]) + ")" if inside else ""}')
