#!/usr/bin/env python3
"""Signal nets that share a marker with VDD/VSS in a TritonRoute DRC report.
usage: supply_nets_from_rpt.py <drc.rpt> <nets_out> <pairs_out>   (pairs: '1 <net> pwr', input of nets_pins_xy_exact.tcl)"""
import re
import sys

rpt, nets_out, pairs_out = sys.argv[1:4]
nets = []
for b in open(rpt, errors='replace').read().split('violation type:')[1:]:
    m = re.search(r'srcs:(.*)', b)
    if not m:
        continue
    ns = [s[4:] for s in m.group(1).split() if s.startswith('net:')]
    sup = [s for s in ns if re.fullmatch(r'(?i)(vdd\w*|vss\w*)', s.split('/')[-1])]
    if not sup:
        continue
    for s in ns:
        if s not in sup and s not in nets:
            nets.append(s)
open(nets_out, 'w').write(''.join(n + '\n' for n in nets))
open(pairs_out, 'w').write(''.join(f'1 {n} pwr\n' for n in nets))
print(f'# supply-short nets: {len(nets)}')
