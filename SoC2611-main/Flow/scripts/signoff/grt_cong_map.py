#!/usr/bin/env python3
"""Where does the global-route overflow sit?  Reads an OpenROAD congestion report (violation blocks with srcs nets,
comment capacity/usage/overflow, bbox), prints the overflow share per net owner block, H/V split, and an ASCII map
of 250 um bins.  usage: grt_cong_map.py <congestion.rpt> [label]"""
import collections
import re
import sys


def block_of(n):
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
    if n.startswith('clknet') or n.startswith('clk'):
        return 'clock'
    if n.startswith('HFN'):
        return 'hfn(reset/tie)'
    if n.startswith('hb_i'):
        return 'hyperbus'
    return 'other'


f = sys.argv[1]
lab = sys.argv[2] if len(sys.argv) > 2 else f
txt = open(f, errors='replace').read()
blocks = txt.split('violation type:')[1:]
grid = collections.Counter(); tot = 0; xs = []; hv = collections.Counter(); own = collections.Counter()
for b in blocks:
    m = re.search(r'overflow:(\d+)', b)
    bb = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)', b)
    if not m or not bb:
        continue
    ov = int(m.group(1)); x0, y0 = float(bb.group(1)), float(bb.group(2))
    tot += ov; xs.append(x0); grid[(int(x0 // 250), int(y0 // 250))] += ov
    hv['H' if b.lstrip().startswith('Horizontal') else 'V'] += ov
    nets = re.findall(r'net:(\S+)', b)
    for n in nets:
        own[block_of(n)] += ov / max(len(nets), 1)
print(f'===== {lab}: entries {len(blocks)}  overflow in report {tot}  x covered {min(xs):.0f}-{max(xs):.0f}  H/V {dict(hv)}')
print('  by net owner:', ', '.join(f'{k} {100 * v / tot:.0f}%' for k, v in own.most_common(8)))
mx = max(grid.values())
for gy in range(25, -1, -1):
    print(f'{gy * 250:5d} |' + ''.join((' .:-=+*#%@'[min(9, int(9 * grid.get((gx, gy), 0) / mx))] if grid.get((gx, gy), 0) else ' ')
                                    for gx in range(27)) + '|')
print('      ' + ''.join(str((gx * 250) // 1000) if gx % 4 == 0 else ' ' for gx in range(27)) + '  (x in mm, 250 um bins)')
top = sorted(grid.items(), key=lambda kv: -kv[1])[:6]
print('  top bins:', [((gx * 250, gy * 250), v) for (gx, gy), v in top])
