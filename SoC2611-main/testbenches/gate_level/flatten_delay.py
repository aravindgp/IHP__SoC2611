#!/usr/bin/env python3
"""The routed netlist as logic WITH its delays, for a simulation with real delays (13 November 2026).
Like flatten_netlist.py, every standard cell becomes one line of logic from the PDK timing library. Here the delays
of a delay file (SDF, written by the timing engine from the routed wires at one corner) are built in:
  cell delay   every output gets the rise and fall delay of its slowest input-to-output arc (max value of the SDF,
               conditional arcs left out), a flip-flop its clock-to-output delay, the clock gate its clock delay;
  wire delay   a pin whose wire delay is at least WMIN ps, and every pin on a clock net, gets its own delayed copy
               of the net, so clock skew is as in the layout; smaller wire delays are left out;
  SRAM macros  stay instances of the functional PDK model; each data output gets the clock-to-output delay of the
               delay file, and the clock pin its wire delay;
  pads         input and output pads become a delayed wire (the split pad pins of strip_netlist.py --split-pads).
Clock and reset pins stay on their real nets: the clock tree and the reset tree run with their delays.
Not modelled: setup and hold windows. A flip-flop takes what is on its input at the clock edge, so the simulation
shows whether the chip works at a clock period, and static timing analysis remains the check of the margins.
Every flip-flop starts at 0, as a simulation with unknown values would stop at the clock generator, whose
registers have no reset and find their rhythm from any start value.
usage: flatten_delay.py <netlist.v, pads split> <stdcell .lib> <chip.sdf> <out.v> [WMIN_PS=20]"""
import collections
import re
import sys

net_f, lib_f, sdf_f, out_f = sys.argv[1:5]
WMIN = float(sys.argv[5]) if len(sys.argv) > 5 else 20.0

# ------------------------------------------------------------------ library (as in flatten_netlist.py)
cells = {}
for c in re.split(r'\n\s*cell\s*\(\s*', open(lib_f).read())[1:]:
    name = c[:c.index(')')].strip().strip('"')
    pins = {}
    for p, body in re.findall(r'\n\s*pin\s*\(\s*"?(\w+)"?\s*\)\s*\{(.*?)(?=\n\s*pin\s*\(|\Z)', c, re.S):
        d = re.search(r'direction\s*:\s*"?(\w+)"?', body)
        f = re.search(r'function\s*:\s*"([^"]*)"', body)
        if d and p not in pins:
            pins[p] = (d.group(1), f.group(1) if f else None)
    ff = re.search(r'\n\s*ff\s*\(\s*"?(\w+)"?\s*,\s*"?(\w+)"?\s*\)\s*\{(.*?)\}', c, re.S)
    icg = re.search(r'clock_gating_integrated_cell\s*:\s*"?(\w+)', c)
    info = {'pins': pins, 'kind': 'comb'}
    if ff:
        info.update(kind='ff', iq=ff.group(1), iqn=ff.group(2), ff=dict(re.findall(r'(\w+)\s*:\s*"([^"]*)"', ff.group(3))))
    elif icg:
        info.update(kind='icg')
    cells[name] = info
TOK = re.compile(r"[A-Za-z_]\w*|[01]|[!*+^()]")


def expr(f, conn):
    out = []
    for t in TOK.findall(f):
        out.append(conn[t] if t in conn else f"1'b{t}" if t in '01' else {'!': '~', '*': '&', '+': '|'}.get(t, t))
    return ''.join(out)


# ------------------------------------------------------------------ the delay file
NUM = re.compile(r'\(\s*(-?[\d.]+)?\s*:\s*(-?[\d.]+)?\s*:\s*(-?[\d.]+)?\s*\)|\(\s*\)')


def vals(text):
    """max rise and fall, ps, of the value groups of one SDF entry; a missing fall takes the rise"""
    v = []
    for m in NUM.finditer(text):
        x = m.group(3) or m.group(2) or m.group(1)
        v.append(float(x) * 1000.0 if x else None)
    r = v[0] if v and v[0] is not None else (v[1] if len(v) > 1 and v[1] is not None else 0.0)
    f = v[1] if len(v) > 1 and v[1] is not None else r
    return r, f


def unesc(s):
    return s.replace('\\/', '/').replace('\\[', '[').replace('\\]', ']').replace('\\$', '$')


def split_pin(s):
    """'inst\\/sub/PIN' -> (instance, pin); the divider of the pin is the last '/' that is not escaped"""
    i = len(s)
    while True:
        i = s.rfind('/', 0, i)
        if i <= 0:
            return None, s
        if s[i - 1] != '\\':
            return unesc(s[:i]), s[i + 1:]


