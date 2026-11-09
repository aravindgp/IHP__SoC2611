#!/usr/bin/env python3
"""Replace the status paragraph of the release notes in the IHP repo with the exact state.
usage: fix_release_notes.py [version ...]   (default: all versions listed below)"""
import re
import sys

repo = '/workspace/ihp_ip_repo/IHP__DSOC2610/release/'
notes = {
 'v.1.2.0': ("> **Status: PRELIMINARY, not for fabrication.** Routed state after ECO round H (9 Nov, 05:17 UTC): 42 power shorts\n"
             "> between signal wires and the SRAM macros' VDD/VSS stripes inside the macros remain, on 17 nets, 5 of which touch\n"
             "> both VDD and VSS; 1,433 detailed-route violations in total, about 1,200 of them signal-to-signal shorts in one\n"
             "> congestion knot around the dp_sink3 / dp_fetch SRAM block (see `../../STATUS_2026-11-09.md`). Density (PDK fill +\n"
             "> top-up, `density_fullfill.txt`): 0 violations. Antenna repair, LVS and timing sign-off not run on this GDS.\n"
             "> Superseded the same day by v.1.3.0."),
 'v.1.3.0': ("> **Status: PRELIMINARY, not for fabrication.** First routed state with **no supply short**: 0 power shorts inside\n"
             "> the SRAM macros, 0 nets touching VDD or VSS (round H + explicit channel routes for the last 17 crossing nets,\n"
             "> 9 Nov 05:58 UTC). 1,760 detailed-route violations remain, 1,194 of them signal-to-signal shorts in one 50 um\n"
             "> elbow (x 2800-2850, y 2900-2950) where a 256x32 and a 64x16 SRAM slice overlap by 2.8 um and the 60 um channel\n"
             "> turns through a 20 um gap; the rest is ordinary spacing residue. Density (PDK fill + top-up, `density_fullfill.txt`):\n"
             "> 0 violations. Antenna repair, LVS and timing sign-off not run on this GDS; IHP minimum DRC deck running on it,\n"
             "> result to be added. Closure of the elbow (local floorplan ECO) is the next step, `../../STATUS_2026-11-09.md`."),
 'v.1.3.1': ("> **Status: PRELIMINARY, not for fabrication.** The v.1.3.0 routing base after 32 further detailed-route passes\n"
             "> (9 Nov 09:40 UTC): still **0 power shorts inside the SRAM macros and 0 nets touching VDD or VSS**; 1,624\n"
             "> detailed-route violations remain (1,495 shorts between signal nets, 129 spacing). 1,532 of them lie in one 50 um\n"
             "> square (x 2800-2850, y 2900-2950) on 109 nets, where a 256x32 and a 64x16 SRAM slice overlap by 2.8 um and the\n"
             "> 60 um channel turns through a 20 um gap; 92 are anywhere else on the chip. Passes alone do not dissolve that\n"
             "> knot (1,760 -> 1,288 at pass 24 -> 1,624 after the pass-25 rip-up); a staged local floorplan ECO that moves the\n"
             "> 64x16 slice 63 um east and re-routes the affected nets is running (`../../STATUS_2026-11-09.md`). Density (PDK\n"
             "> fill + top-up, `density_fullfill.txt`): 0 violations. Antenna repair, LVS and timing sign-off not run on this GDS;\n"
             "> IHP minimum DRC deck running on it, result to be added. Target: a checked GDS by 12 November for the 20 November slot."),
}
if len(sys.argv) > 1:
    notes = {v: notes[v] for v in sys.argv[1:]}
for ver, new in notes.items():
    p = repo + ver + '/ReleaseNote.md'
    s = open(p).read()
    s2 = re.sub(r"> \*\*Status: PRELIMINARY.*?(?=\n\n## Contents)", new, s, count=1, flags=re.S)
    if s2 == s: sys.exit('no change in ' + p)
    open(p, 'w').write(s2); print('updated', p)
