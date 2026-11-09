#!/usr/bin/env python3
"""DPASS (Deep Probe using Autoresearch, Score and Select) -- DSOC2610 (SoC2611, SG13CMOS5L, 6.6 mm) hand-FLOORPLAN
campaign, 5 Nov 2026.  Hypotheses and kill criteria are written here BEFORE a probe runs; every probe is the real
engine flow (fixed macro placements -> PDN -> GPL -> repair -> DPL -> CTS -> GRT) stopped after the groute
checkpoint, scored on the global-route overflow (GRT-0096 Total), the number detailed routing inherits.

Baseline (what every probe must beat): run c7w32-6600-respread, automatic macro placer (halo 25), GRT overflow
49,512 (Metal2 17,943 / Metal3 8,633 / Metal4 15,473 / TopMetal1 7,463), row util 37.7%; its detailed route never
closed (west SRAM column 26 um from the pad ring).  NOTES recipe gate: overflow < 20k before DRT.

Floorplans come from fp2_plan.py (env FP_KNOBS), macros grouped by the logic that drives them, SRAM pin edges facing
standard-cell strips, hard placement blockages on the in-row gaps and the 100 um band inside the pad ring.
Round 1 (5 Nov 01:06 IST): all four probes died in the post-CTS detailed_placement (DPL-0036 on 125/475/189/725
'clkload' dummy loads): CTS drops them next to their sinks, 3,398 of 6,603 inside the hard blockages (the 100 um band
at the die-edge pins), and the legaliser's default search range cannot move them out -> dpl_max_disp '1500 1500'.
Score (lower is better): GRT Total overflow; 1e6 if the flow did not reach groute; +1e5 if the planner reports a
block that does not fit or an overlap.

    dpass_dsoc_fp.py run [tag ...]     run probes (PAR in parallel, 4 threads each; default: all)
    dpass_dsoc_fp.py table             collect + score everything run so far
    dpass_dsoc_fp.py plan <tag>        only draw the floorplan of one probe
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DG = Path('/root/.claude/jobs/658ac326/tmp/dgse/DGSE')
A = Path('<design-repo>/HW/asic')
BASE_CFG = DG / 'runs/c7w32-6600-respread/config.json'
NET = DG / 'runs/soc1-c5l-chip7w32-net/soc2611_chip_top_synth.v'
PLACE_TXT = Path('/workspace/chip_drt/density/place_F7.txt')
CELLS_TXT = Path('/workspace/chip_fp2/cellgroups_F7.txt')
OUT = Path('/workspace/chip_fp2/dpass')
PAR = int(os.environ.get('DPASS_PAR', '4'))
THREADS = int(os.environ.get('DPASS_THREADS', '8'))
BASELINE_OVF = 49512

# tag: (hypothesis, kill criterion, planner knobs, engine knobs)
PROBES = {
    'A-bands': ('owner blocks in two PCORE bands + a middle band, SRAM pins facing 100-200 um logic strips, '
                '60 um gaps, 100 um pad band: the pin traffic no longer funnels through one strip',
                f'killed if GRT overflow >= {BASELINE_OVF} (the automatic floorplan)',
                dict(layout='bands', G=60, BB=20, strip_scale=1.0), dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'B-spread': ('same blocks with the macros pulled apart (100 um gaps, 40 um back-to-back) and shorter strips: '
                 'wider vertical escapes beat taller strips', 'killed if overflow is not below A',
                 dict(layout='bands', G=100, BB=40, strip_scale=0.6), dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'C-corners': ('PCORE squares in the four corners, side blocks between them, datapath/zmem/axi in a centre column: '
                  'shorter PCORE<->centre paths and no full-width macro walls', 'killed if overflow is not below A',
                  dict(layout='corners', G=60, BB=20, strip_scale=1.0), dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    # ---- round 2 (5 Nov 09:30 IST): round 1b killed all four bands/corners floorplans (102,785-126,596 overflow); the
    # overflow sat on the back-to-back macro row pairs (unaligned gaps block N-S crossings), 24-29 percent clock nets.
    'E-mpl-core440': ('the automatic placer (halo 25, level 1, the 49.5k baseline) run on a core shrunk by 100 um on '
                      'every side: keeps its routable open areas and removes the only known killer (macros at the '
                      'pad ring)', f'killed if GRT overflow >= {BASELINE_OVF}, or any macro inside the 100 um band',
                      dict(pl='/root/.claude/jobs/658ac326/tmp/dgse/DGSE/runs/mpl-c7w32/h25_core440.pl'),
                      dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'F-single': ('bands with single rows (every row faces its own strip, no back-to-back pairs), strips x0.5: a '
                 'one-row wall with a strip on each side can be crossed', 'killed if overflow is not below D (102,785)',
                 dict(layout='bands', G=60, BB=20, strip_scale=0.5, pairs=False), dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'G-highway': ('bands split into two sub-columns per block with 150 um vertical highways aligned across all bands, '
                  'strips x0.5, PCORE band 1000: N-S traffic gets its own channels', 'killed if overflow is not below D',
                  dict(layout='bands', G=60, BB=20, strip_scale=0.5, cols=2, CW=150, pch=1000, cpuh=1300), dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H-targeted': ('ChatGPT edit of G (5 Nov 09:50 IST): 123 macros moved, 8 reoriented; highways widened to ~180 um, '
                   '73 pin faces freed (no pin faces another macro back under 60 um); no cell blockages on the lanes',
                   'killed if overflow is not below G', dict(pl='/workspace/chip_fp2/handoff/H-highway.pl'),
                   dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'I-balanced': ('ChatGPT edit of G: 201 macros moved, three ~220 um vertical and horizontal freeways balanced across '
                   'the die', 'killed if overflow is not below H', dict(pl='/workspace/chip_fp2/handoff/I-highway.pl'),
                   dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'J-auto-bw0': ('automatic placer on the fenced core with -boundary_weight 0 (halo 25, level 1): no edge walls, '
                   'clusters with an open centre like the 49.5k baseline but 100 um off the pad ring',
                   'killed if overflow is not below the thread-matched baseline', dict(pl='/workspace/chip_fp2/handoff/J_auto_bw0.pl'),
                   dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'K-relocate': ('the proven automatic placement (49.5k, DRT converged everywhere but the west strip) with ONLY its '
                   '28 west-column macros relocated: 8 PCORE register files in a row above the PCORE SRAM rows (pins up '
                   'into the PCORE logic), 16 stream lookups + 4 AXI tiles in the open centre (rows of 4, 120 um '
                   'channels); the 53 edge macros on the other three sides stay (they routed)',
                   'killed if overflow >= 49,567 (it should be about equal) or if the DRT later shows a new wall',
                   dict(pl='/workspace/chip_fp2/handoff/K_relocate.pl', allow_band=True),
                   dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H2-noring': ('H without the 100 um cell blockage ring (routes may still use the band; cells allowed there as '
                  'in the reproducible 49.5k baseline)', 'killed if overflow is not below H (55,655)',
                  dict(pl='/workspace/chip_fp2/handoff/H-highway.pl', no_ring=True), dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'K2-noring': ('K without the ring: isolates the ring from the 28 moved macros (baseline reproduces at 49,512)',
                  'killed if overflow is not below K (168,268)',
                  dict(pl='/workspace/chip_fp2/handoff/K_relocate.pl', allow_band=True, no_ring=True), dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H3-axi120': ('H2 with the AXI block rows above y 2700 shifted up 60 um: the 2P 64x32 row pins face the 256x32 '
                  'row pins across 120 um instead of 60 (drtH2 pass-3 wall: 7,551 markers in one 150 um window there)',
                  'killed if GRT overflow is not below H2 (11,716) or if the drtH2 wall clears by itself',
                  dict(pl='/workspace/chip_fp2/handoff/H3_axi120.pl', no_ring=True), dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H4-axi3': ('H3 with the AXI block re-packed in three sub-columns (13 rows each, 85 um pin strips everywhere, '
                'y 2140-3921) and the camera FIFOs moved above PCORE1: the dp/AXI seam column stays the slowest part '
                'of drtH3 (-17 percent/pass vs -50 elsewhere)', 'killed if GRT overflow is not within 10 percent of H2',
                dict(pl='/workspace/chip_fp2/handoff/H4_axi3.pl', no_ring=True), dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H5-slotblk': ('H4 with a placement blockage over the slot the camera FIFOs left (x 3300-3900, y 1955-2140): in H4 '
                   '635 dp_gen_core + 86 dp_fetch cells moved into it, their nets cross the 180 um highway at '
                   'y 1900-2100 and that highway holds 8.3k shorts at drtH4 pass 3 (H3: 3.0k, same macros)',
                   'killed if GRT overflow is above 10,000 (H4 9,520) or the x 2740 / y 1540 window at DRT pass 3 '
                   'is not below H3 (3,835)',
                   dict(pl='/workspace/chip_fp2/handoff/H4_axi3.pl', no_ring=True, blk=['3300 1955 3900 2140']),
                   dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H6-cam2010': ('H4 with the 4 camera FIFO macros put back into the slot east of the dp highway (H3 x positions, '
                   'R0 at y 2010: a 55 um pin strip above the pin-free ztachip_in row top, 11 um under the AXI MX row): '
                   'the macro bodies keep cells AND M1-M4 routes out of the slot as in H3, without the global '
                   'placement perturbation of the H5 cell blockage (H5 GRT 11,655: the dp spill went elsewhere)',
                   'killed if GRT overflow is above 10,000 (H4 9,520) or the x 2740 / y 1540 window at DRT pass 3 '
                   'is not below H3 (3,835)',
                   dict(pl='/workspace/chip_fp2/handoff/H6_cam2010.pl', no_ring=True),
                   dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H7-pad2': ('H4 unchanged (same global placement) + engine pad_instances: 2 sites of detailed-placement padding '
                'each side on every dp_gen_core cell, so the dp_gen_core cluster that fills the 180 um corridor + the '
                'camera slot spreads out (drtH4 wall x 3120-3300 y 1900-2140: 6,746 of 16,059 markers at pass 9, '
                '-3.5%/pass; 1,401 nets, dp_gen_primary buffer trees)',
                'killed if GRT overflow is above 11,000 (H4 9,520) or the highway window at DRT pass 3 is not below '
                '6,000 (H4 9,364)',
                dict(pl='/workspace/chip_fp2/handoff/H4_axi3.pl', no_ring=True),
                dict(halo=10, density=0.6, dpl_max_disp='1500 1500', pad_instances='*dp_1_i/dp0_i/dp_gen_core_i* 2')),
    'H8-pad1dp': ('H4 + pad_instances 1 site each side on the whole dp0 datapath (dp_gen_core, dp_fetch, dp_sink, '
                  'dp_source logic): milder, wider spread than H7',
                  'killed if GRT overflow is above 11,000 or the highway window at DRT pass 3 is not below 6,000',
                  dict(pl='/workspace/chip_fp2/handoff/H4_axi3.pl', no_ring=True),
                  dict(halo=10, density=0.6, dpl_max_disp='1500 1500', pad_instances='*dp_1_i/dp0_i/* 1')),
    'H9-corrblk': ('H4 + a hard placement blockage on the dp highway corridor (x 3120-3300, y 1400-2300) so the '
                   'dp_gen_core cluster cannot sit in the macro-bounded 180 um corridor and the corridor becomes the '
                   'pure routing channel the floorplan intended (H5 blocked the SLOT and pushed cells INTO the '
                   'corridor; H7 padding left the cluster in place: wall 8,336 vs 9,364)',
                   'GRT only as sanity (< 15,000); killed if the highway window at DRT pass 3 is not below 6,000 or '
                   'the pass-3 total is above 47,000 (H4 40,601 + 15%)',
                   dict(pl='/workspace/chip_fp2/handoff/H4_axi3.pl', no_ring=True, blk=['3120 1400 3300 2300']),
                   dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H10-corrslot': ('H9 + the camera slot blocked as well (x 3300-3900, y 1955-2140): the cluster must settle west '
                     'of the dp column or east of x 3900', 'same as H9',
                     dict(pl='/workspace/chip_fp2/handoff/H4_axi3.pl', no_ring=True,
                          blk=['3120 1400 3300 2300', '3300 1955 3900 2140']),
                     dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H11-cputags': ('H10 (H4 + corridor + slot blockages) with the two CPU ibus-tag 64x22 macros moved from the east '
                    'column of the cache pair (x 5634-6160, y 4359-4894) to the free rows west of the lower cache '
                    '(x 3360-3886, y 4360-4570): opens a 586 um vertical channel east of the 1024x32 caches. In '
                    'drtH10 265 of the 442 Metal4 guide boxes inside macros (and the M4 power shorts they cause) are '
                    'pass-through nets of CPU logic split north/south by the east cache pair with no channel east.',
                    'GRT sanity < 15,000; killed if guides_in_macros (margin -10) still shows > 150 Metal4 boxes '
                    'inside macros on the chip guides, or the DRT pass-3 total is above 40,000',
                    dict(pl='/workspace/chip_fp2/handoff/H11_cputags.pl', no_ring=True,
                         blk=['3120 1400 3300 2300', '3300 1955 3900 2140']),
                    dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H12-cpueast': ('H11 + the two east CPU 1024x32 caches shifted 586 um east to the core-edge margin (x 5474-6160): '
                    'opens a central north-south passage x 4640-5474 (lower row) / x 4343-5474 (upper row) through '
                    'the CPU block, so pass-through nets of the CPU logic north/south of the caches detour 0-400 um '
                    'instead of crossing the macros (H11 with only the east column opened: still 371 M4 guide boxes '
                    'inside macros, 589 of them on these two caches)',
                    'GRT sanity < 15,000; killed if guides_in_macros (margin -10) still shows > 150 Metal4 boxes '
                    'inside macros on the chip guides',
                    dict(pl='/workspace/chip_fp2/handoff/H12_cpueast.pl', no_ring=True,
                         blk=['3120 1400 3300 2300', '3300 1955 3900 2140']),
                    dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H13-pockets': ('H12 + placement blockages on every dead space of the macro placement (fp_pockets.py: 146 rects, '
                    '5.0 mm2): the 60-130 um pockets between two macro rows whose pin edges face each other and the '
                    '100 um margin strips between the pad ring and the edge-row macros. H12 DRT pass 3 showed the '
                    'remaining inside-macro shorts (PCORE register-file rows, AXI FIFO stack x 4464, dp FIFO columns '
                    'x 1930/2407) come from cells placed in these pockets: 98 of the 112 nets with guides inside those '
                    'macros have a pin in a pocket, and the pocket cells have no vertical routing exit (M1-M4 blocked '
                    'inside the macros, no layer above TopMetal1 in cmos5l)',
                    'GRT sanity < 15,000; killed if guides_in_macros (margin -10) shows > 60 Metal4 boxes inside '
                    'macros on the chip guides (H12: 166), or DRT pass 3 > 40,000',
                    dict(pl='/workspace/chip_fp2/handoff/H12_cpueast.pl', no_ring=True,
                         blk=['3120 1400 3300 2300', '3300 1955 3900 2140'],
                         blk_file='/workspace/chip_fp2/handoff/H12_pockets.txt'),
                    dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'H14-camspread': ('H13 + (a) the camera write-FIFO row at y 1240 (four flat macros 3480-5899 with 60 um gaps, a '
                      '2.4 mm wall above a 0.4 mm band of cells) spread to 147 um gaps: slice1 4243 -> 4330, '
                      'write_fifo2 slice0 5006 -> 5180, slice1 5482 -> 5743 (ends at the 6160 margin), and (b) '
                      'placement blockages on every thin (< 30 um) blank gap between stacked macros as well (88 more '
                      'rects, 234 total, 5.56 mm2). H13 DRT pass 3 still had 866 shorts inside macros: camera FIFOs '
                      '347 (traffic from the band below through the 60 um gaps), dp FIFO rows ~390 (cells in 20 um '
                      'blank gaps between stacked rows)',
                      'GRT sanity < 15,000; killed if guides_in_macros (margin -10) shows > 25 Metal4 or > 150 '
                      'Metal2 boxes inside macros (H13: 35 / 209), or DRT pass 3 > 25,000',
                      dict(pl='/workspace/chip_fp2/handoff/H14_camspread.pl', no_ring=True,
                           blk=['3120 1400 3300 2300', '3300 1955 3900 2140'],
                           blk_file='/workspace/chip_fp2/handoff/H14_pockets.txt'),
                      dict(halo=10, density=0.6, dpl_max_disp='1500 1500')),
    'D-h25-d050': ('A with the previous best run\'s engine knobs: halo 25 keeps cells off the macro edges, '
                   'GPL density 0.5 spreads the logic into the strips', 'killed if overflow is not below A',
                   dict(layout='bands', G=60, BB=20, strip_scale=1.0), dict(halo=25, density=0.5, dpl_max_disp='1500 1500')),
}


def plan(tag):
    hyp, kill, kn, ek = PROBES[tag]
    pre = OUT / tag
    if 'pl' in kn:        # placement file from the automatic placer: convert, blockages = the 100 um band only
        r = subprocess.run([sys.executable, str(A / 'dgse/runs/cmos5l-01/scripts/pl_to_placements.py'), kn['pl'],
                            str(DG / 'runs/mpl-c7w32/macros.txt'), str(pre) + '_placements.json'], capture_output=True, text=True)
        n_out = sum(1 for ln in open(kn['pl']) if len(ln.split()) == 4 and
                    (float(ln.split()[1]) < 440 or float(ln.split()[2]) < 440))
        txt = r.stdout + r.stderr + f'\nmacros with lower-left inside the band: {n_out}\n'
        ring = '340.3 340.2 6259.7 440.3;340.3 6159.7 6259.7 6259.7;340.3 440.3 440.3 6159.7;6159.7 440.3 6259.7 6159.7'
        blks = ([] if kn.get('no_ring') else [ring]) + list(kn.get('blk', []))   # blk: extra 'x0 y0 x1 y1' um rects
        if kn.get('blk_file'):   # fp_pockets.py output: "BLK x0 y0 x1 y1  # why"
            blks += [' '.join(ln.split()[1:5]) for ln in open(kn['blk_file']) if ln.startswith('BLK ')]
            txt_extra = f'blockages from {kn["blk_file"]}: {len(blks)} total\n'
        else:
            txt_extra = ''
        (OUT / f'{tag}_blockages.txt').write_text(';'.join(blks))
        (OUT / f'{tag}_summary.txt').write_text(txt)
        (OUT / f'{tag}_plan.log').write_text(txt)
        ok = ('298 placements' in txt) and (n_out == 0 or kn.get('allow_band'))
        return ok, txt
    env = dict(os.environ, FP_KNOBS=json.dumps(kn))
    r = subprocess.run([sys.executable, str(A / 'signoff/fp2_plan.py'), str(PLACE_TXT), str(CELLS_TXT), str(pre)],
                       env=env, capture_output=True, text=True)
    txt = r.stdout + r.stderr
    (OUT / f'{tag}_plan.log').write_text(txt)
    bad = ('DOES NOT FIT' in txt) or ('OVERLAP' in txt) or ('OUTSIDE' in txt) or ('placed 298 of 298' not in txt)
    return not bad, txt


def run_probe(tag):
    hyp, kill, kn, ek = PROBES[tag]
    res_f = OUT / f'{tag}.json'
    if res_f.exists():
        return json.load(open(res_f))
    ok, ptxt = plan(tag)
    name = f'dpass-dsoc-{tag}'
    R = DG / 'runs' / name
    t0 = time.time()
    if not ok:
        res = dict(tag=tag, hypothesis=hyp, kill=kill, knobs=kn, engine=ek, plan_ok=False, score=1e6 + 1e5,
                   note='planner: does not fit / overlap')
        json.dump(res, open(res_f, 'w'), indent=1)
        return res
    if not (R / 'build/ck_groute.odb').exists():
        if R.exists():
            shutil.rmtree(R)
        subprocess.run([sys.executable, str(A / 'dgse/runs/cmos5l-01/scripts/derive_run.py'), str(BASE_CFG), name,
                        str(NET), f'threads={THREADS}', f'macro_halo={ek["halo"]}',
                        f'place_density_override={ek["density"]}'], check=True, capture_output=True)
        c = json.load(open(R / 'config.json'))
        c['macro_placements'] = json.load(open(OUT / f'{tag}_placements.json'))['macro_placements']
        bl = (OUT / f'{tag}_blockages.txt').read_text().strip()
        c['place_blockages'] = bl.split(';') if bl else []
        for k, v in ek.items():            # extra engine config keys (e.g. dpl_max_disp, cts_extra)
            if k not in ('halo', 'density'):
                c[k] = v
        c['notes'] = f'DPASS DSOC2610 floorplan probe {tag}: {hyp} | kill: {kill} | knobs {kn} {ek}'
        json.dump(c, open(R / 'config.json', 'w'), indent=1)
        env = dict(os.environ, DGSE_CHECKPOINTS='1', DGSE_PNR_STOP_AFTER='groute', DGSE_THREADS=str(THREADS))
        subprocess.run(['bash', str(A / 'dgse/runs/cmos5l-01/scripts/launch.sh'), name, 'floorplan_pnr'], env=env)
    return finish(tag, R, t0)


def parse_log(txt):
    out = {}
    m = re.search(r'row utilisation after repair_design = ([\d.]+)%', txt)
    out['row_util'] = float(m.group(1)) / 100 if m else None
    tabs = [m.start() for m in re.finditer(r'GRT-0096\] Final congestion report', txt)]
    if tabs:
        seg = txt[tabs[-1]:tabs[-1] + 2000]
        rows = re.findall(r'^(Metal\d|TopMetal\d|Total)\s+\d+\s+\d+\s+([\d.]+)%\s+\d+ / +\d+ / +(\d+)', seg, re.M)
        out['grt'] = {k: dict(usage=float(u), overflow=int(o)) for k, u, o in rows}
    out['stopped'] = 'stop-after: checkpoint groute written' in txt
    g = re.findall(r'GRT-0053\].*', txt)
    out['grt_warn'] = g[-1] if g else None
    for k in ('DPL-0036', 'DPL-0011', 'PSM-0040', 'ERROR'):
        out['n_' + k] = len(re.findall(re.escape(k), txt))
    return out


def finish(tag, R, t0):
    hyp, kill, kn, ek = PROBES[tag]
    log = R / 'logs/openroad.log'
    txt = log.read_text(errors='replace') if log.exists() else ''
    res = dict(tag=tag, hypothesis=hyp, kill=kill, knobs=kn, engine=ek, plan_ok=True, pnr_s=round(time.time() - t0))
    res.update(parse_log(txt))
    summ = OUT / f'{tag}_summary.txt'
    res['plan_summary'] = summ.read_text() if summ.exists() else ''
    ov = (res.get('grt') or {}).get('Total', {}).get('overflow')
    res['score'] = (ov if ov is not None else 1e6)
    json.dump(res, open(OUT / f'{tag}.json', 'w'), indent=1)
    return res


def table():
    rows = [json.load(open(f)) for f in sorted(OUT.glob('*.json')) if f.name.count('_') == 0 or f.stem in PROBES]
    rows = [r for r in rows if 'tag' in r]
    print(f"{'probe':12} {'rowutil':>8} {'M2':>7} {'M3':>7} {'M4':>7} {'TM1':>7} {'TOTAL':>8} {'score':>9}  verdict")
    best_a = next((r for r in rows if r['tag'] == 'D-h25-d050'), None)
    for r in sorted(rows, key=lambda r: r['score']):
        g = r.get('grt') or {}
        f = lambda k: g.get(k, {}).get('overflow', '-')
        u = r.get('row_util')
        ov = f('Total')
        if ov == '-':
            v = 'no groute checkpoint'
        elif ov >= BASELINE_OVF:
            v = 'KILLED: not below the automatic floorplan'
        elif r['tag'] != 'D-h25-d050' and best_a and (best_a.get('grt') or {}).get('Total', {}).get('overflow', 1e9) <= ov:
            v = 'KILLED: not below D (best of round 1b)'
        else:
            v = 'alive' + (' (meets <20k gate)' if ov < 20000 else '')
        print(f"{r['tag']:12} {'-' if u is None else round(100 * u, 1):>8} {f('Metal2'):>7} {f('Metal3'):>7} "
              f"{f('Metal4'):>7} {f('TopMetal1'):>7} {ov:>8} {r['score']:9.0f}  {v}")


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1]
    if cmd == 'table':
        table()
    elif cmd == 'plan':
        ok, txt = plan(sys.argv[2]); print(txt[-1500:]); print('PLAN_OK', ok)
    else:
        tags = sys.argv[2:] or list(PROBES)
        print('DPASS start', time.strftime('%H:%M:%S'), tags, flush=True)
        with ThreadPoolExecutor(PAR) as ex:
            for r in ex.map(run_probe, tags):
                print(r['tag'], r.get('row_util'), (r.get('grt') or {}).get('Total'), r['score'],
                      time.strftime('%H:%M:%S'), flush=True)
        table()
        print('DPASS done', time.strftime('%H:%M:%S'), flush=True)
