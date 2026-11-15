#!/usr/bin/env python3
"""Input pins without a driver in a flat netlist, and what they reach (13 November 2026).
Reads every instance statement, takes the pin directions of the standard cells from the PDK timing library, and
reports (1) input pins of standard cells that are not connected at all, (2) nets that are read by a pin but driven
by nothing (no cell output, no macro or pad pin, no port), and for each such start the pins it reaches through
buffers, delay cells and inverters: these are the places where an undefined level enters real logic.
Macro and pad pins count as possible drivers when their name is a known output (DOUT, p2c, pad) and as readers
otherwise.
usage: netlist_floating.py <netlist.v> <stdcell .lib> [net to trace ...]"""
import collections
import re
import sys

net_f, lib_f = sys.argv[1:3]
extra = sys.argv[3:]
pins = {}
for c in re.split(r'\n\s*cell\s*\(\s*', open(lib_f).read())[1:]:
    name = c[:c.index(')')].strip().strip('"')
    d = {}
    for p, body in re.findall(r'\n\s*pin\s*\(\s*"?(\w+)"?\s*\)\s*\{(.*?)(?=\n\s*pin\s*\(|\Z)', c, re.S):
        m = re.search(r'direction\s*:\s*"?(\w+)"?', body); f = re.search(r'function\s*:\s*"([^"]*)"', body)
        if m and p not in d:
            d[p] = (m.group(1), f.group(1) if f else None)
    pins[name] = d
THROUGH = {n for n, d in pins.items() if len(d) == 2 and [f for dr, f in d.values() if dr == 'output'] in (['A'], ['!A'])}
INST = re.compile(r'^ ([A-Za-z_][A-Za-z0-9_]*) (\\\S+ |[A-Za-z_][A-Za-z0-9_$]*) ?\(')
CONN = re.compile(r'\.(\w+)\(\s*(\{[^}]*\}|\\\S+|[^\s()]*)\s*\)')
MACRO_OUT = re.compile(r'DOUT$|^p2c$|^pad$|^pad_o$|^pad_oe$')
NETS = re.compile(r'\\\S+|[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])?')

drivers = collections.defaultdict(list); readers = collections.defaultdict(list); unconnected = []; ports = set()
with open(net_f, errors='replace') as f:
    buf = None
    for l in f:
        m = re.match(r'^ (input|output|inout) (?:\[[^\]]*\] )?(\S+?);', l)
        if m:
            ports.add(m.group(2))
        if buf is None:
            m = INST.match(l)
            if not m or m.group(1) in ('wire', 'input', 'output', 'inout', 'module'):
                continue
            buf = [l]
        else:
            buf.append(l)
        if not l.rstrip().endswith(');'):
            continue
        text = ''.join(buf); buf = None
        m = INST.match(text); cell, inst = m.group(1), m.group(2).strip()
        conn = {p: n for p, n in CONN.findall(text[m.end():])}
        if cell in pins:
            for p, (d, fn) in pins[cell].items():
                n = conn.get(p, '')
                if d == 'input':
                    if not n:
                        unconnected.append((cell, inst, p))
                    else:
                        readers[n].append((cell, inst, p))
                elif d == 'output' and n:
                    drivers[n].append((cell, inst, p))
        else:
            for p, n in conn.items():
                for one in NETS.findall(n):
                    (drivers if MACRO_OUT.search(p) else readers)[one].append((cell, inst, p))
out_of = {}
for n, ds in drivers.items():
    for cell, inst, p in ds:
        out_of[inst] = n


def reach(net):
    """pins reached from a net through buffers, delay cells and inverters"""
    seen = set(); todo = [net]; leaves = collections.Counter(); ex = {}; through = 0
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        for cell, inst, p in readers.get(n, []):
            if cell in THROUGH:
                through += 1
                if inst in out_of:
                    todo.append(out_of[inst])
            else:
                k = (cell.replace('sg13cmos5l_', ''), p)
                leaves[k] += 1; ex.setdefault(k, inst)
    return through, leaves, ex


print(f'# netlist_floating: {sum(len(v) for v in readers.values())} read pins on {len(readers)} nets, {len(drivers)} driven nets')
print(f'# input pins of standard cells without any connection: {len(unconnected)}')
starts = []
for cell, inst, p in unconnected:
    print(f'  {cell.replace("sg13cmos5l_", "")} {inst} pin {p}; its output net: {out_of.get(inst, "-")}')
    if inst in out_of:
        starts.append(out_of[inst])
undriven = [n for n in readers if n not in drivers and n.split('[')[0] not in ports and not re.match(r"\d+'", n)]
print(f'# nets that are read but driven by nothing: {len(undriven)}')
for n in undriven[:40]:
    r = readers[n]
    print(f'  {n.strip()}: {len(r)} pins, for example {r[0][0].replace("sg13cmos5l_", "")} {r[0][1][-60:]} pin {r[0][2]}')
for n in starts + undriven[:10] + extra:
    through, leaves, ex = reach(n)
    print(f'# from {n.strip()}: through {through} buffers to {sum(leaves.values())} pins:')
    for (cell, p), c in leaves.most_common(30):
        print(f'    {c:5d}  {cell} pin {p}   for example {ex[(cell, p)][-90:]}')
