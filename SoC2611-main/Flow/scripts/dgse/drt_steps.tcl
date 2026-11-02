# Resume detailed routing on a partially routed ODB at pass START of OpenROAD's own 65-pass schedule,
# instead of restarting the schedule at pass 0 (a plain detailed_route on a routed ODB re-runs passes
# 0-2 with the pass-0 initial-route set-up: the c7w32 chunk 2 went 40,965 -> 81,947).
#
# How (OpenROAD dcf3613, src/drt/src/dr/FlexDR.cpp strategy() + TritonRoute::stepDR):
#   1. detailed_route -single_step_dr : pin access + track assignment + FlexDR::init(), no passes.
#   2. START-1 no-op steps (RipUpMode DRC): the marker list is empty after init, so searchRepair()
#      returns at once and stepDR() only advances the pass counter (pass 0 set-up never runs).
#   3. one scan step at pass START-1: RipUpMode INCR (rips up only nets WITHOUT routing = none) with
#      mazeEndIter 0 -> no rerouting, every worker just DRC-checks its clip -> marker list rebuilt.
#   4. passes START..END with the schedule's own arguments (clip-size growth reset to 0).
#   5. drt::step_end -> DRC report + routing written to the db; write_db OUT.
# Checkpoints: a step session cannot write the db mid-session, so run it in sessions of a few passes
# (drt_steps.sh loops: OUT of one session is IN of the next with START advanced).
#
# env: STEP_IN STEP_OUT STEP_START (>=1) STEP_END (<=64) [STEP_THREADS=16] [STEP_DRC_RPT]
#      [STEP_ALL_AS_INCR=0]  1 = turn the schedule's RipUpMode ALL passes into INCR (main() does this
#                            when the design has FIXED nets)
#      [STEP_SNAPSHOT_DIR]   only for STEP_START=0 runs: plain continuous detailed_route that also writes
#                            drt_iter<N>.odb after every pass (OpenROAD's DRT "snapshot" debug hook)
proc env_or {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }

set in      $::env(STEP_IN)
set out     $::env(STEP_OUT)
set start   [env_or STEP_START 1]
set end     [env_or STEP_END 64]
set rpt     [env_or STEP_DRC_RPT [file rootname $out]_drc.rpt]
set all_inc [env_or STEP_ALL_AS_INCR 0]

read_db $in
set_thread_count [env_or STEP_THREADS 16]

