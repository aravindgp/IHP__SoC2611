#!/usr/bin/env python3
"""The routed netlist with every standard cell written out as one line of logic (13 November 2026).
A simulator has to resolve 347,000 cell instances of a flat netlist one by one, and that took longer than the
simulation itself. Here each cell instance becomes what the PDK timing library says the cell does:
  a logic cell   ->  assign <output net> = <function of the input nets>;
  a flip-flop    ->  a register with a non-blocking assignment on its clock edge and its asynchronous reset
  the clock gate ->  a latch that is open while the clock is low, and an AND gate
SRAM macros and pads stay instances. Net names are those of the netlist.
Clock and reset pins: in a simulation without delays a chain of buffers is transparent, so the clock pin of a
flip-flop (and of an SRAM, and of a clock gate) and its reset pin are connected to the START of their buffer
tree: the tool follows buffers, delay cells and inverters back to the first net that is driven by something else
(a pad, a clock gate, a flip-flop, a tie cell, a logic gate). An odd number of inverters turns the edge around.
The simulator then sees a handful of clocks instead of thousands of clock-tree nets. The census of these sources
is printed and written to <out>.clocks.txt: every flip-flop must hang on one of the expected clock sources.
usage: flatten_netlist.py <netlist.v, pads split> <stdcell .lib> <out.v>"""
import collections
import re
import sys

net_f, lib_f, out_f = sys.argv[1:4]

# ------------------------------------------------------------------ the cells of the library
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
        g = dict(re.findall(r'(\w+)\s*:\s*"([^"]*)"', ff.group(3)))
        info.update(kind='ff', iq=ff.group(1), iqn=ff.group(2), ff=g)
    elif icg:
        info.update(kind='icg', icg=icg.group(1))
    cells[name] = info
BUF = {n for n, i in cells.items() if i['kind'] == 'comb' and
       [f for d, f in i['pins'].values() if d == 'output'] in (['A'],) and len(i['pins']) == 2}
INV = {n for n, i in cells.items() if i['kind'] == 'comb' and
       [f for d, f in i['pins'].values() if d == 'output'] in (['!A'], ['!(A)'], ["A'"]) and len(i['pins']) == 2}

TOK = re.compile(r"[A-Za-z_]\w*|[01]|[!*+^()']")


def expr(f, conn):
    """liberty function with the pins replaced by the nets of one instance"""
    out = []
    for t in TOK.findall(f):
        if t in conn:
            out.append(conn[t])
        elif t in ('0', '1'):
            out.append(f"1'b{t}")
        elif t == '!':
            out.append('~')
        elif t == '*':
            out.append('&')
        elif t == '+':
            out.append('|')
        elif t == "'":
            raise SystemExit(f'postfix inversion in a function is not handled: {f}')
        elif t in '^()':
            out.append(t)
        else:
            raise SystemExit(f'unknown name {t} in function {f}; connections {conn}')
    return ''.join(out)


# ------------------------------------------------------------------ the netlist: statements
INST = re.compile(r'^ ([A-Za-z_][A-Za-z0-9_]*) (\\\S+ |[A-Za-z_][A-Za-z0-9_$]*) ?\(')


def connections(text):
    """.PIN(net) pairs of one instance statement; an escaped identifier keeps its closing blank"""
    conn = {}; i = text.index('(') + 1
    while True:
        j = text.find('.', i)
        if j < 0:
            break
        k = text.index('(', j)
        pin = text[j + 1:k].strip(); k += 1
        while text[k] in ' \n\t':
            k += 1
        if text[k] == '\\':
            e = k
            while text[e] not in ' \n\t':
                e += 1
            net = text[k:e] + ' '
            e = text.index(')', e)
        else:
            e = text.index(')', k)
            net = text[k:e].strip()
        conn[pin] = net
        i = e + 1
    return conn


stmts = []          # ('raw', text) | ('cell', cellname, instname, conn)
with open(net_f, errors='replace') as f:
    buf = None
    for l in f:
        if buf is not None:
            buf.append(l)
            if l.rstrip().endswith(');'):
                text = ''.join(buf); m = INST.match(text)
                stmts.append(('cell', m.group(1), m.group(2).strip(), connections(text)) if m.group(1) in cells
                             else ('raw', text))
                buf = None
            continue
        m = INST.match(l)
        if m and m.group(1) not in ('wire', 'input', 'output', 'inout', 'module'):
            if l.rstrip().endswith(');'):
                stmts.append(('cell', m.group(1), m.group(2).strip(), connections(l)) if m.group(1) in cells
                             else ('raw', l))
            else:
                buf = [l]
        else:
            stmts.append(('raw', l))

# ------------------------------------------------------------------ who drives a net; start of a buffer tree
driver = {}
for s in stmts:
    if s[0] == 'cell':
        _, cell, inst, conn = s
        for p, (d, fn) in cells[cell]['pins'].items():
            if d == 'output' and conn.get(p):
                driver[conn[p]] = (cell, inst, conn)
root_cache = {}


