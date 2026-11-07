import collections, re, sys
pat = re.compile(r"bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\) on Layer (\S+)")
for rpt in sys.argv[1:]:
    z = collections.Counter(); zl = collections.defaultdict(collections.Counter)
    for b in open(rpt, errors='replace').read().split("violation type:")[1:]:
        m = pat.search(b)
        if not m:
            continue
        x = (float(m.group(1)) + float(m.group(3))) / 2; y = (float(m.group(2)) + float(m.group(4))) / 2
        d = min(x, y, 6600 - x, 6600 - y)
        side = ['W', 'S', 'E', 'N'][[x, y, 6600 - x, 6600 - y].index(d)]
        k = 'outer 0-140' if d < 140 else 'IO band 140-320' if d < 320 else 'gap 320-340' if d < 340 else 'core'
        if k != 'core':
            k += ' ' + side
        z[k] += 1; zl[k][m.group(5)] += 1
    tot = sum(z.values())
    print(rpt, tot)
    for k, v in sorted(z.items(), key=lambda a: -a[1]):
        print(f"  {k:22s} {v:6d} {100*v/tot:5.1f}%  " + ', '.join(f"{l} {c}" for l, c in zl[k].most_common(3)))
