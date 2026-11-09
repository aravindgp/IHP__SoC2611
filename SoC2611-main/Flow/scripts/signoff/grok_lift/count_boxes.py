#!/usr/bin/env python3
"""Marker counts of DRC reports in the fixed boxes used to compare the lift ECOs:
slice[27]'s bottom-edge strip, the old-jog column x 2822-2838, the column x 2838-2860, slice[27]'s new footprint.
usage: count_boxes.py <drc.rpt> [<drc.rpt> ...]"""
import re
import sys

BOXES = [('edge y2929-2931', (2880, 2929, 3125, 2931)), ('col 2822-2838', (2822, 2742, 2838, 3018)),
         ('col 2838-2860', (2838, 2742, 2860, 3018)), ('footprint+1um', (2882.9, 2929.4, 3121.7, 2995.8))]
for rpt in sys.argv[1:]:
    c = {k: 0 for k, _ in BOXES}
    for b in open(rpt, errors='replace').read().split('violation type:')[1:]:
        bb = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)', b)
        if not bb:
            continue
        x = (float(bb.group(1)) + float(bb.group(3))) / 2; y = (float(bb.group(2)) + float(bb.group(4))) / 2
        for k, (x0, y0, x1, y1) in BOXES:
            if x0 <= x <= x1 and y0 <= y <= y1:
                c[k] += 1
    print(rpt.split('/')[-1], ' | '.join(f'{k} {v}' for k, v in c.items()))
