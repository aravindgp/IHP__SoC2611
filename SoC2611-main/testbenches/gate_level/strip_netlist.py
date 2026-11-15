#!/usr/bin/env python3
"""Copy of a routed netlist for simulation (13 November 2026).
1. Instances without logic are left out: row filler cells, antenna diodes, bond pads, pad-ring fillers, corners and
   supply pads. Of the 1.44 million instances of the chip 1.08 million are such cells.
2. With --split-pads the pad pins lose their tri-state: an input pad pin becomes an input port, an output pad pin
   an output port, and a bidirectional pad pin NAME becomes three ports NAME_i (from the board), NAME_o and NAME_oe
   (what the chip drives and when). The pad instances stay, with the pin .pad of a bidirectional pad connected as
   .pad_i/.pad_o/.pad_oe; pads_split.v holds the matching pad models. Reason: the simulator's tri-state analysis
   of a flat module with 350,000 instances takes most of its run time, and ten pads are all that needs it.
Every other line is copied unchanged, so the logic is exactly that of the released netlist.
usage: strip_netlist.py [--split-pads] <chip.v> <out.v>"""
import collections
import re
import sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
split = '--split-pads' in sys.argv
src, dst = args[0], args[1]
DROP = re.compile(r'^ (sg13cmos5l_fill_\d+|sg13cmos5l_decap_\d+|sg13cmos5l_antennanp|bondpad_\w+|sg13cmos5l_Filler\d+|'
                  r'sg13cmos5l_Corner|sg13cmos5l_IOPad(?:IO)?V(?:dd|ss)) ')
INST = re.compile(r'^ ([A-Za-z_][A-Za-z0-9_]*) (\\\S+ |[A-Za-z_][A-Za-z0-9_$]*) ?\(')
PADCELL = re.compile(r'^ sg13cmos5l_IOPad(In|Out\d+mA|InOut\d+mA|TriOut\d+mA) ')
PADPIN = re.compile(r'\.pad\(\s*([A-Za-z_][A-Za-z0-9_$]*)\s*\)')

# pass 1: direction of every pad pin, from the pad cell that is connected to it
kind = {}
if split:
    cur = None
    for l in open(src, errors='replace'):
        m = PADCELL.match(l)
        if m:
            cur = 'in' if m.group(1) == 'In' else ('out' if m.group(1).startswith('Out') else 'inout')
        if cur:
            p = PADPIN.search(l)
            if p:
                kind[p.group(1)] = cur
            if l.rstrip().endswith(');'):
                cur = None
    if not kind:
        raise SystemExit('no pad instances found')

kept = collections.Counter(); dropped = collections.Counter()
with open(src, errors='replace') as f, open(dst, 'w') as o:
    skip = False; header = True; pad_inst = None
    for l in f:
        if skip:
            if l.rstrip().endswith(');'):
                skip = False
            continue
        m = DROP.match(l)
        if m:
            dropped[m.group(1)] += 1
            if not l.rstrip().endswith(');'):
                skip = True
            continue
        if split:
            if header:
                # the port list of the module: lines up to the first ');'
                def ports(mm):
                    n = mm.group(0)
                    return f'{n}_i, {n}_o, {n}_oe' if kind.get(n) == 'inout' else n
                l2 = re.sub(r'[A-Za-z_][A-Za-z0-9_$]*', lambda mm: ports(mm) if mm.group(0) in kind else mm.group(0), l)
                if l.rstrip().endswith(');'):
                    header = False
                l = l2
            else:
                d = re.match(r'^ inout ([A-Za-z_][A-Za-z0-9_$]*);', l)
                if d and d.group(1) in kind:
                    n = d.group(1); k = kind[n]
                    l = (f' input {n};\n' if k == 'in' else f' output {n};\n' if k == 'out'
                         else f' input {n}_i;\n output {n}_o;\n output {n}_oe;\n')
                mp = PADCELL.match(l)
                if mp:
                    pad_inst = 'inout' if mp.group(1).startswith(('InOut', 'TriOut')) else 'plain'
                if pad_inst == 'inout':
                    l = PADPIN.sub(lambda mm: f'.pad_i({mm.group(1)}_i), .pad_o({mm.group(1)}_o), .pad_oe({mm.group(1)}_oe)', l)
                if pad_inst and l.rstrip().endswith(');'):
                    pad_inst = None
        m = INST.match(l)
        if m and m.group(1) not in ('wire', 'input', 'output', 'inout', 'module'):
            kept[m.group(1)] += 1
        o.write(l)
print(f'# strip_netlist: kept {sum(kept.values())} instances of {len(kept)} cell types, dropped {sum(dropped.values())}: '
      f'{dict(dropped)}')
if split:
    c = collections.Counter(kind.values())
    print(f'# strip_netlist: pad pins: {dict(c)}; bidirectional: {sorted(n for n, k in kind.items() if k == "inout")}')
