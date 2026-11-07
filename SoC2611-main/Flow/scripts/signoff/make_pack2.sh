#!/bin/bash
# Assemble the routing-closure consultation pack (data for an outside review) under /workspace/chip_fp2/pack2.
set -u
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
P=/workspace/chip_fp2/pack2; D=$P/data; C=/workspace/chip_fp2
mkdir -p "$D"
: > "$D/drt_pass_histories.txt"
for t in H2 H3 H4 H4b H7 H9 H10 L1 H4r; do
  f=$C/drt$t/drt_chip.log
  [ -f "$f" ] || continue
  echo "== drt$t" >> "$D/drt_pass_histories.txt"
  grep -a "Number of violations" "$f" | grep -a -o "[0-9]*\.$" | tr -d . | nl -v0 | awk '{print "pass " $1 ": " $2}' >> "$D/drt_pass_histories.txt"
done
cp $C/drtH4b/chk/grid21.log "$D/H4b_grid21_600um.log"
cp $C/drtH4b/chk/zoom21.log "$D/H4b_zoom21_150um.log"
cp $C/drtH4b/chk/grid15.log "$D/H4b_grid15_600um.log"
cp $C/drtH4b/chk/grid10.log "$D/H4b_grid10_600um.log"
cp $C/drtH10/chk/grid12.log "$D/H10_grid12_600um.log"
cp $C/drtH10/chk/grid3.log "$D/H10_grid3_600um.log"
cp $C/drtH3/chk/grid5.log "$D/H3_grid5_600um.log" 2>/dev/null
for p in H4b_drt_pass21_map.png H4_drt_pass6_map.png H2_plan.png H2_wall_map.png; do cp "$C/$p" "$D/" 2>/dev/null; done
cp $C/handoff/macros_name_w_h_um.txt $C/handoff/H4_axi3.pl $C/handoff/H3_axi120.pl "$D/"
cp $C/dpass/H10-corrslot_blockages.txt "$D/H10_place_blockages.txt"
cp "$S/../dgse/runs/cmos5l-01/scripts/drt_steps.tcl" "$D/"
cp "$S/eco_plain.tcl" "$S/eco_move.tcl" "$S/local_relocate.tcl" "$S/run_chip_drt.sh" "$S/chip_grt.tcl" "$S/chip_io_obs.tcl" "$D/" 2>/dev/null
# wall window breakdown at pass 21 (types, layers, owners, top nets)
python3 "$S/drc_map.py" $C/drtH4b/chk/grid21/w_2740_1540.rpt H4b_pass21_wall_window > "$D/H4b_wall_window_pass21_breakdown.txt" 2>&1
grep -a -A1 "violation type: Short" $C/drtH4b/chk/grid21/w_2740_1540.rpt | grep -a "srcs:" | grep -a -o "net:[^ ]*" | sort | uniq -c | sort -rn | head -40 > "$D/H4b_wall_top_nets_pass21.txt"
head -400 $C/drtH4b/chk/grid21/w_2740_1540.rpt > "$D/H4b_wall_window_pass21_first400lines.rpt"
# cells and connectivity of the corridor / slot (from the H4 clock-tree checkpoint)
cp $C/dens/H4_slot_cells.log "$D/H4_slot_cells.txt" 2>/dev/null
grep -a SLOT_CONN $C/dens/slot_conn_dp.log $C/dens/slot_conn_hw.log > "$D/H4_corridor_slot_connectivity.txt" 2>/dev/null
# density grid around the corridor
python3 "$S/dens_window.py" $C/dens/H4_cts.txt 2700 1500 3500 2300 100 > "$D/H4_density_corridor_100um.txt" 2>&1
python3 "$S/dens_window.py" $C/dens/H4_cts.txt 3100 1900 5700 2200 100 > "$D/H4_density_band_east_100um.txt" 2>&1
# notes of 5-7 Nov
awk '/2026-11-05 23:10 UTC/{p=1} p' "$S/../dgse/runs/NOTES.md" > "$D/NOTES_5-7Nov_excerpt.md"
ls -la "$D" | wc -l
