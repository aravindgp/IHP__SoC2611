#!/usr/bin/env python3
"""Cells whose location/orientation differs between two dump_loc.tcl dumps (pre/post legalisation), written as
<out_cells.txt>. usage: loc_diff_nets.py <loc_pre.txt> <loc_post.txt> <out_cells.txt>"""
import sys

pre, post, out = sys.argv[1:4]
a = {}
for ln in open(pre):
    p = ln.split()
    if len(p) >= 4:
        a[p[0]] = (p[1], p[2], p[3])
moved = []
for ln in open(post):
    p = ln.split()
    if len(p) >= 4 and p[0] in a and a[p[0]] != (p[1], p[2], p[3]):
        moved.append(p[0])
open(out, 'w').write('\n'.join(moved) + '\n')
print(f"LOC_DIFF {len(moved)} instances moved (of {len(a)} compared) -> {out}")