cell_d = collections.defaultdict(dict)      # instance -> output pin -> (rise, fall) ps, slowest arc
wire_d = {}                                 # (instance, pin) -> ps
inst = None; skip_cond = False
with open(sdf_f, errors='replace') as f:
    for l in f:
        s = l.strip()
        if s.startswith('(INTERCONNECT'):
            p = s.split(None, 3)
            si, sp = split_pin(p[2])
            if si is not None:
                r, fl = vals(p[3])
                wire_d[(si, sp)] = max(r, fl)
        elif s.startswith('(INSTANCE'):
            inst = unesc(s[len('(INSTANCE'):].rstrip(')').strip())
        elif s.startswith('(COND'):
            skip_cond = '(IOPATH' not in s
        elif s.startswith('(IOPATH'):
            if skip_cond:
                skip_cond = False; continue
            p = s.split(None, 3)
            frm = p[1]; out = p[2]
            if frm.startswith('('):          # (posedge CLK) Q ...
                p = s.split(None, 4); out = p[3]; rest = p[4]
            else:
                rest = p[3]
            r, fl = vals(rest)
            a = cell_d[inst].get(out, (0.0, 0.0))
            cell_d[inst][out] = (max(a[0], r), max(a[1], fl))
print(f'# flatten_delay: delay file: {len(cell_d)} instances with cell delays, {len(wire_d)} wire delays')

# ------------------------------------------------------------------ the netlist
INST = re.compile(r'^ ([A-Za-z_][A-Za-z0-9_]*) (\\\S+ |[A-Za-z_][A-Za-z0-9_$]*) ?\(')
CONN = re.compile(r'\.(\w+)\(\s*(\{[^}]*\}|\\\S+ ?|[^\s()]*)\s*\)')
NETS = re.compile(r"\\\S+ ?|\d+'[bhd][0-9a-fA-FxzXZ]+|[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])?")


def norm(n):
    n = n.strip()
    return n + ' ' if n.startswith('\\') else n


stmts = []
with open(net_f, errors='replace') as f:
    buf = None
    for l in f:
        if buf is None:
            m = INST.match(l)
            if not m or m.group(1) in ('wire', 'input', 'output', 'inout', 'module'):
                stmts.append(('raw', l)); continue
            buf = [l]
        else:
            buf.append(l)
        if l.rstrip().endswith(');'):
            text = ''.join(buf); buf = None
            m = INST.match(text)
            conn = {p: [norm(x) for x in NETS.findall(n)] for p, n in CONN.findall(text[m.end() - 1:])}
            stmts.append(('inst', m.group(1), m.group(2).strip().lstrip('\\'), conn, text))

# clock nets: every net that reaches a clock pin (flip-flop, clock gate, macro) through buffers and inverters
reads = collections.defaultdict(list)
for s in stmts:
    if s[0] != 'inst':
        continue
    _, cell, iname, conn, text = s
    info = cells.get(cell)
    for p, ns in conn.items():
        isout = (info and info['pins'].get(p, ('', None))[0] == 'output') or (not info and (p.endswith('DOUT') or p in ('p2c', 'pad_o', 'pad_oe') or (p == 'pad' and 'Out' in cell)))
        if not isout:
            for n in ns:
                reads[n].append((cell, iname, p))
clock = set(); todo = []
for s in stmts:
    if s[0] != 'inst':
        continue
    _, cell, iname, conn, text = s
    info = cells.get(cell)
    if info and info['kind'] == 'ff':
        todo.append(conn[info['ff']['clocked_on'].strip()][0])
    elif info and info['kind'] == 'icg':
        todo.append(conn['CLK'][0])
    elif not info:
        for p, ns in conn.items():
            if p.endswith('_CLK'):
                todo += ns
drv = {}
for s in stmts:
    if s[0] == 'inst' and s[1] in cells:
        for p, (d, fn) in cells[s[1]]['pins'].items():
            if d == 'output' and s[3].get(p):
                drv[s[3][p][0]] = s
while todo:
    n = todo.pop()
    if n in clock:
        continue
    clock.add(n)
    d = drv.get(n)
    if d and cells[d[1]]['kind'] == 'comb' and len(cells[d[1]]['pins']) == 2:
        todo.append(d[3]['A'][0])
    elif d and cells[d[1]]['kind'] == 'icg':
        todo.append(d[3]['CLK'][0])

out = open(out_f, 'w')
out.write('// written by flatten_delay.py: standard cells as logic with the cell and wire delays of the delay file, ps\n`timescale 1ps/1ps\n')
cnt = collections.Counter(); seq = [0]


def pin_net(iname, pin, net):
    """the net as this pin sees it: a delayed copy when the wire delay counts"""
    d = wire_d.get((iname, pin), 0.0)
    if d >= WMIN or (net in clock and d >= 1.0):
        seq[0] += 1; w = f'\\W{seq[0]}__{pin} '
        out.write(f' wire #({d:.0f}) {w}= {net};\n'); cnt['wires'] += 1
        return w
    return net


def dly(iname, pin):
    r, f = cell_d.get(iname, {}).get(pin, (0.0, 0.0))
    return f'#({r:.0f},{f:.0f}) ' if (r or f) else ''


