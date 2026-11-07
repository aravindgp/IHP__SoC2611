# Local relocation on a finished (post-CTS) checkpoint: every std cell whose centre lies in one of the BOX rects and
# whose name matches FILTER is shifted by (DX, DY) um to an explicit target, then the whole design is re-legalized
# (detailed_placement, nearest free sites from the TARGET, not from the old place).  Optional BLK rects become hard
# placement blockages before legalization (keeps the vacated region empty).
# env: IN_ODB OUT_ODB BOX ("x0 y0 x1 y1;...") DX DY [FILTER=*] [BLK=""] [MAXDISP="1500 1500"] [THREADS=8]
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
set blks [rects [expr {[info exists ::env(BLK)] ? $::env(BLK) : ""}] $dbu]
set filt [expr {[info exists ::env(FILTER)] ? $::env(FILTER) : "*"}]
set dx [expr {round($::env(DX) * $dbu)}]; set dy [expr {round($::env(DY) * $dbu)}]
set n 0
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
    incr n
}
puts "LOCAL_RELOCATE shifted $n cells by ($::env(DX), $::env(DY)) um (filter $filt)"
foreach r $blks {
    lassign $r x0 y0 x1 y1
    odb::dbBlockage_create $block $x0 $y0 $x1 $y1
}
set md [expr {[info exists ::env(MAXDISP)] ? $::env(MAXDISP) : "1500 1500"}]
set_placement_padding -global -left 1 -right 1
detailed_placement -max_displacement $md
check_placement -verbose
write_db $::env(OUT_ODB)
puts "LOCAL_RELOCATE done $::env(OUT_ODB)"
