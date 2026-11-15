#!/usr/bin/env python3
"""Expected result of the camera capture test (HW/asic/fw/capture.c), calculated without the chip (13 Nov 2026).
The testbench drives rows of W pixels, two bytes per pixel: byte number cx of row cy is (cy*7 + cx*3 + 1) & 255,
the same in every frame. The camera block (HW/src/soc/peripherals/camera.vhd) makes of the two bytes of a pixel,
d = first<<8 | second, three bytes: (d>>6 & 15)<<4, (d>>1 & 15)<<4, (d>>11 & 15)<<4, in this order in the memory.
Four pixels become three 32-bit words, two words one 64-bit entry of the stream writer, which writes bursts of
256 bytes into the external memory. The firmware sums the first BURSTS bursts as little-endian words:
sum = rotl(sum, 1) ^ word.
usage: cam_expect.py [W=640] [H=4] [BURSTS=28]      prints the expected sum and the first word as 0x........"""
import sys

W = int(sys.argv[1]) if len(sys.argv) > 1 else 640
H = int(sys.argv[2]) if len(sys.argv) > 2 else 4
BURSTS = int(sys.argv[3]) if len(sys.argv) > 3 else 28
need = BURSTS * 256
mem = bytearray()
while len(mem) < need:
    for cy in range(H):
        for px in range(W):
            hi = (cy * 7 + (2 * px) * 3 + 1) & 255
            lo = (cy * 7 + (2 * px + 1) * 3 + 1) & 255
            d = (hi << 8) | lo
            mem += bytes([((d >> 6) & 15) << 4, ((d >> 1) & 15) << 4, ((d >> 11) & 15) << 4])
s = 0
for i in range(0, need, 4):
    w = int.from_bytes(mem[i:i + 4], 'little')
    s = (((s << 1) | (s >> 31)) & 0xFFFFFFFF) ^ w
print(f'0x{s:08x} 0x{int.from_bytes(mem[0:4], "little"):08x}')
