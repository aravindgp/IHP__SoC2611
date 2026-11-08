#!/usr/bin/env python3
"""Side-move plan for the nets that cross a macro: for each (net, macro) pair, split the net's pins into those north
and south of the macro's y-span; the minority side's cells are to be moved just across the macro (same x, y = the
macro edge on the majority side + CLEAR um).  Macro pins (instances that are blocks) and port pins never move; a net
whose minority side contains a macro or port is reported as unmovable.
usage: pins_side.py <nets_pins.log> <pairs.txt> <macros.txt> <place.pl> [clear_um=12] [blockages.txt] > moves.txt
blockages.txt: the probe's placement blockages ("x0 y0 x1 y1" rects joined by ';'); a target that falls inside one
(the pockets next to the macros are blocked) is pushed past the blockage's far edge.
output lines: MOVE <inst> <x_um> <y_um>   # net, macro, from side   and a summary on stderr"""
import collections
import sys

log, pairs, mac, pl = sys.argv[1:5]
clear = float(sys.argv[5]) if len(sys.argv) > 5 else 12.0
blks = []
if len(sys.argv) > 6:
    for r in open(sys.argv[6]).read().replace(';', '\n').split('\n'):
        if len(r.split()) == 4:
            blks.append(tuple(float(v) for v in r.split()))


def past_blockages(x, y, up):
    """move y past every blockage rect containing (x, y), in the direction 'up' (True = north)"""
    for _ in range(20):
        hit = [b for b in blks if b[0] <= x <= b[2] and b[1] - 4 <= y <= b[3] + 4]
        if not hit:
            return y
        y = (max(b[3] for b in hit) + clear) if up else (min(b[1] for b in hit) - clear)
    return None
S = {l.split()[0]: (float(l.split()[2]), float(l.split()[3])) for l in open(mac) if len(l.split()) == 4}
P = {}
for l in open(pl):
    p = l.split()
    if len(p) == 4 and p[0] in S:
        P[p[0]] = (float(p[1]), float(p[2]), float(p[1]) + S[p[0]][0], float(p[2]) + S[p[0]][1])
# macro outlines (+10 um halo) are blocked space for the push as well: a target pushed past a pocket must not land in
# the next macro row
blks += [(x0 - 10, y0 - 10, x1 + 10, y1 + 10) for (x0, y0, x1, y1) in P.values()]
pins = collections.defaultdict(list)
for l in open(log):
    p = l.split()
    if p and p[0] == 'PIN':
        pins[p[1]].append((p[2], float(p[3]), float(p[4]), p[5]))
macro_of = {}
for l in open(pairs):
    p = l.split()
    if len(p) == 3:
        macro_of.setdefault(p[1], p[2])
moves = {}
stats = collections.Counter()
for net, m in macro_of.items():
    if net not in pins or m not in P:
        stats['no data'] += 1
        continue
    x0, y0, x1, y1 = P[m]
    north = [t for t in pins[net] if t[2] >= y1]
    south = [t for t in pins[net] if t[2] <= y0]
    inside = [t for t in pins[net] if y0 < t[2] < y1]
    if not north or not south:
        stats['one side only (pin access / sideways)'] += 1
        continue
    minority, target_y, side = (north, y0 - clear, 'north') if len(north) < len(south) else (south, y1 + clear, 'south')
    if any(t[0] == 'PORT' or t[3].startswith('RM_IHPSG13') for t in minority):
        stats['unmovable (macro/port on the minority side)'] += 1
        continue
    if len(minority) > 6:
        stats['minority > 6 cells'] += 1
        continue
    for inst, x, y, master in minority:
        tx = min(max(x, x0), x1)
        ty = past_blockages(tx, target_y, side == 'south')
        if ty is None or abs(ty - target_y) > 250:
            # fallback: the vertical channel beside the macro (just outside its x-span, nearest side), at the
            # majority-side y next to the macro edge
            for cx in sorted((x0 - 25, x1 + 25), key=lambda v: abs(v - x)):
                cy = past_blockages(cx, target_y, side == 'south')
                if cy is not None and abs(cy - target_y) <= 60:
                    tx, ty = cx, cy
                    stats['channel fallback'] += 1
                    break
            else:
                stats['no free target within 250 um'] += 1
                continue
        if inst in moves and abs(moves[inst][1] - ty) > 1:
            stats['conflict'] += 1
            continue
        moves[inst] = (tx, ty, net, m, side)
    stats['planned'] += 1
for inst, (x, y, net, m, side) in sorted(moves.items(), key=lambda t: t[1][1]):
    print(f'MOVE {inst} {x:.2f} {y:.2f}   # {net.replace("soc_i/", "")[-50:]} across {m.split("/")[-2][-26:]} from {side}')
print(f'# nets {len(macro_of)}: {dict(stats)}; {len(moves)} cells to move', file=sys.stderr)
