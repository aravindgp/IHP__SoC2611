#!/usr/bin/env python3
"""ASCII map (250 um bins) and type/layer/net-owner breakdown of a drt::check_drc report.
usage: drc_map.py <drc.rpt> [label]"""
import collections
import re
import sys


def owner(n):
    if 'gen1_pcore_i' in n:
        return 'PCORE' + re.search(r'gen_reg\\?\[(\d)', n).group(1)
    if n.startswith('soc_i/ztachip_inst/dp_'):
        return 'datapath'
    if n.startswith('soc_i/ztachip_inst/core_i/gen_stream'):
        return 'streams'
    if n.startswith('soc_i/ztachip_inst/core_i'):
        return 'zcore'
    if n.startswith('soc_i/ztachip_inst/'):
        return 'zmem'
    if n.startswith('soc_i/axi_'):
        return 'axi'
    if n.startswith('soc_i/gen_cpu') or n.startswith('soc_i/tcm') or n.startswith('soc_i/uart'):
        return 'cpu'
    if n.startswith('clk'):
        return 'clock'
    if n in ('VDD', 'VSS', 'IOVDD', 'IOVSS'):
        return 'power'
    return 'other'


f = sys.argv[1]
lab = sys.argv[2] if len(sys.argv) > 2 else f
txt = open(f, errors='replace').read()
blocks = txt.split('violation type:')[1:]
grid = collections.Counter(); typ = collections.Counter(); lay = collections.Counter(); own = collections.Counter()
for b in blocks:
    t = b.split('\n', 1)[0].strip()
    bb = re.search(r'bbox = \(\s*([\d.]+),\s*([\d.]+)\s*\)\s*-\s*\(\s*([\d.]+),\s*([\d.]+)\s*\)\s*on Layer\s*(\S+)', b)
    if not bb:
        continue
    x0, y0 = float(bb.group(1)), float(bb.group(2)); L = bb.group(5)
    grid[(int(x0 // 250), int(y0 // 250))] += 1; typ[t] += 1; lay[L] += 1
    nets = re.findall(r'net:(\S+)', b)
    for n in nets:
        own[owner(n)] += 1 / max(len(nets), 1)
tot = len(blocks)
print(f'===== {lab}: {tot} markers')
print('  types :', ', '.join(f'{k} {v}' for k, v in typ.most_common(6)))
print('  layers:', ', '.join(f'{k} {v}' for k, v in lay.most_common(8)))
print('  nets  :', ', '.join(f'{k} {100 * v / tot:.0f}%' for k, v in own.most_common(8)))
mx = max(grid.values())
for gy in range(25, -1, -1):
    print(f'{gy * 250:5d} |' + ''.join((' .:-=+*#%@'[min(9, int(9 * grid.get((gx, gy), 0) / mx))] if grid.get((gx, gy), 0) else ' ')
                                    for gx in range(27)) + '|')
print('      ' + ''.join(str((gx * 250) // 1000) if gx % 4 == 0 else ' ' for gx in range(27)) + '  (x in mm, 250 um bins)')
top = sorted(grid.items(), key=lambda kv: -kv[1])[:6]
print('  top bins:', [((gx * 250, gy * 250), v) for (gx, gy), v in top])
