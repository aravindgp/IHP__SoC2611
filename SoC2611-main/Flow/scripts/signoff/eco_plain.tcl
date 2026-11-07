# ECO re-route with a plain continuous detailed_route on a routed db: optionally delete the routing of the nets in
# NETS_FILE, then detailed_route -droute_end_iter END.  Existing wires are kept (passes 0-2 take seconds on a routed
# db), unrouted nets are routed in pass 0, later passes repair markers at the restarted schedule's costs.
# env: IN_ODB OUT_ODB [NETS_FILE] [END=3] [THREADS=8] [DRC_RPT] [SNAP_DIR]
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
puts "ECO_PLAIN wires deleted on $n nets ($miss names not found)"
set rpt [expr {[info exists ::env(DRC_RPT)] ? $::env(DRC_RPT) : "[file rootname $::env(OUT_ODB)]_drc.rpt"}]
set end [expr {[info exists ::env(END)] ? $::env(END) : 3}]
if {[info exists ::env(SNAP_DIR)] && $::env(SNAP_DIR) ne ""} {
    file mkdir $::env(SNAP_DIR)
    detailed_route_debug -snapshot_dir $::env(SNAP_DIR)
    set_debug_level DRT snapshot 1
}
detailed_route -output_drc $rpt -droute_end_iter $end -verbose 1
set unrouted 0
foreach net [$block getNets] {
    if {[$net getSigType] ne "SIGNAL"} { continue }
    if {[$net getWire] eq "NULL" && [llength [$net getITerms]] > 1} { incr unrouted }
}
puts "ECO_PLAIN unrouted multi-pin signal nets after: $unrouted"
write_db $::env(OUT_ODB)
puts "ECO_PLAIN done $::env(OUT_ODB)"
