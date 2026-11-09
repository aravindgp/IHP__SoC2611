# Local floorplan ECO on a routed db: shift macros (and listed standard cells) by (dx, dy) um, move their Metal2/Metal4
# routing obstructions with them, re-legalize, regenerate the guides of every net touching a displaced instance by an
# incremental global route, delete those nets' wires and re-route them with a plain detailed_route (END passes).
# SHIFT_FILE lines: "<inst> <dx_um> <dy_um>".  Extra nets (EXTRA_NETS, one per line) are re-routed as well.
# env: IN_ODB OUT_ODB SHIFT_FILE [EXTRA_NETS] [MAXDISP="250 40"] [END=3] [THREADS=8] [DRC_RPT]
read_db $::env(IN_ODB)
set_thread_count [expr {[info exists ::env(THREADS)] ? $::env(THREADS) : 8}]
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set_global_routing_layer_adjustment Metal2-TopMetal1 0.05
set_routing_layers -signal Metal2-TopMetal1
global_route -start_incremental
set before [dict create]
foreach inst [$block getInsts] { dict set before [$inst getName] [$inst getLocation] }
set shifted {}
set fh [open $::env(SHIFT_FILE) r]
while {[gets $fh ln] >= 0} {
    set p [split [string trim $ln]]
    if {[llength $p] != 3} continue
    set inst [$block findInst [lindex $p 0]]
    if {$inst eq "NULL"} { puts "ECO_SHIFT missing [lindex $p 0]"; continue }
    set dx [expr {round([lindex $p 1] * $dbu)}]; set dy [expr {round([lindex $p 2] * $dbu)}]
    set bb [$inst getBBox]
    set old [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    lassign [$inst getLocation] x y
    set isblk [[$inst getMaster] isBlock]
    if {$isblk} { $inst setPlacementStatus PLACED }
    $inst setLocation [expr {$x + $dx}] [expr {$y + $dy}]
    if {$isblk} {
        # move the routing obstructions that lie inside the macro's old outline
        set nmv 0
        foreach o [$block getObstructions] {
            set ob [$o getBBox]
            if {[$ob xMin] >= [lindex $old 0] - 1 && [$ob xMax] <= [lindex $old 2] + 1 && [$ob yMin] >= [lindex $old 1] - 1 && [$ob yMax] <= [lindex $old 3] + 1} {
                set layer [$ob getTechLayer]
                odb::dbObstruction_create $block $layer [expr {[$ob xMin] + $dx}] [expr {[$ob yMin] + $dy}] [expr {[$ob xMax] + $dx}] [expr {[$ob yMax] + $dy}]
                odb::dbObstruction_destroy $o
                incr nmv
            }
        }
        $inst setPlacementStatus FIRM
        puts "ECO_SHIFT macro [$inst getName] by ($dx,$dy) dbu, obstructions moved: $nmv"
    } else {
        $inst setPlacementStatus PLACED
    }
    lappend shifted $inst
}
close $fh
# standard cells left under a shifted macro's new outline (plus 2 um) move with it
set npush 0
foreach m $shifted {
    if {![[$m getMaster] isBlock]} continue
    set mb [$m getBBox]
    set mx0 [expr {[$mb xMin] - 2000}]; set my0 [expr {[$mb yMin] - 2000}]; set mx1 [expr {[$mb xMax] + 2000}]; set my1 [expr {[$mb yMax] + 2000}]
    set sh [dict create]
    foreach i $shifted { dict set sh [$i getName] 1 }
    foreach inst [$block getInsts] {
        if {![[$inst getMaster] isCore] || [dict exists $sh [$inst getName]]} continue
        set b [$inst getBBox]
        if {[$b xMax] <= $mx0 || [$b xMin] >= $mx1 || [$b yMax] <= $my0 || [$b yMin] >= $my1} continue
        lassign [$inst getLocation] x y
        $inst setLocation $x [expr {$y + ($my1 - $my0 - 4000) + 2000}]
        $inst setPlacementStatus PLACED
        lappend shifted $inst; incr npush
    }
}
puts "ECO_SHIFT instances shifted: [llength $shifted] (cells pushed out from under the macros: $npush)"
set md [expr {[info exists ::env(MAXDISP)] ? $::env(MAXDISP) : "250 40"}]
set removed {}
foreach bt [$block getBTerms] {
    if {[llength [$bt getBPins]] == 0} {
        lappend removed [list [$bt getName] [[$bt getNet] getName] [$bt getIoType] [$bt getSigType]]
        odb::dbBTerm_destroy $bt
    }
}
set_placement_padding -global -left 1 -right 1
detailed_placement -max_displacement $md
check_placement -verbose
foreach r $removed {
    lassign $r bn nn io st
    set bt [odb::dbBTerm_create [$block findNet $nn] $bn]
    $bt setIoType $io
    $bt setSigType $st
}
set touched [dict create]
set nshift 0
foreach inst [$block getInsts] {
    if {[dict get $before [$inst getName]] eq [$inst getLocation]} { continue }
    incr nshift
    foreach it [$inst getITerms] {
        set net [$it getNet]
        if {$net ne "NULL" && [$net getSigType] ni {POWER GROUND}} { dict set touched [$net getName] $net }
    }
}
puts "ECO_SHIFT instances displaced (shifted + legalizer): $nshift, nets touched: [dict size $touched]"
if {[info exists ::env(EXTRA_NETS)] && $::env(EXTRA_NETS) ne ""} {
    set nx 0
    set fh [open $::env(EXTRA_NETS) r]
    while {[gets $fh ln] >= 0} {
        set p [split [string trim $ln]]
        set name [expr {[llength $p] == 3 ? [lindex $p 1] : [lindex $p 0]}]
        if {$name eq "" || [dict exists $touched $name]} continue
        set n [$block findNet $name]
        if {$n eq "NULL" || [$n getSigType] in {POWER GROUND}} continue
        set its [$n getITerms]
        if {[llength $its] == 0} continue
        set it [lindex $its 0]
        set modnet [$it getModNet]
        $it disconnect
        if {$modnet ne "NULL"} { $it connect $n $modnet } else { $it connect $n }
        dict set touched $name $n
        incr nx
    }
    close $fh
    puts "ECO_SHIFT extra nets added: $nx"
}
set nd 0
dict for {name net} $touched {
    set w [$net getWire]
    if {$w ne "NULL"} { odb::dbWire_destroy $w; incr nd }
}
puts "ECO_SHIFT routing deleted on $nd nets"
global_route -end_incremental -allow_congestion
puts "ECO_SHIFT incremental global route done"
set rpt [expr {[info exists ::env(DRC_RPT)] ? $::env(DRC_RPT) : "[file rootname $::env(OUT_ODB)]_drc.rpt"}]
set end [expr {[info exists ::env(END)] ? $::env(END) : 3}]
detailed_route -output_drc $rpt -droute_end_iter $end -verbose 1
set unrouted 0
foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} { continue }
    if {[$net getWire] eq "NULL" && [llength [$net getITerms]] > 1} { incr unrouted }
}
puts "ECO_SHIFT unrouted multi-pin signal nets after: $unrouted"
write_db $::env(OUT_ODB)
puts "ECO_SHIFT done $::env(OUT_ODB)"
