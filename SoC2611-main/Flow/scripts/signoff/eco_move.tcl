# ECO cell move + re-route on a routed db: every std cell whose centre lies in a BOX rect (and matches FILTER) is
# shifted by (DX, DY) um, the design is re-legalized (detailed_placement, max displacement MAXDISP), the routing of
# every net touching a moved cell (plus the nets in NETS_FILE, if given) is deleted, and a plain detailed_route
# re-routes only those nets with everything else kept (END passes).  Writes OUT_ODB, a DRC report, snapshots.
# env: IN_ODB OUT_ODB BOX ("x0 y0 x1 y1;...") DX DY [FILTER=*] [MAXDISP="300 300"] [NETS_FILE] [END=3]
#      [THREADS=8] [SNAP_DIR] [DRC_RPT]
read_db $::env(IN_ODB)
set_thread_count [expr {[info exists ::env(THREADS)] ? $::env(THREADS) : 8}]
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
proc rects {s dbu} {
    set out {}
    foreach r [split $s ";"] {
        set r [string trim $r]
        if {$r eq ""} { continue }
        lassign $r x0 y0 x1 y1
        lappend out [list [expr {round($x0 * $dbu)}] [expr {round($y0 * $dbu)}] [expr {round($x1 * $dbu)}] [expr {round($y1 * $dbu)}]]
    }
    return $out
}
set boxes [rects $::env(BOX) $dbu]
set filt [expr {[info exists ::env(FILTER)] ? $::env(FILTER) : "*"}]
set dx [expr {round($::env(DX) * $dbu)}]; set dy [expr {round($::env(DY) * $dbu)}]
set moved {}
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isCore]} { continue }
    if {![string match $filt [$inst getName]]} { continue }
    set bb [$inst getBBox]
    set cx [expr {([$bb xMin] + [$bb xMax]) / 2}]; set cy [expr {([$bb yMin] + [$bb yMax]) / 2}]
    set hit 0
    foreach r $boxes {
        lassign $r x0 y0 x1 y1
        if {$cx >= $x0 && $cx < $x1 && $cy >= $y0 && $cy < $y1} { set hit 1; break }
    }
    if {!$hit} { continue }
    lassign [$inst getLocation] ix iy
    $inst setLocation [expr {$ix + $dx}] [expr {$iy + $dy}]
    $inst setPlacementStatus PLACED
    lappend moved $inst
}
puts "ECO_MOVE shifted [llength $moved] cells by ($::env(DX), $::env(DY)) um"
# nets touching moved cells
set touched [dict create]
foreach inst $moved {
    foreach it [$inst getITerms] {
        set net [$it getNet]
        if {$net ne "NULL" && [$net getSigType] eq "SIGNAL"} { dict set touched [$net getName] $net }
    }
}
if {[info exists ::env(NETS_FILE)] && $::env(NETS_FILE) ne ""} {
    set fh [open $::env(NETS_FILE) r]
    while {[gets $fh line] >= 0} {
        set name [string trim $line]
        if {$name eq ""} { continue }
        set net [$block findNet $name]
        if {$net ne "NULL"} { dict set touched $name $net }
    }
    close $fh
}
# legalize (padding as the engine: 1 site); every cell the legalizer displaces (moved or neighbour) gets its nets
# re-routed too, so no stale wire is left on a pin that moved.
set before [dict create]
foreach inst [$block getInsts] {
    if {[[$inst getMaster] isCore]} { dict set before [$inst getName] [$inst getLocation] }
}
set md [expr {[info exists ::env(MAXDISP)] ? $::env(MAXDISP) : "300 300"}]
# chip-level dbs carry pad BTerms without shapes (ports moved onto the pads); DPL refuses them (DPL-0386), so they
# are removed for the legalization and recreated with the same net / io type / signal type afterwards.
set removed {}
foreach bt [$block getBTerms] {
    if {[llength [$bt getBPins]] == 0} {
        lappend removed [list [$bt getName] [[$bt getNet] getName] [$bt getIoType] [$bt getSigType]]
        odb::dbBTerm_destroy $bt
    }
}
puts "ECO_MOVE shape-less BTerms removed for legalization: [llength $removed]"
set_placement_padding -global -left 1 -right 1
detailed_placement -max_displacement $md
check_placement -verbose
foreach r $removed {
    lassign $r bn nn io st
    set bt [odb::dbBTerm_create [$block findNet $nn] $bn]
    $bt setIoType $io
    $bt setSigType $st
}
puts "ECO_MOVE BTerms recreated: [llength $removed]"
set nshift 0
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isCore]} { continue }
    if {[dict get $before [$inst getName]] eq [$inst getLocation]} { continue }
    incr nshift
    foreach it [$inst getITerms] {
        set net [$it getNet]
        if {$net ne "NULL" && [$net getSigType] eq "SIGNAL"} { dict set touched [$net getName] $net }
    }
}
puts "ECO_MOVE cells displaced by the legalizer (moved + neighbours): $nshift"
set nd 0
dict for {name net} $touched {
    set w [$net getWire]
    if {$w ne "NULL"} { odb::dbWire_destroy $w; incr nd }
}
puts "ECO_MOVE routing deleted on $nd nets ([dict size $touched] touched)"
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
puts "ECO_MOVE unrouted multi-pin signal nets after: $unrouted"
write_db $::env(OUT_ODB)
puts "ECO_MOVE done $::env(OUT_ODB)"
