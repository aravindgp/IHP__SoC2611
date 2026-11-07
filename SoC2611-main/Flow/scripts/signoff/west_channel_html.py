#!/usr/bin/env python3
"""Self-contained HTML animation of the west-edge fix on real data: SRAM macros, IO band, DRT markers (runs B and
D) and the guide boxes of the west nets at each stage (GRT original, run D clamp, soft channel, hard channel shift).
usage: west_channel_html.py <macros.txt> <runB.rpt> <runD.rpt> <guide_orig> <guide_clamp> <guide_soft> <keep> <out.html>"""
import json
import re
import sys

macf, rptB, rptD, g0, g1, g2, keepf, out = sys.argv[1:9]
X0, X1, Y0, Y1 = 0.0, 1000.0, 300.0, 1800.0
keep = set(l.strip() for l in open(keepf) if l.strip())


WEST = set()
cur = None
for ln in open(g0):
    p = ln.split()
    if len(p) == 1 and p[0] not in '()':
        cur = p[0]
    elif len(p) == 5 and int(p[0]) < 316800 and cur not in keep:
        WEST.add(cur)


def guides(path, limit=6000):
    cur, res = None, []
    for ln in open(path):
        p = ln.split()
        if len(p) == 1 and p[0] not in '()':
            cur = p[0]
        elif len(p) == 5 and cur in WEST:
            x0, y0, x1, y1 = (int(v) / 1000 for v in p[:4])
            if x1 > X0 and x0 < X1 and y1 > Y0 and y0 < Y1 and x0 < 900:
                res.append([round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1), p[4][-1]])
    step = max(1, len(res) // limit)
    return res[::step], len(res)


def markers(path, limit=4000):
    pat = re.compile(r"bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)")
    res = []
    for b in open(path, errors='replace').read().split("violation type:")[1:]:
        m = pat.search(b)
        if not m:
            continue
        x = (float(m.group(1)) + float(m.group(3))) / 2
        y = (float(m.group(2)) + float(m.group(4))) / 2
        if X0 <= x < X1 and Y0 <= y < Y1:
            res.append([round(x, 1), round(y, 1)])
    step = max(1, len(res) // limit)
    return res[::step], len(res)


macros = []
for ln in open(macf):
    p = ln.split()
    x0, y0, x1, y1 = map(float, p[:4])
    if x1 > X0 and x0 < X1 and y1 > Y0 and y0 < Y1:
        macros.append([x0, y0, x1, y1, p[4].replace('RM_IHPSG13_', '').replace('_bm_bist', '')])
mB, nB = markers(rptB)
mD, nD = markers(rptD)
G0, n0 = guides(g0)
G1, n1 = guides(g1)
G2, n2 = guides(g2)
data = dict(macros=macros, mB=mB, nB=nB, mD=mD, nD=nD, G=[G0, G1, G2], nG=[n0, n1, n2])
html = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSOC2610 West Channel</title>
<style>
:root{--bg:#0e2a33;--fg:#e6f1f2;--mute:#9bb3b8;--band:#ff6b6b;--strip:#ffd166;--sram:#4a7fa8;--g0:#e07000;--g1:#d04040;--g2:#2ec27e;--mk:#ff3b3b}
html,body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.4 "IBM Plex Sans",system-ui,sans-serif}
#wrap{max-width:1500px;margin:0 auto;padding:16px}
h1{font:700 26px/1.1 "Barlow Condensed",Arial Narrow,sans-serif;margin:0 0 4px}
.sub{color:var(--mute);margin:0 0 12px}
#top{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}
canvas{background:#f6f7f5;border:1px solid #345;max-width:100%;height:auto}
#side{flex:1;min-width:300px;max-width:460px}
.step{padding:10px 12px;border-left:4px solid #345;margin-bottom:8px;cursor:pointer;background:#10343f}
.step.on{border-color:var(--g2);background:#154452}
.step b{display:block;font-size:17px}
.step small{color:var(--mute)}
.ctl{margin:10px 0}button{background:#4fd1c5;color:#0e2a33;border:0;border-radius:4px;padding:8px 14px;font-weight:700;cursor:pointer;margin-right:8px}
.leg span{display:inline-block;margin-right:14px}.leg i{display:inline-block;width:14px;height:10px;margin-right:4px;vertical-align:middle}
table{border-collapse:collapse;margin-top:8px}td,th{padding:3px 8px;border-bottom:1px solid #345;text-align:left;font-variant-numeric:tabular-nums}
</style></head><body><div id="wrap">
<h1>DSOC2610: what we are doing at the west edge</h1>
<p class="sub">South-west corner of the 6.6 mm die, x 0–1000 µm, y 300–1800 µm, real coordinates from the routing database. Click a step or press Play.</p>
<div id="top"><canvas id="c" width="900" height="1350"></canvas>
<div id="side">
<div class="step on" data-s="0"><b>1. Original route (run B)</b><small>GRT sent the PCORE 0 SRAM nets into the IO band (pink), on top of the IO cells' power rails. Red dots: run B pass-13 DRT markers. Those shorts cannot be fixed by more passes.</small></div>
<div class="step" data-s="1"><b>2. Run D: guides pushed inside</b><small>Every guide box in the band was projected onto ONE 7.2 µm column at the band's inner edge. Red dots: run D markers. The band is clean, but the nets are now crammed into a single column of the 46 µm strip (yellow).</small></div>
<div class="step" data-s="2"><b>3. Soft channel (run E)</b><small>Same nets spread over the strip's 6 columns, and half of them steered east through the clean 50 µm gap between SRAM columns 1 and 2 (green boxes), with a Metal3 bridge above the array. Nothing moves. Routing starts now.</small></div>
<div class="step" data-s="3"><b>4. Hard channel (option 2)</b><small>SRAM column 1 (8 macros) shifts 32 µm east into that gap; the strip grows from 46 to 78 µm. Needs the power vias moved, 49 cell rows trimmed, 137 cells re-placed and ~1,100 nets re-routed, then placement, power-grid and DRC gates.</small></div>
<div class="ctl"><button id="play">Play</button><button id="prev">Prev</button><button id="next">Next</button></div>
<div class="leg"><span><i style="background:#ffd0d0"></i>IO band 140–320</span><span><i style="background:#fff0b8"></i>strip 320–366</span><span><i style="background:#cfe0ee;border:1px solid #4a7fa8"></i>SRAM</span><span><i style="background:#ff3b3b"></i>DRT marker</span><span><i style="background:#e07000"></i>guide (orig)</span><span><i style="background:#2ec27e"></i>guide (new)</span></div>
<table><tr><th>Stage</th><th>Markers in this window</th><th>Guide boxes of west nets</th></tr>
<tr><td>1 run B pass 13</td><td id="tB"></td><td id="t0"></td></tr>
<tr><td>2 run D pass 1</td><td id="tD"></td><td id="t1"></td></tr>
<tr><td>3 soft channel</td><td>to be measured</td><td id="t2"></td></tr>
<tr><td>4 hard channel</td><td>to be measured</td><td>re-routed</td></tr></table>
</div></div></div>
<script>
const D = __DATA__;
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const X0=0, X1=1000, Y0=300, Y1=1800, S=0.9, H=cv.height;
const px = x => (x-X0)*S, py = y => H-(y-Y0)*S;
document.getElementById('tB').textContent = D.nB.toLocaleString();
document.getElementById('tD').textContent = D.nD.toLocaleString();
D.nG.forEach((n,i)=>document.getElementById('t'+i).textContent = n.toLocaleString());
let step = 0, t0 = performance.now(), playing = false, shift = 0;
function draw(now){
  const dt = (now - t0)/1000;
  ctx.clearRect(0,0,cv.width,H);
  ctx.fillStyle = '#ffd0d0'; ctx.fillRect(px(140),0,(320-140)*S,H);
  const sw = step===3 ? 366+32 : 365.7;
  ctx.fillStyle = '#fff0b8'; ctx.fillRect(px(320),0,(sw-320)*S,H);
  shift = step===3 ? 32*Math.min(1, dt/1.2) : 0;
  for (const m of D.macros){
    const dx = (m[0] < 400 && m[1] < 1700) ? shift : 0;
    ctx.fillStyle = '#cfe0ee'; ctx.strokeStyle = '#4a7fa8'; ctx.lineWidth = 1;
    ctx.fillRect(px(m[0]+dx),py(m[3]),(m[2]-m[0])*S,(m[3]-m[1])*S); ctx.strokeRect(px(m[0]+dx),py(m[3]),(m[2]-m[0])*S,(m[3]-m[1])*S);
    ctx.fillStyle = '#4a7fa8'; ctx.font = '10px sans-serif'; ctx.fillText(m[4], px(m[0]+dx)+4, py(m[1])-4);
  }
  const gi = step===0 ? 0 : step===1 ? 1 : 2;
  const col = step===0 ? '#e07000' : step===1 ? '#d04040' : '#2ec27e';
  const G = D.G[gi]; const nShow = Math.min(G.length, Math.floor(G.length*Math.min(1, dt/1.5)));
  ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = 0.6; ctx.globalAlpha = 0.5;
  for (let i=0;i<nShow;i++){ const b=G[i]; const x=px(Math.max(b[0],X0)), y=py(Math.min(b[3],Y1)); const w=(Math.min(b[2],X1)-Math.max(b[0],X0))*S, h=(Math.min(b[3],Y1)-Math.max(b[1],Y0))*S; ctx.globalAlpha=0.12; ctx.fillRect(x,y,w,h); ctx.globalAlpha=0.5; ctx.strokeRect(x,y,w,h); }
  ctx.globalAlpha = 1;
  const M = step===0 ? D.mB : step===1 ? D.mD : [];
  const mShow = Math.min(M.length, Math.floor(M.length*Math.min(1, (dt-0.8)/1.2)));
  ctx.fillStyle = '#ff3b3b';
  for (let i=0;i<mShow;i++){ ctx.beginPath(); ctx.arc(px(M[i][0]),py(M[i][1]),1.4,0,6.28); ctx.fill(); }
  ctx.fillStyle = '#123'; ctx.font = '13px sans-serif';
  ctx.fillText('x 0..1000 um  |  y 300..1800 um  |  IO band 140..320  |  strip 320..'+sw.toFixed(0)+'  |  SRAM column 1 at x '+(365.7+shift).toFixed(1), 10, H-10);
  if (step===3 && shift>0){ ctx.fillStyle='#2ec27e'; ctx.font='bold 14px sans-serif'; ctx.fillText('column 1 shifted +'+shift.toFixed(0)+' um -> strip '+(46+shift).toFixed(0)+' um wide', px(400), 30); }
  requestAnimationFrame(draw);
}
function setStep(s){ step=(s+4)%4; t0=performance.now(); document.querySelectorAll('.step').forEach(e=>e.classList.toggle('on', +e.dataset.s===step)); }
document.querySelectorAll('.step').forEach(e=>e.onclick=()=>{playing=false;setStep(+e.dataset.s)});
document.getElementById('prev').onclick=()=>{playing=false;setStep(step-1)};
document.getElementById('next').onclick=()=>{playing=false;setStep(step+1)};
document.getElementById('play').onclick=()=>{playing=!playing; document.getElementById('play').textContent=playing?'Pause':'Play';};
setInterval(()=>{ if(playing) setStep(step+1); }, 5000);
requestAnimationFrame(draw);
</script></body></html>'''
open(out, 'w').write(html.replace('__DATA__', json.dumps(data, separators=(',', ':'))))
print('wrote', out, 'markers B/D', nB, nD, 'guides', n0, n1, n2)
