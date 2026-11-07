# Where do the cells inside a box connect to?  For the std cells whose centre is in X0 Y0 X1 Y1 (um) and whose name
# matches FILTER (glob, default *), count the other pins of their nets by region: inside the box, west of WX (um),
# east of EX (um), or between (the highway).  env: IN_ODB X0 Y0 X1 Y1 WX EX [FILTER=*]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set X0 [expr {$::env(X0) * $dbu}]; set Y0 [expr {$::env(Y0) * $dbu}]
set X1 [expr {$::env(X1) * $dbu}]; set Y1 [expr {$::env(Y1) * $dbu}]
set WX [expr {$::env(WX) * $dbu}]; set EX [expr {$::env(EX) * $dbu}]
set filt [expr {[info exists ::env(FILTER)] ? $::env(FILTER) : "*"}]
proc centre {inst} {
    set bb [$inst getBBox]
    return [list [expr {([$bb xMin] + [$bb xMax]) / 2}] [expr {([$bb yMin] + [$bb yMax]) / 2}]]
}
set sel {}
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isCore]} { continue }
    if {![string match $filt [$inst getName]]} { continue }
    lassign [centre $inst] cx cy
    if {$cx >= $X0 && $cx < $X1 && $cy >= $Y0 && $cy < $Y1} { lappend sel $inst }
}
array set cnt {inbox 0 west 0 highway 0 east 0 other 0 macro 0}
set nnets 0
set seen [dict create]
foreach inst $sel {
    foreach it [$inst getITerms] {
        set net [$it getNet]
        if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} { continue }
        if {[dict exists $seen [$net getName]]} { continue }
        dict set seen [$net getName] 1
        incr nnets
        foreach ot [$net getITerms] {
            set oi [$ot getInst]
            if {[[$oi getMaster] isBlock]} { incr cnt(macro); continue }
            lassign [centre $oi] ox oy
            if {$ox >= $X0 && $ox < $X1 && $oy >= $Y0 && $oy < $Y1} { incr cnt(inbox)
            } elseif {$ox < $WX} { incr cnt(west)
            } elseif {$ox < $EX} { incr cnt(highway)
            } elseif {$oy >= $Y0 - 400 * $dbu && $oy < $Y1 + 400 * $dbu} { incr cnt(east)
            } else { incr cnt(other) }
        }
    }
}
puts "SLOT_CONN cells [llength $sel] (filter $filt) nets $nnets: pins inbox $cnt(inbox) west(<$::env(WX)) $cnt(west) highway $cnt(highway) east(>$::env(EX), same y band) $cnt(east) elsewhere $cnt(other) macro $cnt(macro)"
