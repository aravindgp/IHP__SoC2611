# Summarise DRT markers stored in an ODB (drt snapshot): by category/type and by region (core vs pad-ring margin)
# env: IN_ODB  [CORE_LO=340] [CORE_HI=6260] (um)
proc env_or {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set lo [expr {[env_or CORE_LO 340] * $dbu}]
set hi [expr {[env_or CORE_HI 6260] * $dbu}]
array set cnt {}
array set reg {}
array set lay {}
proc walk {cat path} {
    upvar cnt cnt reg reg lay lay lo lo hi hi
    foreach m [$cat getMarkers] {
        set bb [$m getBBox]
        set cx [expr {([$bb xMin] + [$bb xMax]) / 2}]
        set cy [expr {([$bb yMin] + [$bb yMax]) / 2}]
        set r [expr {($cx >= $lo && $cx < $hi && $cy >= $lo && $cy < $hi) ? "core" : "margin"}]
        incr cnt($path)
        incr reg($r)
        set l [$m getTechLayer]
        set ln [expr {$l eq "NULL" ? "-" : [$l getName]}]
        incr lay($r/$ln)
    }
    foreach sub [$cat getMarkerCategories] { walk $sub "$path/[$sub getName]" }
}
foreach top [$block getMarkerCategories] { walk $top [$top getName] }
puts "MARKERS by type:"
foreach k [lsort [array names cnt]] { puts [format "  %-60s %8d" $k $cnt($k)] }
puts "MARKERS by region:"
foreach k [lsort [array names reg]] { puts [format "  %-10s %8d" $k $reg($k)] }
puts "MARKERS by region/layer:"
foreach k [lsort [array names lay]] { puts [format "  %-24s %8d" $k $lay($k)] }
