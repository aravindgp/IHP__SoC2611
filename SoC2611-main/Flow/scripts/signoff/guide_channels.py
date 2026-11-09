#!/usr/bin/env python3
"""Explicit routing guides through the macro-free space for nets the global router sent across SRAM macros.
For each net: a breadth-first path on a coarse grid over the core, with every macro outline (plus a halo) as an
obstacle, from pin to pin in nearest-neighbour order; the path cells become guide boxes (merged runs) that the
detailed router follows instead of the router's own macro-crossing guides.
usage: guide_channels.py <pins_exact.log> <nets.txt> <macros.txt> <place.pl> <out_guides.txt> [grid_um=4] [halo_um=3]
pins_exact.log: "PIN <net> <inst|PORT> <x> <y> <master>" (nets_pins_xy_exact.tcl: true pin positions)
out: one line per box "net layer x0 y0 x1 y1" (um) for layers Metal2 Metal3 Metal4; pin boxes included."""
import collections
import heapq
import sys

pins_f, nets_f, mac_f, pl_f, out_f = sys.argv[1:6]
G = float(sys.argv[6]) if len(sys.argv) > 6 else 4.0
HALO = float(sys.argv[7]) if len(sys.argv) > 7 else 3.0
DIE = 6600.0; CORE = (340.0, 340.0, 6260.0, 6260.0)

wh = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac_f) if len(l.split()) == 4}
macs = []
for l in open(pl_f):
    p = l.split()
    if len(p) == 4 and p[0] in wh:
        w, h = wh[p[0]]; x, y = float(p[1]), float(p[2]); macs.append((x, y, x + w, y + h))
nets = [l.strip() for l in open(nets_f) if l.strip()]
pins = collections.defaultdict(list)
for l in open(pins_f, errors='replace'):
    p = l.split()
    if p and p[0] == 'PIN' and p[1] in nets:
        pins[p[1]].append((float(p[3]), float(p[4]), p[2]))

# grid: blocked cells = inside a macro + halo
nx = int((CORE[2] - CORE[0]) / G) + 1; ny = int((CORE[3] - CORE[1]) / G) + 1
blocked = bytearray(nx * ny)
for (x0, y0, x1, y1) in macs:
    i0 = max(0, int((x0 - HALO - CORE[0]) / G)); i1 = min(nx - 1, int((x1 + HALO - CORE[0]) / G))
    j0 = max(0, int((y0 - HALO - CORE[1]) / G)); j1 = min(ny - 1, int((y1 + HALO - CORE[1]) / G))
    for j in range(j0, j1 + 1):
        base = j * nx
        for i in range(i0, i1 + 1): blocked[base + i] = 1

def cell(x, y): return (min(nx - 1, max(0, int((x - CORE[0]) / G))), min(ny - 1, max(0, int((y - CORE[1]) / G))))
def um(i, j): return (CORE[0] + i * G, CORE[1] + j * G)

def free_near(c):
    """a macro pin lies inside the macro outline: step out to the nearest free cell"""
    i, j = c
    if not blocked[j * nx + i]: return c
    for r in range(1, 40):
        for di, dj in ((0, r), (0, -r), (r, 0), (-r, 0), (r, r), (-r, -r), (r, -r), (-r, r)):
            ii, jj = i + di, j + dj
            if 0 <= ii < nx and 0 <= jj < ny and not blocked[jj * nx + ii]: return (ii, jj)
    return c

def astar(a, b):
    """4-neighbour A* with a small penalty for turns (prefers straight channel runs)"""
    openq = [(0, 0, a, None)]; best = {a: 0}; prev = {}
    while openq:
        f, g, c, d = heapq.heappop(openq)
        if c == b: break
        if g > best.get(c, 1e18): continue
        i, j = c
        for nd in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ii, jj = i + nd[0], j + nd[1]
            if not (0 <= ii < nx and 0 <= jj < ny) or blocked[jj * nx + ii]: continue
            ng = g + 1 + (0.3 if d is not None and nd != d else 0)
            if ng < best.get((ii, jj), 1e18):
                best[(ii, jj)] = ng; prev[(ii, jj)] = (c, nd)
                heapq.heappush(openq, (ng + abs(ii - b[0]) + abs(jj - b[1]), ng, (ii, jj), nd))
    if b not in prev and a != b: return None
    path = [b]
    while path[-1] != a: path.append(prev[path[-1]][0])
    return path[::-1]

def boxes_of(path):
    """merge straight runs into boxes (um), one grid cell wide plus a margin"""
    out = []; k = 0
    while k < len(path):
        m = k
        while m + 1 < len(path) and (path[m + 1][0] == path[k][0] or path[m + 1][1] == path[k][1]) and \
                (m == k or (path[m + 1][0] - path[m][0], path[m + 1][1] - path[m][1]) == (path[m][0] - path[m - 1][0], path[m][1] - path[m - 1][1])):
            m += 1
        (xa, ya), (xb, yb) = um(*path[k]), um(*path[m])
        out.append((min(xa, xb) - G / 2, min(ya, yb) - G / 2, max(xa, xb) + G + G / 2, max(ya, yb) + G + G / 2))
        k = m if m > k else k + 1
        if m == k: k += 1
    return out

fo = open(out_f, 'w'); stats = collections.Counter()
for n in nets:
    ps = pins.get(n, [])
    if len(ps) < 2: stats['skipped (<2 pins)'] += 1; continue
    cells = [free_near(cell(x, y)) for x, y, _ in ps]
    # nearest-neighbour chaining from the first pin
    order = [0]; left = set(range(1, len(cells)))
    while left:
        last = cells[order[-1]]
        nxt = min(left, key=lambda k: abs(cells[k][0] - last[0]) + abs(cells[k][1] - last[1]))
        order.append(nxt); left.remove(nxt)
    allboxes = []; ok = True
    for a, b in zip(order, order[1:]):
        path = astar(cells[a], cells[b])
        if path is None: ok = False; break
        allboxes += boxes_of(path)
    if not ok: stats['no path'] += 1; print(f'NO PATH {n}', file=sys.stderr); continue
    for x, y, _ in ps:                         # pin access boxes
        allboxes.append((x - 2.0, y - 2.0, x + 2.0, y + 2.0))
    for (x0, y0, x1, y1) in allboxes:
        for layer in ('Metal2', 'Metal3', 'Metal4'):
            fo.write(f'{n} {layer} {x0:.2f} {y0:.2f} {x1:.2f} {y1:.2f}\n')
    stats['guided'] += 1; stats['boxes'] += len(allboxes)
fo.close()
print(f'# guide_channels: {dict(stats)}', file=sys.stderr)
