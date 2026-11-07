#!/usr/bin/env python3
"""Move named macros in a .pl placement.  usage: fp_move_macros.py <in.pl> <out.pl> "<name_substring>=x,y,ORIENT" ...
Each substring must match exactly one macro name; coordinates are the lower-left corner in um."""
import sys

src, out = sys.argv[1:3]
moves = []
for spec in sys.argv[3:]:
    key, val = spec.split('=', 1)
    x, y, o = val.split(',')
    moves.append((key, float(x), float(y), o))
rows = [l.split() for l in open(src) if len(l.split()) == 4]
for key, x, y, o in moves:
    hits = [r for r in rows if key in r[0]]
    if len(hits) != 1:
        sys.exit(f'{key}: {len(hits)} matches')
    r = hits[0]
    print(f'{r[0][-70:]}: ({r[1]}, {r[2]}, {r[3]}) -> ({x}, {y}, {o})')
    r[1], r[2], r[3] = f'{x:.2f}', f'{y:.2f}', o
with open(out, 'w') as fh:
    for r in rows:
        fh.write(' '.join(r) + '\n')
print(f'wrote {out}: {len(rows)} macros, {len(moves)} moved')
