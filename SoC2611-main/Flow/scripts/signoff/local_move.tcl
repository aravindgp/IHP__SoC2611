# Local placement fix on a finished (post-CTS) checkpoint: add hard placement blockages and re-legalize so the cells
# inside them move to the nearest free sites; everything else stays.  Same padding / displacement as the engine's
# post-CTS detailed_placement (cell_pad 1, dpl_max_disp 1500 1500).
# env: IN_ODB OUT_ODB BLK ("x0 y0 x1 y1;..." um) [MAXDISP="1500 1500"] [THREADS=8]
read_db $::env(IN_ODB)
set_thread_count [expr {[info exists ::env(THREADS)] ? $::env(THREADS) : 8}]
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set rects {}
foreach r [split $::env(BLK) ";"] {
    set r [string trim $r]
    if {$r eq ""} { continue }
    lassign $r x0 y0 x1 y1
    lappend rects [list [expr {round($x0 * $dbu)}] [expr {round($y0 * $dbu)}] [expr {round($x1 * $dbu)}] [expr {round($y1 * $dbu)}]]
}
proc count_in {block rects} {
    set n 0
    foreach inst [$block getInsts] {
        if {![[$inst getMaster] isCore]} { continue }
        set bb [$inst getBBox]
        set cx [expr {([$bb xMin] + [$bb xMax]) / 2}]; set cy [expr {([$bb yMin] + [$bb yMax]) / 2}]
        foreach r $rects {
            lassign $r x0 y0 x1 y1
            if {$cx >= $x0 && $cx < $x1 && $cy >= $y0 && $cy < $y1} { incr n; break }
        }
    }
    return $n
}
puts "LOCAL_MOVE cells inside the blockages before: [count_in $block $rects]"
foreach r $rects {
    lassign $r x0 y0 x1 y1
    odb::dbBlockage_create $block $x0 $y0 $x1 $y1
}
set md [expr {[info exists ::env(MAXDISP)] ? $::env(MAXDISP) : "1500 1500"}]
set_placement_padding -global -left 1 -right 1
detailed_placement -max_displacement $md
check_placement -verbose
puts "LOCAL_MOVE cells inside the blockages after: [count_in $block $rects]"
write_db $::env(OUT_ODB)
puts "LOCAL_MOVE done $::env(OUT_ODB)"
