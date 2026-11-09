#!/usr/bin/env python3
"""Cross-check padring JSON, portmap JSON and the chip-top ports of a (synthesized) Verilog netlist.
usage: check_portmap.py padring.json portmap.json netlist.v
Every non-supply pad must be mapped, every mapped port must exist, every chip port must be mapped
(once as c2p/p2c; c2p_en may fan out to several pads)."""
import json
import re
import sys
from collections import Counter

pr, pm, vf = sys.argv[1:4]
cfg = json.load(open(pr)); mp = json.load(open(pm))
top = mp['chip_top']
txt = open(vf).read()
m = re.search(r'^module\s+' + re.escape(top) + r'\s*\((.*?)\);', txt, re.S | re.M)
assert m, f'module {top} not found in {vf}'
ports = set()
for p in m.group(1).split(','):
    p = p.strip().lstrip('\\').strip()
    if p:
        ports.add(p)
# expand vector declarations (input [7:0] x;) if ports were declared as plain names
for d in re.finditer(r'^\s*(input|output|inout)\s+\[(\d+):(\d+)\]\s+(\w+)\s*;', txt[m.end():m.end() + 200000], re.M):
    hi, lo, n = int(d.group(2)), int(d.group(3)), d.group(4)
    if n in ports:
        ports.discard(n)
        ports |= {f'{n}[{i}]' for i in range(min(hi, lo), max(hi, lo) + 1)}
SUP = {'VDD', 'VSS', 'IOVDD', 'IOVSS'}
pads = {}
for side, lst in cfg['sides'].items():
    for name, cell in lst:
        if name not in SUP:
            pads[name] = cell
err = 0
used = Counter()
for name, cell in pads.items():
    if name not in mp['pads']:
        print(f'ERROR pad {name} ({cell}) has no portmap entry'); err += 1; continue
    pins = mp['pads'][name]
    need = {'IOPadIn': {'p2c'}, 'IOPadOut4mA': {'c2p'}, 'IOPadOut16mA': {'c2p'}, 'IOPadOut30mA': {'c2p'}}
    allowed = need.get(cell, {'c2p', 'c2p_en', 'p2c'})
    if not set(pins) <= allowed:
        print(f'ERROR pad {name} ({cell}): pins {sorted(pins)} not on this cell'); err += 1
    for pin, port in pins.items():
        if port not in ports:
            print(f'ERROR pad {name}.{pin} -> {port}: no such chip port'); err += 1
        if pin != 'c2p_en':
            used[port] += 1
        else:
            used[port] += 0
            used.setdefault(port, 0)
for p in mp['pads']:
    if p not in pads:
        print(f'ERROR portmap entry {p} is not a pad in {pr}'); err += 1
en_ports = {pt for v in mp['pads'].values() for k, pt in v.items() if k == 'c2p_en'}
for p in sorted(ports):
    if p in SUP:
        continue
    if used.get(p, 0) == 0 and p not in en_ports:
        print(f'ERROR chip port {p} not mapped to any pad'); err += 1
    if used.get(p, 0) > 1:
        print(f'ERROR chip port {p} mapped {used[p]} times'); err += 1
print(f'{len(pads)} signal pads, {len(ports)} chip ports, {err} error(s)')
sys.exit(1 if err else 0)
