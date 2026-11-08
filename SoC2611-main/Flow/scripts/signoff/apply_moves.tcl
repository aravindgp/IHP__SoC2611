# Apply a side-move plan (pins_side.py "MOVE <inst> <x> <y>" um) to a pre-route db (e.g. the engine's ck_cts.odb),
# legalize with MAXDISP, report the displacement of the moved cells, write OUT_ODB.  The global route then sees the
# cells on the majority side of their macro rows and has no reason to cross them.
# env: IN_ODB OUT_ODB MOVES_FILE [MAXDISP="250 40"]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set targets {}
set miss 0
set fh [open $::env(MOVES_FILE) r]
while {[gets $fh line] >= 0} {
    set p [split [string trim $line]]
    if {[lindex $p 0] ne "MOVE"} { continue }
    set inst [$block findInst [lindex $p 1]]
    if {$inst eq "NULL"} { incr miss; continue }
    set bb [$inst getBBox]
    set w [expr {[$bb xMax] - [$bb xMin]}]; set h [expr {[$bb yMax] - [$bb yMin]}]
    set cx [expr {round([lindex $p 2] * $dbu)}]; set cy [expr {round([lindex $p 3] * $dbu)}]
    $inst setLocation [expr {$cx - $w / 2}] [expr {$cy - $h / 2}]
    $inst setPlacementStatus PLACED
    lappend targets [list $inst $cx $cy]
}
close $fh
puts "APPLY_MOVES moved [llength $targets] cells ($miss names not found)"
set removed {}
foreach bt [$block getBTerms] {
    if {[llength [$bt getBPins]] == 0} {
        lappend removed [list [$bt getName] [[$bt getNet] getName] [$bt getIoType] [$bt getSigType]]
        odb::dbBTerm_destroy $bt
    }
}
set md [expr {[info exists ::env(MAXDISP)] ? $::env(MAXDISP) : "250 40"}]
set_placement_padding -global -left 1 -right 1
detailed_placement -max_displacement $md
check_placement -verbose
foreach r $removed {
    lassign $r bn nn io st
    set bt [odb::dbBTerm_create [$block findNet $nn] $bn]
    $bt setIoType $io
    $bt setSigType $st
}
set far 0
foreach t $targets {
    lassign $t inst cx cy
    set bb [$inst getBBox]
    set dy [expr {(([$bb yMin] + [$bb yMax]) / 2.0 - $cy) / $dbu}]
    if {abs($dy) > 15} { incr far }
}
puts "APPLY_MOVES cells more than 15 um from their target in y: $far of [llength $targets]"
write_db $::env(OUT_ODB)
puts "APPLY_MOVES done $::env(OUT_ODB)"
