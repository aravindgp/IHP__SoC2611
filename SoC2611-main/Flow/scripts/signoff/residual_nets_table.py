#!/usr/bin/env python3
"""Table of the nets with power shorts inside SRAM macros after an ECO round: crossing macro and orientation, macro
pins with their true pin edge (south for R0/MY, north for MX/R180), standard cells with coordinates, shorts and the
supplies touched (VDD and VSS both = direct supply short).
usage: residual_nets_table.py <pins.log> <pairs.txt> <macros.txt> <place.pl> <drc.rpt> > table.txt"""
import collections
import re
import sys

pins_f, pairs_f, mac_f, pl_f, rpt = sys.argv[1:6]
wh = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac_f) if len(l.split()) == 4}
mac = {}
for l in open(pl_f):
    p = l.split()
    if len(p) == 4 and p[0] in wh:
        w, h = wh[p[0]]; mac[p[0]] = (float(p[1]), float(p[2]), float(p[1]) + w, float(p[2]) + h, p[3])
pins = collections.defaultdict(list)
for l in open(pins_f, errors='replace'):
    p = l.split()
    if p and p[0] == 'PIN': pins[p[1]].append((p[2], float(p[3]), float(p[4]), p[5] if len(p) > 5 else ''))
cross = {}
for l in open(pairs_f):
    p = l.split()
    if len(p) == 3: cross.setdefault(p[1], p[2])
sup = collections.defaultdict(set); cnt = collections.Counter(); boxes = collections.defaultdict(list)
for b in open(rpt, errors='replace').read().split('violation type:')[1:]:
    m = re.search(r'srcs:(.*)', b)
    if not m or 'Metal4' not in b or not b.strip().startswith('Short'): continue
    srcs = re.findall(r'net:(\S+)', m.group(1))
    s_ = [s for s in srcs if re.fullmatch(r'(?i)(vdd\w*|vss\w*)', s.split('/')[-1])]
    for s in srcs:
        if s not in s_ and s_:
            sup[s].update(x.split('/')[-1] for x in s_); cnt[s] += 1
            bb = re.search(r'bbox = \(([^)]*)\) - \(([^)]*)\)', b); boxes[s].append(bb.group(1) + ' / ' + bb.group(2) if bb else '')
print('# residual power shorts inside SRAM macros (coordinates in um, die 6600 x 6600, origin bottom-left).')
print('# RM_IHPSG13 pins: 0.26 um Metal2 squares on the macro edge: south edge for orientation R0/MY, north edge for MX/R180.')
print('# For each net: the macro it crosses, its macro pin(s) with the pin edge, its standard cells, shorts and supplies touched.\n')
for n in sorted(cross, key=lambda k: -cnt[k]):
    m = cross[n]; x0, y0, x1, y1, o = mac[m]
    print(f'NET {n}')
    print(f'  crosses macro {m.split("/")[-2]}/{m.split("/")[-1]}  box ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) orient {o}  '
          f'(pins on the {"south" if o in ("R0", "MY") else "north"} edge)')
    both = len({s[:3].upper() for s in sup[n]}) > 1
    print(f'  shorts {cnt[n]} on Metal4, supplies touched {sorted(sup[n])}  {"<-- VDD and VSS both: direct supply short" if both else ""}')
    for inst, x, y, c in pins[n]:
        if inst in mac:
            mx0, my0, mx1, my1, mo = mac[inst]; pe = my0 if mo in ('R0', 'MY') else my1
            print(f'  MACRO-PIN {inst.split("/")[-2]}/{inst.split("/")[-1]} orient {mo} pin edge y={pe:.1f} '
                  f'(macro box ({mx0:.1f},{my0:.1f})-({mx1:.1f},{my1:.1f}))')
        else:
            print(f'  CELL {inst} at ({x:.1f},{y:.1f}) {c}')
    for bb in boxes[n][:6]: print(f'  short bbox {bb}')
    print()
