#!/usr/bin/env python3
"""Engine macro_placements JSON (inst:origin_x:origin_y:orient) -> MPL-style .pl (inst llx lly orient, um).
usage: placements_to_pl.py <macros.txt name w h> <in.json> <out.pl>"""
import json
import sys

mac, src, out = sys.argv[1:4]
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
with open(out, 'w') as fh:
    for e in json.load(open(src))['macro_placements']:
        n, ox, oy, o = e.rsplit(':', 3)
        w, h = S[n]
        ox, oy = float(ox), float(oy)
        x = ox - (w if o in ('MY', 'R180') else 0.0)
        y = oy - (h if o in ('MX', 'R180') else 0.0)
        fh.write(f'{n} {x:.2f} {y:.2f} {o}\n')
print('wrote', out)
