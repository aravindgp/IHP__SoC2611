#!/usr/bin/env python3
"""Nets named in DRT markers whose bbox centre lies at x < XMAX um (default 320: the west IO band), supplies excluded.
usage: west_marker_nets.py <route_drc.rpt> <out.txt> [xmax=320]"""
import re
import sys

pat = re.compile(r"bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)")
xmax = float(sys.argv[3]) if len(sys.argv) > 3 else 320.0
nets = set()
for b in open(sys.argv[1], errors='replace').read().split("violation type:")[1:]:
    m = pat.search(b)
    if not m:
        continue
    if (float(m.group(1)) + float(m.group(3))) / 2 < xmax:
        for n in re.findall(r"net:(\S+)", b):
            if n not in ('IOVSS', 'IOVDD', 'VDD', 'VSS'):
                nets.add(n)
open(sys.argv[2], 'w').write('\n'.join(sorted(nets)) + '\n')
print(f"WEST_MARKER_NETS {len(nets)}")
