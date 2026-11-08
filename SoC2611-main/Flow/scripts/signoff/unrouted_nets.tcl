# List the multi-pin signal nets without a wire in a routed db (opens after an ECO), with pin count and whether the
# net is in NETS_FILE (one name per line) if given.  env: IN_ODB [NETS_FILE]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set listed [dict create]
if {[info exists ::env(NETS_FILE)] && $::env(NETS_FILE) ne ""} {
    set fh [open $::env(NETS_FILE) r]
    while {[gets $fh ln] >= 0} { set ln [string trim $ln]; if {$ln ne ""} { dict set listed $ln 1 } }
    close $fh
}
set n 0
foreach net [$block getNets] {
    if {[$net getSigType] ne "SIGNAL"} { continue }
    set its [$net getITerms]
    if {[$net getWire] ne "NULL" || [llength $its] <= 1} { continue }
    incr n
    set xs {}; set ys {}
    foreach it $its {
        set bb [[$it getInst] getBBox]
        lappend xs [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}]; lappend ys [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}]
    }
    puts [format "UNROUTED %s pins %d bbox %.0f,%.0f-%.0f,%.0f guides %d %s" [$net getName] [llength $its] \
              [tcl::mathfunc::min {*}$xs] [tcl::mathfunc::min {*}$ys] [tcl::mathfunc::max {*}$xs] [tcl::mathfunc::max {*}$ys] \
              [llength [$net getGuides]] [expr {[dict exists $listed [$net getName]] ? "LISTED" : "-"}]]
}
puts "UNROUTED total $n"
