#!/usr/bin/env python3
"""Bin the pins dumped by nets_pins_xy.tcl into named boxes (pockets, margin strips): how many of the crossing nets'
pins sit in the dead spaces around the macro stacks.  usage: pins_in_boxes.py <nets_pins.log> <m4_pairs.txt> "<name>=x0,y0,x1,y1" ..."""
import collections
import sys

log, pairs = sys.argv[1:3]
boxes = {}
for a in sys.argv[3:]:
    k, v = a.split('=')
    boxes[k] = tuple(float(t) for t in v.split(','))
pins = collections.defaultdict(list)
for l in open(log):
    p = l.split()
    if p and p[0] == 'PIN':
        pins[p[1]].append((float(p[3]), float(p[4]), p[2] == 'PORT'))
macro_of = {}
for l in open(pairs):
    p = l.split()
    if len(p) == 3:
        macro_of.setdefault(p[1], p[2])


def hits(x, y):
    return [k for k, (x0, y0, x1, y1) in boxes.items() if x0 <= x <= x1 and y0 <= y <= y1]


by_region = collections.Counter()
nets_with = collections.Counter()
ports = 0
for n, ps in pins.items():
    hit = set()
    for x, y, port in ps:
        ports += port
        for k in hits(x, y):
            by_region[k] += 1
            hit.add(k)
    for k in hit:
        nets_with[k] += 1
print(f'nets {len(pins)}  pins {sum(len(v) for v in pins.values())}  port pins {ports}')
for k in boxes:
    print(f'  {k:26s} pins {by_region[k]:4d}  nets with a pin there {nets_with[k]:3d}')
print('per crossed macro: nets, pins in boxes')
per = collections.defaultdict(lambda: [0, collections.Counter()])
for n, m in macro_of.items():
    if n not in pins:
        continue
    per[m][0] += 1
    for x, y, port in pins[n]:
        for k in hits(x, y):
            per[m][1][k] += 1
for m, (c, cnt) in sorted(per.items(), key=lambda t: -t[1][0]):
    s = m.replace('soc_i/', '').split('/')
    print(f'  {c:3d} nets  {dict(cnt)}  {"/".join(s[-4:-1])[-70:]}')
