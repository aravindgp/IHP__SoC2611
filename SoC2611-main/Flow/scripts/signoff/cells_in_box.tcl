# Which logic sits in a box?  Counts std cells whose centre lies in X0 Y0 X1 Y1 (um) grouped by the first DEPTH
# hierarchy levels of the instance name, with their area.  env: IN_ODB X0 Y0 X1 Y1 [DEPTH=4]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set X0 [expr {$::env(X0) * $dbu}]; set Y0 [expr {$::env(Y0) * $dbu}]
set X1 [expr {$::env(X1) * $dbu}]; set Y1 [expr {$::env(Y1) * $dbu}]
set depth [expr {[info exists ::env(DEPTH)] ? $::env(DEPTH) : 4}]
array set cnt {}
array set area {}
set n 0
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    if {![$m isCore]} { continue }
    set bb [$inst getBBox]
    set cx [expr {([$bb xMin] + [$bb xMax]) / 2}]
    set cy [expr {([$bb yMin] + [$bb yMax]) / 2}]
    if {$cx < $X0 || $cx >= $X1 || $cy < $Y0 || $cy >= $Y1} { continue }
    set parts [split [$inst getName] "/"]
    set key [join [lrange $parts 0 [expr {$depth - 1}]] "/"]
    if {![info exists cnt($key)]} { set cnt($key) 0; set area($key) 0.0 }
    incr cnt($key)
    set area($key) [expr {$area($key) + double([$bb getDX]) * [$bb getDY] / $dbu / $dbu}]
    incr n
}
puts "CELLS_IN_BOX $::env(X0) $::env(Y0) $::env(X1) $::env(Y1): $n cells"
set rows {}
foreach k [array names cnt] { lappend rows [list $cnt($k) $area($k) $k] }
foreach r [lrange [lsort -integer -decreasing -index 0 $rows] 0 24] {
    puts [format "  %7d cells %9.0f um2  %s" [lindex $r 0] [lindex $r 1] [lindex $r 2]]
}
