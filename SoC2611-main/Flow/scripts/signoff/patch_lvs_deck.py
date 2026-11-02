#!/usr/bin/env python3
"""Make a private copy of the PDK LVS runner + deck with extra LVS DSL statements before `align`.

usage: patch_lvs_deck.py <outdir> [--blackbox PATTERN]... [--stmt 'ruby statement']...
Writes <outdir>/run_lvs.py (verbatim copy; it runs the deck next to itself) and
<outdir>/sg13cmos5l.lvs (PDK deck, `# %include rule_decks/...` made absolute, statements inserted).
--blackbox P  ->  blank_circuit('P')   (empties circuit P on both sides: SRAM macros, IO cells, ...)
"""
import argparse
import os
import re
import shutil
from pathlib import Path

LVS = Path(os.environ.get('KLAYOUT_TECH', '/root/.claude/jobs/658ac326/tmp/pdk_root/'
                          'ihp-sg13cmos5l/libs.tech/klayout/tech')) / 'lvs'

ap = argparse.ArgumentParser()
ap.add_argument('outdir')
ap.add_argument('--blackbox', action='append', default=[])
ap.add_argument('--stmt', action='append', default=[])
a = ap.parse_args()
out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
shutil.copy(LVS / 'run_lvs.py', out / 'run_lvs.py')
deck = (LVS / 'sg13cmos5l.lvs').read_text()
deck = deck.replace('# %include rule_decks/', f'# %include {LVS}/rule_decks/')
stmts = [f"blank_circuit('{p}')" for p in a.blackbox] + a.stmt
ins = ''.join(f"  logger.info(\"signoff patch: {s.replace(chr(34), chr(39))}\")\n  {s}\n" for s in stmts)
deck, n = re.subn(r'^(\s*)align\s*$', lambda m: ins + m.group(0), deck, count=1, flags=re.M)
assert n == 1, 'align statement not found in deck'
(out / 'sg13cmos5l.lvs').write_text(deck)
print(f'patched deck in {out}: {len(stmts)} statement(s) before align')
