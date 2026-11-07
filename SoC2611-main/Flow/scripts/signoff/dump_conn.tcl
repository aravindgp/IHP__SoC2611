# Connectivity for the hand floorplan: for every macro, how many of its net pins land in which logic group
# (hierarchy prefix, 4 levels), plus every BTerm (pad pin) position.  env: IN_ODB OUT_TXT
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set fh [open $::env(OUT_TXT) w]
proc grp {name} {
    set p [split $name /]
    return [join [lrange $p 0 [expr {[info exists ::env(GRP_DEPTH)] ? $::env(GRP_DEPTH) - 1 : 3}]] /]
}
foreach bt [$block getBTerms] {
    set bb [$bt getBBox]
    set n [$bt getNet]
    puts $fh "BTERM [$bt getName] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [expr {$n eq "NULL" ? "-" : [$n getName]}]"
}
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    if {![$m isBlock]} { continue }
    array unset cnt
    set npins 0
    foreach it [$inst getITerms] {
        set net [$it getNet]
        if {$net eq "NULL"} { continue }
        if {[$net getSigType] ne "SIGNAL"} { continue }
        incr npins
        foreach ot [$net getITerms] {
            set oi [$ot getInst]
            if {$oi eq $inst} { continue }
            set g [grp [$oi getName]]
            if {[[$oi getMaster] isBlock]} { set g "MACRO:$g" }
            if {[info exists cnt($g)]} { incr cnt($g) } else { set cnt($g) 1 }
        }
        foreach bt [$net getBTerms] {
            set g "PAD:[$bt getName]"
            if {[info exists cnt($g)]} { incr cnt($g) } else { set cnt($g) 1 }
        }
    }
    set bb [$inst getBBox]
    puts $fh "MACRO [$inst getName] [$m getName] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] pins=$npins"
    foreach {g c} [array get cnt] { puts $fh "  CONN $c $g" }
}
close $fh
puts "DUMP_CONN done"
