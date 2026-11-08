# Dry run of the side-move legalization: apply MOVES_FILE, legalize with MAXDISP, print per moved cell the target,
# the legalized location and the displacement from the target (um).  No routing, no write.
# env: IN_ODB MOVES_FILE [MAXDISP="300 300"]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set targets {}
set fh [open $::env(MOVES_FILE) r]
while {[gets $fh line] >= 0} {
    set p [split [string trim $line]]
    if {[lindex $p 0] ne "MOVE"} { continue }
    set inst [$block findInst [lindex $p 1]]
    if {$inst eq "NULL"} { continue }
    set bb [$inst getBBox]
    set w [expr {[$bb xMax] - [$bb xMin]}]; set h [expr {[$bb yMax] - [$bb yMin]}]
    set cx [expr {round([lindex $p 2] * $dbu)}]; set cy [expr {round([lindex $p 3] * $dbu)}]
    $inst setLocation [expr {$cx - $w / 2}] [expr {$cy - $h / 2}]
    $inst setPlacementStatus PLACED
    lappend targets [list $inst $cx $cy]
}
close $fh
foreach bt [$block getBTerms] { if {[llength [$bt getBPins]] == 0} { odb::dbBTerm_destroy $bt } }
set md [expr {[info exists ::env(MAXDISP)] ? $::env(MAXDISP) : "300 300"}]
set_placement_padding -global -left 1 -right 1
detailed_placement -max_displacement $md
check_placement -verbose
set far 0
foreach t $targets {
    lassign $t inst cx cy
    set bb [$inst getBBox]
    set fx [expr {([$bb xMin] + [$bb xMax]) / 2.0}]; set fy [expr {([$bb yMin] + [$bb yMax]) / 2.0}]
    set dx [expr {($fx - $cx) / $dbu}]; set dy [expr {($fy - $cy) / $dbu}]
    if {abs($dy) > 15 || abs($dx) > 60} { incr far }
    puts [format "SIDECHK %s target %.1f,%.1f final %.1f,%.1f d %.1f,%.1f" [$inst getName] [expr {$cx / double($dbu)}] [expr {$cy / double($dbu)}] \
              [expr {$fx / $dbu}] [expr {$fy / $dbu}] $dx $dy]
}
puts "SIDECHK far from target (|dy|>15 or |dx|>60): $far of [llength $targets]"
