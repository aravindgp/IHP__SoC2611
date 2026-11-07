# List the special-wire (power) shapes of VDD/VSS-type nets that intersect a box, per layer, with their extents,
# plus the routing-track count the box has on each layer.  env: IN_ODB X0 Y0 X1 Y1 (um)
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set X0 [expr {$::env(X0) * $dbu}]; set Y0 [expr {$::env(Y0) * $dbu}]
set X1 [expr {$::env(X1) * $dbu}]; set Y1 [expr {$::env(Y1) * $dbu}]
set n 0
foreach net [$block getNets] {
    set st [$net getSigType]
    if {$st ne "POWER" && $st ne "GROUND"} { continue }
    foreach sw [$net getSWires] {
        foreach w [$sw getWires] {
            if {[$w isVia]} { continue }
            set bb $w
            if {[$bb xMax] < $X0 || [$bb xMin] > $X1 || [$bb yMax] < $Y0 || [$bb yMin] > $Y1} { continue }
            set lay [[$w getTechLayer] getName]
            set dir [expr {([$bb getDX] >= [$bb getDY]) ? "H" : "V"}]
            puts [format "PWR %-4s %-9s %s x %.1f..%.1f y %.1f..%.1f width %.2f" [$net getName] $lay $dir \
                  [expr {[$bb xMin] / double($dbu)}] [expr {[$bb xMax] / double($dbu)}] \
                  [expr {[$bb yMin] / double($dbu)}] [expr {[$bb yMax] / double($dbu)}] \
                  [expr {(($dir eq "H") ? [$bb getDY] : [$bb getDX]) / double($dbu)}]]
            incr n
        }
    }
}
puts "PWR_DONE $n power shapes in the box"
