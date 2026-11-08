#!/usr/bin/env python3
"""How deep the signal pins of a macro LEF reach into the macro from its pin edge (y from the south edge, R0), per
layer, and the OBS layers with their rect counts.  usage: lef_pin_depth.py <macro.lef> ..."""
import re
import sys

for fn in sys.argv[1:]:
    size = None
    pin = None
    layer = None
    in_obs = False
    depth = {}
    obs = {}
    for l in open(fn):
        p = l.split()
        if not p:
            continue
        if p[0] == 'SIZE':
            size = (float(p[1]), float(p[3]))
        elif p[0] == 'PIN':
            pin = p[1]
        elif p[0] == 'OBS':
            in_obs = True
        elif p[0] == 'END' and len(p) == 1:
            in_obs = False
        elif p[0] == 'END' and pin and p[1] == pin:
            pin = None
        elif p[0] == 'LAYER':
            layer = p[1]
        elif p[0] == 'RECT' and layer:
            y0, y1 = float(p[2]), float(p[4])
            if in_obs:
                obs[layer] = obs.get(layer, 0) + 1
            elif pin and not pin.endswith('!'):
                d = depth.setdefault(layer, [1e9, 0, 0])
                d[0] = min(d[0], y0)
                d[1] = max(d[1], y1)
                d[2] += 1
    print(f'{fn.split("/")[-1]} size {size[0]} x {size[1]}')
    for k, (a, b, n) in depth.items():
        print(f'  signal pins {k}: {n} rects, y {a:.2f} .. {b:.2f} (depth {b:.2f} um from the south edge)')
    print(f'  OBS rects per layer: {obs}')
