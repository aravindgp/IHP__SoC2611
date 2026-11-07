# Std-cell count and area per hierarchy group (depth GRP_DEPTH, default 4; PCORE instances keep depth 6).
# env: IN_ODB OUT_TXT.  Output lines: <group> <count> <area_um2>
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set d [expr {[info exists ::env(GRP_DEPTH)] ? $::env(GRP_DEPTH) - 1 : 3}]
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    if {![$m isCore]} { continue }
    set p [split [$inst getName] /]
    set g [join [lrange $p 0 $d] /]
    if {[regexp {gen1_pcore_i} [$inst getName]]} { set g [join [lrange $p 0 5] /] }
    set a [expr {[$m getWidth] * [$m getHeight] / 1e6}]
    if {[info exists area($g)]} { set area($g) [expr {$area($g) + $a}]; incr n($g) } else { set area($g) $a; set n($g) 1 }
}
set fh [open $::env(OUT_TXT) w]
foreach g [array names area] { puts $fh "$g $n($g) [format %.1f $area($g)]" }
close $fh
puts "DUMP_CELLGROUPS done"
