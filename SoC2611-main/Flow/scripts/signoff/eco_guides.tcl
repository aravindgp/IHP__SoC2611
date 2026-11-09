# Re-route a net list along explicit guides: the nets' existing guides and wires are deleted, the boxes from
# GUIDES_FILE ("net layer x0 y0 x1 y1" in um, guide_channels.py) become their new guides, and a plain detailed_route
# (END passes, no global route) routes them inside those guides with everything else frozen.
# env: IN_ODB OUT_ODB GUIDES_FILE [END=3] [THREADS=8] [DRC_RPT]
read_db $::env(IN_ODB)
set_thread_count [expr {[info exists ::env(THREADS)] ? $::env(THREADS) : 8}]
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set dbu [$block getDbUnitsPerMicron]
set boxes [dict create]
set fh [open $::env(GUIDES_FILE) r]
while {[gets $fh ln] >= 0} {
    set p [split [string trim $ln]]
    if {[llength $p] != 6} continue
    dict lappend boxes [lindex $p 0] [lrange $p 1 5]
}
close $fh
set nn 0; set nb 0; set miss 0
dict for {name lst} $boxes {
    set net [$block findNet $name]
    if {$net eq "NULL"} { incr miss; puts "ECO_GUIDES missing net $name"; continue }
    foreach g [$net getGuides] { odb::dbGuide_destroy $g }
    set w [$net getWire]
    if {$w ne "NULL"} { odb::dbWire_destroy $w }
    foreach b $lst {
        lassign $b lname x0 y0 x1 y1
        set layer [$tech findLayer $lname]
        if {$layer eq "NULL"} continue
        set r [odb::Rect]
        $r init [expr {int($x0 * $dbu)}] [expr {int($y0 * $dbu)}] [expr {int($x1 * $dbu)}] [expr {int($y1 * $dbu)}]
        if {[catch {odb::dbGuide_create $net $layer $layer $r 0} err]} {
            if {[catch {odb::dbGuide_create $net $layer $layer $r} err2]} { error "dbGuide_create: $err / $err2" }
        }
        incr nb
    }
    incr nn
}
puts "ECO_GUIDES $nn nets re-guided with $nb boxes ($miss missing)"
set rpt [expr {[info exists ::env(DRC_RPT)] ? $::env(DRC_RPT) : "[file rootname $::env(OUT_ODB)]_drc.rpt"}]
set end [expr {[info exists ::env(END)] ? $::env(END) : 3}]
detailed_route -output_drc $rpt -droute_end_iter $end -verbose 1
set unrouted 0
foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} { continue }
    if {[$net getWire] eq "NULL" && [llength [$net getITerms]] > 1} { incr unrouted }
}
puts "ECO_GUIDES unrouted multi-pin signal nets after: $unrouted"
write_db $::env(OUT_ODB)
puts "ECO_GUIDES done $::env(OUT_ODB)"
