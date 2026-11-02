#!/usr/bin/env python3
"""Summarize a KLayout .lvsdb: per-circuit match status and the first mismatching nets/devices/pins.
usage: lvsdb_report.py file.lvsdb [max_items]"""
import sys
import klayout.db as db

path = sys.argv[1]
nmax = int(sys.argv[2]) if len(sys.argv) > 2 else 15
lvs = db.LayoutVsSchematic()
lvs.read(path)
xref = lvs.xref()
S = db.NetlistCrossReference
bad = 0
for cp in xref.each_circuit_pair():
    st = cp.status()
    a, b = cp.first(), cp.second()
    name = (a or b).name
    if st in (S.Match, S.MatchWithWarning):
        continue
    bad += 1
    print(f'CIRCUIT {name}: {st}  (layout={"yes" if a else "MISSING"}, schematic={"yes" if b else "MISSING"})')
    n = 0
    for kind, it in (('pin', xref.each_pin_pair(cp)), ('net', xref.each_net_pair(cp)),
                     ('device', xref.each_device_pair(cp)), ('subckt', xref.each_subcircuit_pair(cp))):
        for p in it:
            if p.status() in (S.Match, S.MatchWithWarning):
                continue
            f, s = p.first(), p.second()
            def nm(o):
                if o is None:
                    return '-'
                return getattr(o, 'expanded_name', lambda: str(o))() if hasattr(o, 'expanded_name') else str(o)
            print(f'   {kind:7s} {str(p.status()):12s} layout={nm(f)}  schematic={nm(s)}')
            n += 1
            if n >= nmax:
                break
        if n >= nmax:
            print('   ...')
            break
print(f'{bad} non-matching circuit(s)')

# top-level port check (what the deck's flag_missing_ports looks at)
lt = lvs.netlist().top_circuit()
st = lvs.reference.top_circuit()
if lt and st:
    lp = {p.name() for p in lt.each_pin() if p.name()}
    sp = {p.name() for p in st.each_pin() if p.name()}
    print(f'top {lt.name}: layout pins {len(lp)}, schematic pins {len(sp)}')
    if sp - lp:
        print('  schematic-only pins (unlabeled/missing in layout):', sorted(sp - lp)[:30])
    if lp - sp:
        print('  layout-only pins:', sorted(lp - sp)[:30])