for s in stmts:
    if s[0] == 'raw':
        out.write(s[1]); continue
    _, cell, iname, conn, text = s
    info = cells.get(cell)
    if info is None:
        if 'IOPad' in cell:
            cnt['pads'] += 1
            c = {p: ns[0] for p, ns in conn.items() if ns}
            if 'InOut' in cell:
                out.write(f' assign {dly(iname, "pad")}{c["pad_o"]} = {pin_net(iname, "c2p", c["c2p"])};\n')
                out.write(f' assign {c["pad_oe"]} = {c["c2p_en"]};\n')
                if 'p2c' in c:
                    out.write(f' assign {dly(iname, "p2c")}{c["p2c"]} = {c["c2p_en"]} ? {c["c2p"]} : {c["pad_i"]};\n')
            elif 'Out' in cell:
                out.write(f' assign {dly(iname, "pad")}{c["pad"]} = {pin_net(iname, "c2p", c["c2p"])};\n')
            else:
                out.write(f' assign {dly(iname, "p2c")}{c["p2c"]} = {c["pad"]};\n')
            continue
        # a macro: clock pins through their wire delay, data outputs through the clock-to-output delay
        cnt['macros'] += 1; t = text; pre = []; post = []
        for p, ns in conn.items():
            if p.endswith('_CLK') and len(ns) == 1:
                w = pin_net(iname, p, ns[0])
                if w != ns[0]:
                    t = re.sub(r'\.' + p + r'\(\s*' + re.escape(ns[0].strip()) + r'\s*\)', lambda m: f'.{p}({w})', t, count=1)
            elif p.endswith('DOUT'):
                raws = []
                for i, n in enumerate(ns):
                    seq[0] += 1; rw = f'\\R{seq[0]}__{p} '
                    raws.append(rw)
                    bit = len(ns) - 1 - i
                    r, f = cell_d.get(iname, {}).get(f'{p}[{bit}]', cell_d.get(iname, {}).get(p, (0.0, 0.0)))
                    pre.append(f' wire {rw};\n'); post.append(f' assign #({r:.0f},{f:.0f}) {n}= {rw};\n')
                t = re.sub(r'\.' + p + r'\(\s*(\{[^}]*\}|\\\S+ ?|[^\s()]*)\s*\)', lambda m: f'.{p}({{{", ".join(raws)}}})', t, count=1)
        out.write(''.join(pre) + t + ''.join(post))
        continue
    cnt[info['kind']] += 1
    c = {}
    for p, (d, fn) in info['pins'].items():
        if conn.get(p):
            c[p] = pin_net(iname, p, conn[p][0]) if d == 'input' else conn[p][0]
    # Flip-flops and latches are instances of the three small modules at the end of the file, not always blocks
    # in the chip module: Icarus looks up every signal of a process by a linear search over the names of its scope
    # (dll_target::find_signal), which takes hours with 73,000 processes in a scope of 400,000 signals.
    if info['kind'] == 'ff':
        g = info['ff']; r = f'\\{iname}__IQ '
        ck = c[g['clocked_on'].strip()]
        ns = expr(g['next_state'], c)
        if not re.fullmatch(r'\s*(\\\S+ |[A-Za-z_][\w$]*)\s*', ns):
            nsw = f'\\{iname}__NS '
            out.write(f' wire {nsw}= {ns};\n'); ns = nsw
        if 'clear' in g:
            rs = c[re.fullmatch(r'\s*!\s*(\w+)\s*', g['clear']).group(1)]
            out.write(f' wire {r};\n FD_FF_R \\{iname}__FF (.Q({r}), .CK({ck}), .D({ns}), .RN({rs}));\n')
        else:
            out.write(f' wire {r};\n FD_FF_N \\{iname}__FF (.Q({r}), .CK({ck}), .D({ns}));\n')
        cc = dict(c); cc[info['iq']] = r; cc[info['iqn']] = '~' + r
        for p, (d, fn) in info['pins'].items():
            if d == 'output' and conn.get(p):
                out.write(f' assign {dly(iname, p)}{conn[p][0]} = {expr(fn, cc)};\n')
    elif info['kind'] == 'icg':
        r = f'\\{iname}__LATCH '
        out.write(f' wire {r};\n FD_LAT_L \\{iname}__LT (.Q({r}), .CK({c["CLK"]}), .G({c["GATE"]}));\n')
        out.write(f' assign {dly(iname, "GCLK")}{conn["GCLK"][0]} = {c["CLK"]} & {r};\n')
    else:
        for p, (d, fn) in info['pins'].items():
            if d == 'output' and conn.get(p):
                out.write(f' assign {dly(iname, p)}{conn[p][0]} = {expr(fn, c)};\n')
out.write('''
// the storage elements: flip-flop with clear (active low), flip-flop without, latch that is open while CK is low
module FD_FF_R (output reg Q, input CK, input D, input RN);
 initial Q = 1'b0;
 always @(posedge CK or negedge RN) if (!RN) Q <= 1'b0; else Q <= D;
endmodule
module FD_FF_N (output reg Q, input CK, input D);
 initial Q = 1'b0;
 always @(posedge CK) Q <= D;
endmodule
module FD_LAT_L (output reg Q, input CK, input G);
 initial Q = 1'b0;
 always @(CK or G) if (!CK) Q <= G;
endmodule
''')
out.close()
print(f'# flatten_delay: {dict(cnt)}; clock nets {len(clock)}; written to {out_f}')
