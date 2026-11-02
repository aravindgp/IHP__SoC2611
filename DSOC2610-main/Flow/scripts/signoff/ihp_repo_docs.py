#!/usr/bin/env python3
"""Fill the documentation of an IHP Open-Silicon-MPW IP repository (gen_structure.py layout) for DGrid-SoC1.

usage: ihp_repo_docs.py <ip_repo> <name> <bond_table.csv> [status=preliminary|final]
Writes README.md, doc/Specification.md, doc/Datasheet.md (pinout from the bond table), release/<ver>/ReleaseNote.md,
LICENSE (Apache-2.0 header + link), and the metadata fields of doc/info.json.
"""
import csv
import json
import sys
from pathlib import Path

repo, name, bond = sys.argv[1:4]
status = sys.argv[4] if len(sys.argv) > 4 else 'preliminary'
TRL = sys.argv[5] if len(sys.argv) > 5 else '3'   # declare only a level whose TRL-document items are all evidenced
R = Path(repo)
info = json.loads((R / 'doc' / 'info.json').read_text())
ver = info['release']['version']
prelim = status != 'final'
banner = ('> **Status: PRELIMINARY — not for fabrication.** Detailed routing has not converged and hold timing on\n'
          '> CPU↔SRAM paths is open; DRC/LVS are not clean yet. A final release will replace this one.\n\n') if prelim else ''

info.update({
    'repository': info.get('repository') or '',
    'pdk_version': 'IHP-Open-PDK dev dcb03b1e2d24250bccbb2e8783d55d2b4f734f14 (Merge PR #1311, 2026-10-30), unmodified',
    'process': 'SG13CMOS5L',
    'sealring_x': 6600.0,
    'sealring_y': 6600.0,
    'tools': {'synthesis': 'Yosys 0.70+277', 'place_and_route': 'OpenROAD dcf36133 (DGSE flow)',
              'drc_lvs': 'KLayout 0.30.5 with the IHP SG13CMOS5L decks', 'fill': 'PDK fill recipes (tiled)'},
    'trl': int(TRL),
    'dependencies': {'IHP-Open-PDK': 'dcb03b1e2d24250bccbb2e8783d55d2b4f734f14',
                     'libraries': ['sg13cmos5l_stdcell', 'sg13cmos5l_io', 'sg13cmos5l_sram (RM_IHPSG13_*)']},
})
(R / 'doc' / 'info.json').write_text(json.dumps(info, indent=2) + '\n')

readme = R / 'README.md'
# The published README (rewritten by the owner on GitHub) is kept: only the generator's stub is replaced.
if readme.exists() and 'Single-technology IP library.' not in readme.read_text():
    print(f'{readme}: kept (owner README); update its status wording by hand for a final release')
else:
    readme.write_text(f"""# {name} — DGrid-SoC1

{banner}RISC-V SoC with an AI accelerator (DeepGrid Semi), IHP SG13CMOS5L, QFN64, die 6.6 × 6.6 mm.
Category Digital / RiscV based digital SoC (RVSoC). Top cell `{name}` in every view. License: Apache-2.0.

- `doc/` — Specification, Datasheet (pinout), TRL assessment, `info.json`
- `release/{ver}/` — GDS (`gds/{name}.gds.gz`), netlists (`netlist/{name}.cdl.gz` for LVS, `{name}.v.gz`), release note
- `{name}-main/` — flow scripts, constraints, verification reports
- `dependencies/` — none (SRAM macros and IO cells are IHP library cells from the PDK)
""")

(R / 'doc' / 'Specification.md').write_text(f"""# {name} (DGrid-SoC1) — Specification

{banner}## Function
- VexRiscv RISC-V CPU (RV32IM, JTAG debug, I/D caches), boot ROM copy to a tightly-coupled memory, UART loader.
- ztachip AI accelerator: 4 PCOREs, data path, scratchpad SRAM, AXI-lite control.
- AXI interconnect (lean AXI split/merge), HyperBus memory interface, camera input + video stream writer,
  UART, timer, GPIO, APB bridge. Single main clock with integrated clock gating (2 ICG cells).

## Technology and physical data
| Item | Value |
|---|---|
| Process | IHP SG13CMOS5L (CMOS only, Metal1-4 + TopMetal1), 1.2 V core, 3.3 V IO |
| Die / seal ring | 6600 × 6600 µm, seal ring at the die edge |
| Core | 5920 × 5920 µm (340 µm pad-ring margin) |
| Package | QFN64 (64 pads: 48 signal, 16 supply) |
| Standard cells | ~290k after synthesis (~6.2 mm²), ~335k after P&R |
| SRAM | 298 RM_IHPSG13 macros, 214 KiB, ~12.9 mm² |
| IO | sg13cmos5l_io (IOPadIn / Out4mA / InOut4mA / supply pads), 70 × 70 µm bondpads |
""")

rows = list(csv.DictReader(open(bond)))
lines = ['| Pin | Side | Signal | Pad cell |', '|---:|---|---|---|']
lines += [f"| {r['pkg_pin']} | {r['side']} | {r['signal']} | {r['pad_cell'].replace('sg13cmos5l_', '')} |" for r in rows]
(R / 'doc' / 'Datasheet.md').write_text(f"""# {name} (DGrid-SoC1) — Datasheet

{banner}## Supplies
VDD/VSS: 1.2 V core, IOVDD/IOVSS: 3.3 V IO (one pair of each per side).

## QFN64 pinout
Pin numbering counter-clockwise from top-left (west 1-16, south 17-32, east 33-48, north 49-64).

""" + '\n'.join(lines) + '\n')

(R / 'release' / ver / 'ReleaseNote.md').write_text(f"""# {name} {ver} — release note

{banner}- GDS: `gds/{name}.gds.gz` (top cell `{name}`), seal ring + density fill included, saved with the KLayout options of
  Open-Silicon-MPW (GDS2, dbu 0.001, no PCell/library context, zero-length paths eliminated).
- Netlists: `netlist/{name}.cdl.gz` (LVS; IHP SRAM and IO cells as library cells), `netlist/{name}.v.gz`.
- Documentation: `doc/` (Specification, Datasheet with the QFN64 pinout).
""" + ("""- Known open items: detailed routing not converged (metal spacing/shorts on Metal2-4/TopMetal1), core routing into
  the pad-ring margin, 102 pad nets unrouted, hold timing on CPU↔SRAM paths, LVS not run.
""" if prelim else ''))

lic = R / 'LICENSE'
if not (lic.exists() and 'TERMS AND CONDITIONS FOR USE' in lic.read_text()):   # keep the full Apache-2.0 text
  lic.write_text("""Copyright 2026 DeepGrid Semi

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this design except in compliance with
the License. You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software and design data distributed under the License are
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
""")
import shutil
(R / 'release' / ver / 'doc').mkdir(parents=True, exist_ok=True)
for f in ('Specification.md', 'Datasheet.md'):
    shutil.copy(R / 'doc' / f, R / 'release' / ver / 'doc' / f)
print(f'docs written for {name} ({status}); {len(rows)} pins in the datasheet')
