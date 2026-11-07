# ECO re-route on a routed db (snapshot or session output): optionally delete the detailed routing of the nets listed
# in NETS_FILE, rebuild the DRC markers in the db with drt::check_drc (snapshot dbs carry none, and a DRT step session
# only repairs what the stored markers point at), then run a DRT step session resumed at pass START..END so that the
# marked regions are repaired and unrouted nets are routed, with everything else kept.  Writes OUT_ODB + DRC report.
# env: IN_ODB OUT_ODB [NETS_FILE] [START=16] [END=16] [THREADS=8] [DRC_RPT] [NO_CHECK=0]
read_db $::env(IN_ODB)
set_thread_count [expr {[info exists ::env(THREADS)] ? $::env(THREADS) : 8}]
set block [ord::get_db_block]
set n 0; set miss 0
if {[info exists ::env(NETS_FILE)] && $::env(NETS_FILE) ne ""} {
    set fh [open $::env(NETS_FILE) r]
    while {[gets $fh line] >= 0} {
        set name [string trim $line]
        if {$name eq ""} { continue }
        set net [$block findNet $name]
        if {$net eq "NULL"} { incr miss; continue }
        set w [$net getWire]
        if {$w ne "NULL"} { odb::dbWire_destroy $w; incr n }
    }
    close $fh
}
puts "ECO_REROUTE wires deleted on $n nets ($miss names not found)"
proc count_markers {block} {
    set t 0
    foreach c [$block getMarkerCategories] {
        foreach s [$c getMarkerCategories] { set t [expr {$t + [llength [$s getMarkers]]}] }
        set t [expr {$t + [llength [$c getMarkers]]}]
    }
    return $t
}
puts "ECO_REROUTE db markers before check: [count_markers $block]"
set rpt [expr {[info exists ::env(DRC_RPT)] ? $::env(DRC_RPT) : "[file rootname $::env(OUT_ODB)]_drc.rpt"}]
if {!([info exists ::env(NO_CHECK)] && $::env(NO_CHECK) eq "1")} {
    set die [$block getDieArea]
    drt::check_drc -box [list [$die xMin] [$die yMin] [$die xMax] [$die yMax]] -output_file [file rootname $rpt]_before.rpt
    puts "ECO_REROUTE db markers after check_drc: [count_markers $block]"
}
set start [expr {[info exists ::env(START)] ? $::env(START) : 16}]
set end [expr {[info exists ::env(END)] ? $::env(END) : 16}]
# FlexDR::strategy() units (OpenROAD dcf3613): ROUTESHAPECOST S=8, MARKERCOST M=32; ripup 0 DRC, 1 ALL, 3 INCR.
set S 8; set M 32
detailed_route -single_step_dr -output_drc $rpt -verbose 1
puts "ECO_REROUTE db markers after init: [count_markers $block]"
for {set i 0} {$i < $start - 1} {incr i} { drt::step_dr 7 0 8 $S $M [expr {2 * $S}] 0.95 0 0 }
puts "ECO_REROUTE pass counter at [expr {$start - 1}]; INCR step (routes unrouted nets), then DRC passes $start..$end"
drt::step_dr 7 -6 8 [expr {2 * $S}] [expr {1 * $M}] [expr {4 * $S}] 0.95 3 0
puts "ECO_REROUTE after INCR: markers [detailed_route_num_drvs]"
for {set i $start} {$i <= $end} {incr i} {
    drt::step_dr 7 -6 8 [expr {2 * $S}] [expr {1 * $M}] [expr {4 * $S}] 0.95 0 0
    puts "ECO_REROUTE pass $i violations [detailed_route_num_drvs]"
}
drt::step_end
puts "ECO_REROUTE final violations [detailed_route_num_drvs]"
set unrouted 0
foreach net [$block getNets] {
    if {[$net getSigType] ne "SIGNAL"} { continue }
    if {[$net getWire] eq "NULL" && [llength [$net getITerms]] > 1} { incr unrouted }
}
puts "ECO_REROUTE unrouted multi-pin signal nets after: $unrouted"
write_db $::env(OUT_ODB)
puts "ECO_REROUTE done $::env(OUT_ODB)"
