#!/usr/bin/env python3
"""Std-cell density (cell area / row area) per bin inside a window, from dump_density.tcl output.
usage: dens_window.py <place.txt> x0 y0 x1 y1 [bin_um=100]   (um; prints a grid, rows from the top)"""
import sys

fn = sys.argv[1]
x0, y0, x1, y1 = map(float, sys.argv[2:6])
b = float(sys.argv[6]) if len(sys.argv) > 6 else 100.0
nx = int(round((x1 - x0) / b)); ny = int(round((y1 - y0) / b))
cell = [[0.0] * nx for _ in range(ny)]
rowa = [[0.0] * nx for _ in range(ny)]
mac = [[0.0] * nx for _ in range(ny)]
dbu = 1000.0


def add(grid, X0, Y0, X1, Y1):
    for j in range(ny):
        by0 = y0 + j * b; by1 = by0 + b
        oy = min(Y1, by1) - max(Y0, by0)
        if oy <= 0:
            continue
        for i in range(nx):
            bx0 = x0 + i * b; bx1 = bx0 + b
            ox = min(X1, bx1) - max(X0, bx0)
            if ox > 0:
                grid[j][i] += ox * oy


for l in open(fn):
    p = l.split()
    if not p:
        continue
    k = p[0]
    if k in ('C', 'ROW', 'MACRO'):
        X0, Y0, X1, Y1 = (float(v) / dbu for v in p[1:5])
        if X1 <= x0 or X0 >= x1 or Y1 <= y0 or Y0 >= y1:
            continue
        add({'C': cell, 'ROW': rowa, 'MACRO': mac}[k], X0, Y0, X1, Y1)
tc = sum(map(sum, cell)); tr = sum(map(sum, rowa)); tm = sum(map(sum, mac))
free = tr - tm
print(f'window x {x0:.0f}-{x1:.0f} y {y0:.0f}-{y1:.0f}: cell area {tc:.0f} um2, row area {tr:.0f}, macro area {tm:.0f}, '
      f'density on free row area {100 * tc / free if free > 0 else 0:.1f}%')
print('      ' + ' '.join(f'{x0 + i * b:5.0f}' for i in range(nx)))
for j in reversed(range(ny)):
    cells = []
    for i in range(nx):
        f = rowa[j][i] - mac[j][i]
        cells.append('  mac' if f <= 0.05 * b * b else f'{100 * cell[j][i] / f:5.0f}')
    print(f'{y0 + j * b:5.0f} ' + ' '.join(cells))