def root(net):
    """(first net of the buffer tree, True if an odd number of inverters lies between)"""
    path = []; inv = False; n = net
    while True:
        if n in root_cache:
            r, i = root_cache[n]; res = (r, inv ^ i); break
        d = driver.get(n)
        if d is None or (d[0] not in BUF and d[0] not in INV):
            res = (n, inv); break
        path.append((n, inv))
        if d[0] in INV:
            inv = not inv
        n = d[2]['A']
    for pn, pi in path:
        root_cache[pn] = (res[0], res[1] ^ pi)
    return res


def what(net):
    d = driver.get(net)
    return d[0].replace('sg13cmos5l_', '') if d else 'pad or macro'


def reg_name(inst, suffix):
    return '\\' + inst.lstrip('\\') + suffix + ' '


census = collections.Counter(); rst_census = collections.Counter(); n = collections.Counter()
out = open(out_f, 'w')
out.write('// written by flatten_netlist.py: standard cells as logic, clock and reset pins at the start of their buffer tree\n')
for s in stmts:
    if s[0] == 'raw':
        t = s[1]
        if '_CLK(' in t:                     # clock pins of the SRAM macros
            def fix(m):
                r, inv = root(m.group(2).strip() + (' ' if m.group(2).startswith('\\') else ''))
                if inv:
                    raise SystemExit(f'inverted clock at a macro pin: {m.group(0)}')
                census[('macro ' + m.group(1), r.strip(), what(r))] += 1
                return f'.{m.group(1)}({r})'
            t = re.sub(r'\.(\w*_CLK)\(\s*(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\)', fix, t)
        out.write(t)
        continue
    _, cell, inst, conn = s
    info = cells[cell]; n[info['kind']] += 1
    if info['kind'] == 'ff':
        g = info['ff']
        ck, ck_inv = root(conn[g['clocked_on'].strip()])
        census[('flip-flop', ck.strip(), what(ck) + (' (inverted)' if ck_inv else ''))] += 1
        r = reg_name(inst, '__IQ')
        c = dict(conn); c[info['iq']] = r; c[info['iqn']] = '~' + r
        sens = [('negedge ' if ck_inv else 'posedge ') + ck]; body = f'{r}<= {expr(g["next_state"], conn)};'
        level = ''
        for key, val in (('clear', "1'b0"), ('preset', "1'b1")):
            if key in g:
                m = re.fullmatch(r'\s*!\s*(\w+)\s*', g[key])
                if not m:
                    raise SystemExit(f'{cell}: {key} = {g[key]} not handled')
                rs, rs_inv = root(conn[m.group(1)])
                rst_census[(rs.strip(), what(rs) + (' (inverted)' if rs_inv else ''))] += 1
                if what(rs) == 'tiehi' and not rs_inv:
                    continue                 # reset pin tied off: a flip-flop without reset
                sens.append(('posedge ' if rs_inv else 'negedge ') + rs)
                body = f'if ({"" if rs_inv else "!"}{rs}) {r}<= {val}; else ' + body
                # The real cell is cleared as long as its reset pin is low; the always block acts on the falling
                # edge only. A reset that is low from the start has no edge, so a flip-flop whose clock does not
                # run during the reset would keep its start value: this line clears it once at the start.
                level += f' initial #1 if ({"" if rs_inv else "!"}{rs}) {r}= {val};\n'
        out.write(f' reg {r};\n always @({" or ".join(sens)}) {body}\n' + level)
        for p, (d, fn) in info['pins'].items():
            if d == 'output' and conn.get(p):
                out.write(f' assign {conn[p]} = {expr(fn, c)};\n')
    elif info['kind'] == 'icg':
        if info['icg'] != 'latch_posedge':
            raise SystemExit(f'{cell}: clock gate type {info["icg"]} not handled')
        ck, ck_inv = root(conn['CLK'])
        if ck_inv:
            raise SystemExit(f'inverted clock at clock gate {inst}')
        census[('clock gate', ck.strip(), what(ck))] += 1
        r = reg_name(inst, '__LATCH')
        out.write(f' reg {r};\n always @({ck} or {conn["GATE"]}) if (!{ck}) {r}<= {conn["GATE"]};\n')
        out.write(f' assign {conn["GCLK"]} = {ck} & {r};\n')
    else:
        for p, (d, fn) in info['pins'].items():
            if d == 'output' and conn.get(p):
                out.write(f' assign {conn[p]} = {expr(fn, conn)};\n')
out.close()
with open(out_f + '.clocks.txt', 'w') as o:
    o.write('# clock source of every clocked pin (start of its buffer tree): kind, source net, driven by, pins\n')
    for (k, r, w), c in sorted(census.items(), key=lambda kv: (kv[0][0], -kv[1])):
        o.write(f'{k:<18} {r:<60} {w:<22} {c}\n')
    o.write('# reset source of the reset pins of the flip-flops: source net, driven by, pins\n')
    for (r, w), c in sorted(rst_census.items(), key=lambda kv: -kv[1]):
        o.write(f'{r:<60} {w:<22} {c}\n')
print(f'# flatten_netlist: {dict(n)} written to {out_f}')
print(f'# clock sources: {len(census)}; reset sources: {len(rst_census)} (see {out_f}.clocks.txt)')
