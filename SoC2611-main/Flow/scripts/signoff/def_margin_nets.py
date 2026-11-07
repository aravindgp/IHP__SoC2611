#!/usr/bin/env python3
"""List the signal nets whose routing in a DEF leaves the core box (spilled into the pad-ring margin).
usage: def_margin_nets.py <in.def> <out_list.txt> [core_lo_um=340] [core_hi_um=6260]
Streams the NETS section (not SPECIALNETS); a routed point ( x y ) with '*' repeats the previous coordinate."""
import re
import sys

src, dst = sys.argv[1:3]
lo_um = float(sys.argv[3]) if len(sys.argv) > 3 else 340.0
hi_um = float(sys.argv[4]) if len(sys.argv) > 4 else 6260.0
pt = re.compile(r'\(\s*(\S+)\s+(\S+)(?:\s+\S+)?\s*\)')
dbu = 1000
in_nets = False
name = None
out = False
px = py = 0
hits = []
total = 0
with open(src, errors='replace') as f:
    for line in f:
        s = line.strip()
        if s.startswith('UNITS DISTANCE MICRONS'):
            dbu = int(s.split()[3])
        if not in_nets:
            if s.startswith('NETS '):
                in_nets = True
                lo, hi = lo_um * dbu, hi_um * dbu
            continue
        if s.startswith('END NETS'):
            break
        if s.startswith('- '):
            if name is not None and out:
                hits.append(name)
            name = s.split()[1]
            out = False
            total += 1
            continue
        if out or name is None:
            continue
        # routing statements only: "+ ROUTED ..." / "NEW ..." (the "( inst pin )" connection lines also match pt)
        if not (s.startswith('+ ROUTED') or s.startswith('NEW') or s.startswith('+ FIXED') or s.startswith('+ COVER')):
            continue
        for m in pt.finditer(s):
            xs, ys = m.group(1), m.group(2)
            x = px if xs == '*' else int(xs)
            y = py if ys == '*' else int(ys)
            px, py = x, y
            if x < lo or x > hi or y < lo or y > hi:
                out = True
                break
    if name is not None and out:
        hits.append(name)
with open(dst, 'w') as g:
    g.write('\n'.join(hits) + '\n')
print(f'DEF_MARGIN {len(hits)} of {total} nets have routing outside the core box -> {dst}')
