#!/usr/bin/env python3
"""Intel HEX file to a $readmemh file with one byte per entry (address lines @hhhhhhhh), for hyperram_model.v.
Bytes at or above <mem bytes> are left out, as the VHDL model does.
usage: ihex2mem.py <in.hex> <out.mem> [mem bytes = 1048576]"""
import sys

src, dst = sys.argv[1], sys.argv[2]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 1048576
base = 0; data = {}
for l in open(src):
    l = l.strip()
    if not l.startswith(':'):
        continue
    b = bytes.fromhex(l[1:])
    n, addr, typ = b[0], (b[1] << 8) | b[2], b[3]
    if (sum(b) & 255) != 0:
        raise SystemExit(f'checksum error in {l}')
    if typ == 0:
        for i in range(n):
            a = base + addr + i
            if a < limit:
                data[a] = b[4 + i]
    elif typ == 1:
        break
    elif typ == 2:
        base = ((b[4] << 8) | b[5]) * 16
    elif typ == 4:
        base = ((b[4] << 8) | b[5]) * 65536
with open(dst, 'w') as o:
    prev = None
    for a in sorted(data):
        if prev is None or a != prev + 1:
            o.write(f'@{a:08x}\n')
        o.write(f'{data[a]:02x}\n'); prev = a
print(f'# ihex2mem: {len(data)} bytes, {min(data):#x} to {max(data):#x} -> {dst}')
