#!/usr/bin/env python3
"""Exit 0 if the DPASS probe result json has score <= max, 1 otherwise (2 if unreadable).  usage: gate_score.py <json> <max>"""
import json
import sys

try:
    s = json.load(open(sys.argv[1])).get('score', 1e9)
except Exception as e:  # noqa
    print(f'GATE_SCORE unreadable: {e}'); sys.exit(2)
ok = s <= float(sys.argv[2])
print(f'GATE_SCORE {s} {"<=" if ok else ">"} {sys.argv[2]} -> {"PASS" if ok else "FAIL"}')
sys.exit(0 if ok else 1)
