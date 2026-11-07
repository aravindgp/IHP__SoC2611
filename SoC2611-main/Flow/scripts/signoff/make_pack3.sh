#!/bin/bash
# Assemble the H10 inside-macro-shorts consultation pack under /workspace/chip_fp2/pack3.
set -u
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
P=/workspace/chip_fp2/pack3; D=$P/data; C=/workspace/chip_fp2
MAC=$C/handoff/macros_name_w_h_um.txt
mkdir -p "$D"
: > "$D/drt_pass_histories.txt"
for t in H4b H10; do
  echo "== drt$t" >> "$D/drt_pass_histories.txt"
  grep -a "Number of violations" "$C/drt$t/drt_chip.log" | grep -a -o "[0-9]*\.$" | tr -d . | nl -v0 | awk '{print "pass " $1 ": " $2}' >> "$D/drt_pass_histories.txt"
done
python3 "$S/drc_map.py" $C/drtH10/chk/all30.rpt H10_pass30 > "$D/H10_pass30_all_markers_breakdown.txt" 2>&1
python3 "$S/drc_near_macro.py" $C/drtH10/chk/all30.rpt "$MAC" $C/handoff/H4_axi3.pl > "$D/H10_pass30_power_shorts_vs_macros.txt" 2>&1
python3 "$S/drc_near_macro.py" $C/drtH10/chk/all30.rpt "$MAC" $C/handoff/H4_axi3.pl --all >> "$D/H10_pass30_power_shorts_vs_macros.txt" 2>&1
python3 "$S/drc_power_mod.py" $C/drtH10/chk/all30.rpt 341.3 16 50 2.8 > "$D/H10_power_shorts_mod_strap_grid.txt" 2>&1
cp $C/eco/obsA/nets_pwr430.txt "$D/H10_nets_with_power_shorts_430.txt"
head -600 $C/drtH10/chk/grid30/w_2140_340.rpt > "$D/H10_pass30_south_window_first600lines.rpt"
python3 "$S/guides_in_macros.py" $C/drtH10/route_clamped.guide "$MAC" $C/handoff/H4_axi3.pl -10 > "$D/H10_guides_in_macros_margin-10.txt" 2>&1
python3 "$S/guides_in_macros.py" $C/drtH10/route_clamped.guide "$MAC" $C/handoff/H4_axi3.pl 0 > "$D/H10_guides_in_macros_margin0.txt" 2>&1
cp $C/drtH10/chk/m4_pairs.txt "$D/H10_m4_pairs.txt"
grep -a "NET_MACRO_CROSS\|^PAIR" $C/drtH10/chk/net_macro_cross.log > "$D/H10_net_macro_cross.txt"
grep -a "^PWR" $C/drtH10/chk/pwr_south.log | awk '{print $2, $3, $4, $5, $6, "y", $8, "w", $10}' | sort | uniq -c | sort -rn > "$D/H10_power_shapes_south_window.txt"
python3 "$S/dens_window.py" $C/dens/H10_cts.txt 3600 3900 6200 5500 100 > "$D/H10_cpu_block_density_100um.txt" 2>&1
python3 "$S/drc_near_macro.py" $C/eco/obsA/obsA_drc.rpt "$MAC" $C/handoff/H4_axi3.pl --all > "$D/obsA_residue_vs_macros.txt" 2>&1
grep -a "ECO_OBS\|Number of violations" $C/eco/obsA/obsA.log > "$D/obsA_log_excerpt.txt"
for t in H10 H10m H10m3 H10m2; do
  [ -f "$C/chip$t/4_grt.log" ] && grep -a -A9 "GRT-0096" "$C/chip$t/4_grt.log" | grep -a -E "^Layer|^Metal|^TopMetal|^Total" > "$D/${t}_grt_table.txt"
done
[ -f $C/chipH10m3/route.guide ] && python3 "$S/guides_in_macros.py" $C/chipH10m3/route.guide "$MAC" $C/handoff/H4_axi3.pl -10 > "$D/H10m3_guides_in_macros.txt" 2>&1
[ -f $C/chipH10m2/route.guide ] && python3 "$S/guides_in_macros.py" $C/chipH10m2/route.guide "$MAC" $C/handoff/H4_axi3.pl -10 > "$D/H10m2_guides_in_macros.txt" 2>&1
L=/root/.claude/jobs/658ac326/tmp/pdk/sg13g2/sram_lef/RM_IHPSG13_2P_1024x32_c2_bm_bist.lef
{ grep -a "SIZE\|ORIGIN\|CLASS" "$L" | head -3; echo "--- PIN layers (count of LAYER lines per layer):"; awk '/^ *PIN /{p=$2} /^ *LAYER/{print $2}' "$L" | sort | uniq -c
  echo "--- OBS section:"; awk '/^ *OBS/{o=1} o{print} /END MACRO/{o=0}' "$L" | head -40
  echo "--- VDD! pin Metal4 rects (first 12):"; awk '/^ *PIN VDD!/{p=1} p&&/LAYER Metal4/{m=1} p&&m&&/RECT/{print; c++; if(c>=12) exit}' "$L"
  echo "--- VSS! pin Metal4 rects (first 12):"; awk '/^ *PIN VSS!/{p=1} p&&/LAYER Metal4/{m=1} p&&m&&/RECT/{print; c++; if(c>=12) exit}' "$L"
  echo "--- VDDARRAY! pin Metal4 rects (first 12):"; awk '/^ *PIN VDDARRAY!/{p=1} p&&/LAYER Metal4/{m=1} p&&m&&/RECT/{print; c++; if(c>=12) exit}' "$L"
} > "$D/RM_IHPSG13_2P_1024x32_lef_excerpt.txt" 2>&1
sed -n 1,40p "$S/../dgse/runs/cmos5l-01/pdn_c5l_sram_v2.tcl" > "$D/pdn_c5l_sram_v2_header.txt"
cp "$S/chip_grt.tcl" "$S/macro_obs.tcl" "$S/chip_mobs_grt.sh" "$S/eco_obs.tcl" "$S/guides_in_macros.py" "$S/net_macro_cross.tcl" "$S/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" "$D/"
cp "$MAC" $C/handoff/H4_axi3.pl $C/handoff/H11_cputags.pl $C/dpass/H10-corrslot_blockages.txt "$D/"
cp $C/H4b_vs_H10_floorplan.png "$D/" 2>/dev/null
python3 "$S/fp_blk_picture.py" "$MAC" "$D/H11_vs_H10_floorplan.png" "H10 and H11: same macros except the two CPU ibus-tag 64x22 (red arrows not drawn): H11 moves them from x 5634-6160 to x 3360-3886" "H10=$C/handoff/H4_axi3.pl:$C/dpass/H10-corrslot_blockages.txt" "H11=$C/handoff/H11_cputags.pl:$C/dpass/H10-corrslot_blockages.txt" > /dev/null 2>&1
awk '/2026-11-07 ..:.. UTC|2026-11-06 20:50 UTC/{p=1} p' "$S/../dgse/runs/NOTES.md" > "$D/NOTES_7Nov_excerpt.md"
ls "$D" | wc -l
