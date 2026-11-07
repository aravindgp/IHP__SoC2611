# ECO with routing obstructions: add routing obstructions on OBS_LAYERS over every macro outline (+ MARGIN um),
# delete the routing of the nets in NETS_FILE, then run a plain detailed_route for END passes (existing wires of the
# other nets are kept; wires that now overlap an obstruction are repaired by the router).  Writes OUT_ODB.
# env: IN_ODB OUT_ODB NETS_FILE [OBS_LAYERS="Metal4"] [MARGIN=0] [END=5] [THREADS=8] [SNAP_DIR] [DRC_RPT]
read_db $::env(IN_ODB)
set_thread_count [expr {[info exists ::env(THREADS)] ? $::env(THREADS) : 8}]
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set dbu [$block getDbUnitsPerMicron]
set layers [expr {[info exists ::env(OBS_LAYERS)] ? $::env(OBS_LAYERS) : "Metal4"}]
set margin [expr {round(([info exists ::env(MARGIN)] ? $::env(MARGIN) : 0) * $dbu)}]
set nobs 0
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock]} { continue }
    set bb [$inst getBBox]
    foreach ln $layers {
        set layer [$tech findLayer $ln]
        odb::dbObstruction_create $block $layer [expr {[$bb xMin] - $margin}] [expr {[$bb yMin] - $margin}] \
            [expr {[$bb xMax] + $margin}] [expr {[$bb yMax] + $margin}]
        incr nobs
    }
}
puts "ECO_OBS $nobs routing obstructions created on {$layers} over the macros (margin [expr {$margin / double($dbu)}] um)"
set n 0; set miss 0
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
puts "ECO_OBS wires deleted on $n nets ($miss names not found)"
set rpt [expr {[info exists ::env(DRC_RPT)] ? $::env(DRC_RPT) : "[file rootname $::env(OUT_ODB)]_drc.rpt"}]
set end [expr {[info exists ::env(END)] ? $::env(END) : 5}]
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
puts "ECO_OBS unrouted multi-pin signal nets after: $unrouted"
write_db $::env(OUT_ODB)
puts "ECO_OBS done $::env(OUT_ODB)"
