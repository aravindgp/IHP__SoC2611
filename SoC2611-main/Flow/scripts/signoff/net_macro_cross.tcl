# For (net, macro) pairs whose global-route guides run on Metal4 inside the macro: does the net connect to that
# macro's own pins, and where do its other pins lie relative to the macro (north/south/west/east/inside the x-span)?
# env: IN_ODB PAIRS_FILE (lines: "<count> <net> <macro>")   prints one line per pair + a summary
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
array set tot {own 0 other 0}
array set side {N 0 S 0 both 0 none 0}
set fh [open $::env(PAIRS_FILE) r]
set lines 0
while {[gets $fh line] >= 0} {
    set p [split [string trim $line]]
    if {[llength $p] < 3} { continue }
    lassign $p cnt nn mn
    set net [$block findNet $nn]; set mi [$block findInst $mn]
    if {$net eq "NULL" || $mi eq "NULL"} { continue }
    incr lines
    set mb [$mi getBBox]
    set own 0; set n 0; set s 0
    foreach it [$net getITerms] {
        set inst [$it getInst]
        if {$inst eq $mi} { set own 1; continue }
        set bb [$inst getBBox]
        set cy [expr {([$bb yMin] + [$bb yMax]) / 2}]
        if {$cy > [$mb yMax]} { incr n } elseif {$cy < [$mb yMin]} { incr s }
    }
    if {$own} { incr tot(own) } else { incr tot(other) }
    if {$n && $s} { incr side(both) } elseif {$n} { incr side(N) } elseif {$s} { incr side(S) } else { incr side(none) }
    puts [format "PAIR m4boxes %s own %d north %d south %d  %s  %s" $cnt $own $n $s [string range $nn end-60 end] [string range $mn end-50 end]]
}
close $fh
puts "NET_MACRO_CROSS pairs $lines: net connects to the crossed macro: $tot(own), does not: $tot(other); other pins north only $side(N), south only $side(S), both $side(both), neither $side(none)"