# FlexDR strategy(): {size offset mazeEndIter drcCost markerCost fixedShapeCost decay ripup followGuide}
# costs in units of ROUTESHAPECOST (S=8) / MARKERCOST (M=32); ripup 0 DRC, 1 ALL, 2 NEARDRC, 3 INCR
set S 8; set M 32
set sched {
  {7  0  3  1  0   1 0.950 1 1} {7 -2  3  1  1   1 0.950 1 1} {7 -5  3  1  1   1 0.950 1 1}
  {7  0  8  1  1   2 0.950 0 0} {7 -1  8  1  1   2 0.950 0 0} {7 -2  8  1  1   2 0.950 0 0}
  {7 -3  8  1  1   2 0.950 0 0} {7 -4  8  1  1   2 0.950 0 0} {7 -5  8  1  1   2 0.950 0 0}
  {7 -6  8  1  1   2 0.950 0 0} {7  0  8  2  1   3 0.950 0 0} {7 -1  8  2  1   3 0.950 0 0}
  {7 -2  8  2  1   3 0.950 0 0} {7 -3  8  2  1   3 0.950 0 0} {7 -4  8  2  1   3 0.950 0 0}
  {7 -5  8  2  1   4 0.950 0 0} {7 -6  8  2  1   4 0.950 0 0} {7 -3  8  1  1   4 0.950 1 0}
  {7  0  8  4  1   4 0.950 0 0} {7 -1  8  4  1   4 0.950 0 0} {7 -2  8  4  1  10 0.950 0 0}
  {7 -3  8  4  1  10 0.950 0 0} {7 -4  8  4  1  10 0.950 0 0} {7 -5  8  1  1  10 0.950 2 0}
  {7 -6  8  4  1  10 0.950 0 0} {5 -2  8  1  1  10 0.950 1 0} {7  0  8  8  2  10 0.950 0 0}
  {7 -1  8  8  2  10 0.950 0 0} {7 -2  8  8  2  10 0.950 0 0} {7 -3  8  8  2  10 0.950 0 0}
  {7 -4  8  1  1  50 0.950 2 0} {7 -5  8  8  2  50 0.950 0 0} {7 -6  8  8  2  50 0.950 0 0}
  {3 -1  8  1  1  50 0.950 1 0} {7  0  8 16  4  50 0.950 0 0} {7 -1  8 16  4  50 0.950 0 0}
  {7 -2  8 16  4  50 0.950 0 0} {7 -3  8  1  1  50 0.950 2 0} {7 -4  8 16  4  50 0.950 0 0}
  {7 -5  8 16  4  50 0.950 0 0} {7 -6  8 16  4 100 0.990 0 0} {3 -2  8  1  1 100 0.990 1 0}
  {7  0 16 16  4 100 0.990 0 0} {7 -1 16 16  4 100 0.990 0 0} {7 -2 16  1  1 100 0.990 2 0}
  {7 -3 16 16  4 100 0.990 0 0} {7 -4 16 16  4 100 0.990 0 0} {7 -5 16 16  4 100 0.990 0 0}
  {7 -6 16 16  4 100 0.990 0 0} {3  0  8  1  1 100 0.990 1 0} {7  0 32 32  8 100 0.999 0 0}
  {7 -1 32  1  1 100 0.999 2 0} {7 -2 32 32  8 100 0.999 0 0} {7 -3 32 32  8 100 0.999 0 0}
  {7 -4 32 32  8 100 0.999 0 0} {7 -5 32 32  8 100 0.999 0 0} {7 -6 32 32  8 100 0.999 0 0}
  {3 -1  8  1  1 100 0.999 1 0} {7  0 64  1  1 100 0.999 2 0} {7 -1 64 64 16 100 0.999 0 0}
  {7 -2 64 64 16 100 0.999 0 0} {7 -3 64 64 16 100 0.999 0 0} {7 -4 64 64 16 100 0.999 0 0}
  {7 -5 64 64 16 100 0.999 0 0} {7 -6 64 64 16 100 0.999 0 0}
}
# pass 0 marker cost is 0 (the table has 1 for brevity of the list above)
proc step_args {i} {
  global sched S M all_inc
  lassign [lindex $sched $i] size off maze dc mc fc decay rip fg
  if {$i == 0} { set mc 0 }
  if {$rip == 1 && $all_inc} { set rip 3 }
  return [list $size $off $maze [expr {$dc * $S}] [expr {$mc * $M}] [expr {$fc * $S}] $decay $rip $fg]
}

if {$start == 0} {
  set snap [env_or STEP_SNAPSHOT_DIR ""]
  if {$snap ne ""} {
    file mkdir $snap
    detailed_route_debug -snapshot_dir $snap
    set_debug_level DRT snapshot 1
  }
  detailed_route -output_drc $rpt -droute_end_iter $end -verbose 1
} else {
  puts "DRT_STEPS resume $in at pass $start .. $end"
  detailed_route -single_step_dr -output_drc $rpt -verbose 1
  for {set i 0} {$i < $start - 1} {incr i} { drt::step_dr 7 0 8 $S $M [expr {2 * $S}] 0.95 0 0 }
  puts "DRT_STEPS pass counter at [expr {$start - 1}]; scan step (INCR, no reroute) to rebuild markers"
  lassign [step_args [expr {$start - 1}]] size off maze dc mc fc decay rip fg
  drt::step_dr $size $off 0 $dc $mc $fc $decay 3 0
  puts "DRT_STEPS scan markers [detailed_route_num_drvs]"
  for {set i $start} {$i <= $end} {incr i} {
    drt::step_dr {*}[step_args $i]
    set v [detailed_route_num_drvs]
    puts "DRT_STEPS pass $i violations $v"
    flush stdout
    if {$v == 0} { break }
  }
  drt::step_end
}
puts "DRT_STEPS final violations [detailed_route_num_drvs]"
write_db $out
puts "DRT_STEPS wrote $out"
