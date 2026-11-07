#!/usr/bin/env python3
"""Soft channel for the west-edge nets (GRT-free, a rewrite of the GRT guides):
1. band boxes (x < INNER) of non-pad nets are projected inside, as guide_clamp.py does, but SPREAD over the strip's
   gcell columns instead of one column (run D crowded everything into x 316.8..324);
2. for half of the nets, the strip boxes next to the SRAM array (y < YTOP) are translated east into the clean gap
   between SRAM columns 1 and 2 (x 784.8..828.0, 6 gcell columns), the row-gap connector boxes are extended east to
   reach it, and one Metal3 bridge box just above the array (y 1670.4..1677.6) reconnects the net's northern strip
   run. Pad nets (KEEP) untouched. Coordinates in dbu (1000/um), gcell 7.2 um from the die origin.
usage: guide_soft.py <in.guide> <out.guide> <keep_nets.txt>"""
import sys
import zlib

src, dst, keepf = sys.argv[1:4]
DIE = 6600000
G = 7200
INNER = 316800              # first gcell boundary inside the IO band
HI = DIE - INNER
STRIP_COLS = [INNER + G * k for k in range(6)]       # 316.8 .. 360.0 (strip legal to 365.7)
GAP_COLS = [784800 + G * k for k in range(6)]        # 784.8 .. 828.0 (gap 782.34..832.26)
GAP_EAST = 828000
STRIP_X1 = 370000           # a box ending here or west of it is a strip/band box
YTOP = 1700000              # SRAM column 1 spans y 365.2..1665.4 um
BRIDGE = (1670400, 1677600) # one gcell row above the array
keep = set(l.strip() for l in open(keepf) if l.strip())

nets = {}
order = []
cur = None
for ln in open(src):
    p = ln.split()
    if len(p) == 1 and p[0] not in '()':
        cur = p[0]
        order.append(cur)
        nets[cur] = []
    elif len(p) == 5:
        nets[cur].append([int(p[0]), int(p[1]), int(p[2]), int(p[3]), p[4]])


def clamp(b):
    x0, y0, x1, y1, l = b
    if x0 < INNER:
        x0 = INNER
        if x1 <= INNER:
            x1 = INNER + G
    if x1 > HI:
        x1 = HI
        if x0 >= HI:
            x0 = HI - G
    if y0 < INNER:
        y0 = INNER
        if y1 <= INNER:
            y1 = INNER + G
    if y1 > HI:
        y1 = HI
        if y0 >= HI:
            y0 = HI - G
    return [x0, y0, x1, y1, l]


stats = dict(nets=0, strip=0, gap=0, moved=0, ext=0, bridge=0)
out = open(dst, 'w')
for name in order:
    boxes = nets[name]
    if name in keep:
        out.write(name + '\n(\n' + ''.join(f"{b[0]} {b[1]} {b[2]} {b[3]} {b[4]}\n" for b in boxes) + ')\n')
        continue
    west = any(b[0] < INNER for b in boxes)
    if not west:
        # east/south/north band boxes: plain projection inside, as guide_clamp.py
        out.write(name + '\n(\n' + ''.join(f"{b[0]} {b[1]} {b[2]} {b[3]} {b[4]}\n" for b in map(clamp, boxes)) + ')\n')
        continue
    stats['nets'] += 1
    h = zlib.crc32(name.encode()) % 12
    col = STRIP_COLS[h % 6]
    to_gap = h >= 6 and any(b[0] < INNER and b[1] < YTOP for b in boxes)
    stats['gap' if to_gap else 'strip'] += 1
    new = []
    translated = northern = False
    for b in boxes:
        x0, y0, x1, y1, l = b
        in_strip = x1 <= STRIP_X1
        if x0 < INNER and in_strip:
            # a band/strip box: project onto this net's strip column
            w = max(G, min(x1, INNER + G) - INNER) if x1 > INNER else G
            nb = [col, max(y0, INNER), col + G, min(y1, HI), l]
            if nb[3] <= nb[1]:
                nb[3] = nb[1] + G
            if to_gap and y0 < YTOP:
                nb[0] = GAP_COLS[h % 6]
                nb[2] = nb[0] + G
                translated = True
                stats['moved'] += 1
            elif y0 >= YTOP:
                northern = True
            new.append(nb)
        elif x0 < STRIP_X1 < x1 and to_gap and y0 < YTOP:
            # row-gap connector from the strip across the SRAM pins: extend east to the gap channel
            nb = clamp(b)
            nb[2] = max(nb[2], GAP_EAST)
            new.append(nb)
            stats['ext'] += 1
        else:
            nb = clamp(b)
            if nb[2] <= STRIP_X1 and nb[1] >= YTOP:
                northern = True
            new.append(nb)
    if translated and northern:
        new.append([INNER, BRIDGE[0], GAP_EAST, BRIDGE[1], 'Metal3'])
        stats['bridge'] += 1
    out.write(name + '\n(\n' + ''.join(f"{b[0]} {b[1]} {b[2]} {b[3]} {b[4]}\n" for b in new) + ')\n')
out.close()
print('GUIDE_SOFT ' + ' '.join(f"{k}={v}" for k, v in stats.items()) + f" keep={len(keep)} -> {dst}")
