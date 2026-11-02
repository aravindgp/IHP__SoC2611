#!/usr/bin/env python3
"""Summarize KLayout result databases (.lyrdb) from DRC runs.

usage: summarize_lyrdb.py [--waivers waivers.txt] [--json out.json] file.lyrdb|dir ...

Counts items per category (rule) and per cell, merges several lyrdb files
(main/antenna/density/maximal decks), applies an optional waiver list and
exits 1 if unwaived violations remain (0 otherwise).

Waiver file: one rule name (or fnmatch pattern) per line, optionally followed
by "@cell_pattern" to waive only in matching cells, '#' comments allowed:
    M1.b@RM_IHPSG13_*      # SRAM-internal
    Sdiff.*                # ...
"""
import argparse
import fnmatch
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


def parse_rdb(path):
    root = ET.parse(path).getroot()
    descr = {}
    cats = root.find("categories")

    def walk(cat, prefix=""):
        name = cat.findtext("name", "").strip().strip("'")
        full = prefix + name
        descr[full] = (cat.findtext("description") or "").strip()
        sub = cat.find("categories")
        if sub is not None:
            for c in sub.findall("category"):
                walk(c, full + ".")

    if cats is not None:
        for c in cats.findall("category"):
            walk(c)
    counts = Counter()
    per_cell = defaultdict(Counter)
    items = root.find("items")
    if items is not None:
        for it in items.findall("item"):
            cat = (it.findtext("category") or "").strip().strip("'")
            cell = (it.findtext("cell") or "").strip().split(":")[0]
            counts[cat] += 1
            per_cell[cat][cell] += 1
    return counts, per_cell, descr


def load_waivers(paths):
    out = []
    lines = []
    for path in paths:
        lines += Path(path).read_text().splitlines()
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        rule, _, cell = line.partition("@")
        out.append((rule.strip(), cell.strip() or "*"))
    return out


def waived(rule, cell, waivers):
    return any(fnmatch.fnmatchcase(rule, r) and fnmatch.fnmatchcase(cell, c)
               for r, c in waivers)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--waivers", action="append", default=[])
    ap.add_argument("--json")
    a = ap.parse_args()
    files = []
    for p in a.inputs:
        p = Path(p)
        files += sorted(p.glob("*.lyrdb")) if p.is_dir() else [p]
    waivers = load_waivers(a.waivers)
    total = Counter()
    cells = defaultdict(Counter)
    descr = {}
    for f in files:
        c, pc, d = parse_rdb(f)
        total.update(c)
        for k, v in pc.items():
            cells[k].update(v)
        descr.update(d)
    unwaived = Counter()
    wv = Counter()
    for rule, cc in cells.items():
        for cell, n in cc.items():
            (wv if waived(rule, cell, waivers) else unwaived)[rule] += n
    print(f"# lyrdb files: {len(files)}")
    for f in files:
        print(f"#   {f}")
    if not total:
        print("DRC CLEAN: 0 violations")
    else:
        print(f"{'rule':28s} {'count':>8s} {'waived':>7s}  top cells / description")
        for rule, n in sorted(total.items(), key=lambda x: -x[1]):
            top = ", ".join(f"{c}:{k}" for c, k in cells[rule].most_common(3))
            print(f"{rule:28s} {n:8d} {wv[rule]:7d}  {top}  | {descr.get(rule, '')[:70]}")
        print(f"TOTAL {sum(total.values())} violations in {len(total)} rules; "
              f"unwaived {sum(unwaived.values())} in {len(+unwaived)} rules")
    if a.json:
        Path(a.json).write_text(json.dumps({
            "files": [str(f) for f in files],
            "total": dict(total), "unwaived": dict(+unwaived),
            "per_cell": {k: dict(v) for k, v in cells.items()}}, indent=1))
    return 1 if sum(unwaived.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
