#!/usr/bin/env python3
"""(net, macro) pairs of the power shorts inside macros of a check_drc report, in the "<count> <net> <macro>" format
of net_macro_cross.tcl / nets_pins_xy.tcl.  usage: drc_pairs.py <drc.rpt> <macros.txt> <place.pl> > pairs.txt"""
import collections
import re
import sys

fn, mac, pl = sys.argv[1:4]
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
P = {}
for l in open(pl):
    p = l.split()
    if len(p) == 4 and p[0] in S:
        P[p[0]] = (float(p[1]), float(p[2]), float(p[1]) + S[p[0]][0], float(p[2]) + S[p[0]][1])
cnt = collections.Counter()
typ = srcs = ''
for l in open(fn):
    if l.startswith('violation type:'):
        typ = l.split(':', 1)[1].strip()
    elif l.strip().startswith('srcs:'):
        srcs = l
    elif 'bbox' in l and typ == 'Short' and ('net:VDD' in srcs or 'net:VSS' in srcs):
        m = re.search(r'\(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)', l)
        if not m or m.group(5) not in ('Metal4', 'TopMetal1', 'Metal2', 'Metal3'):
            continue
        x = (float(m.group(1)) + float(m.group(3))) / 2
        y = (float(m.group(2)) + float(m.group(4))) / 2
        for n, (x0, y0, x1, y1) in P.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                for s in srcs.split():
                    if s.startswith('net:') and s not in ('net:VDD', 'net:VSS'):
                        cnt[(s[4:], n)] += 1
                break
for (net, m), c in cnt.most_common():
    print(c, net, m)
print(f'# {len(cnt)} pairs, {len({n for n, _ in cnt})} nets, {len({m for _, m in cnt})} macros', file=sys.stderr)
