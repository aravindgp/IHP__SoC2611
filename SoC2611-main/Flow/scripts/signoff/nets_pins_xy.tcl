# Dump the pin positions of the nets named in a "<count> <net> <macro>" pairs file (net_macro_cross input): one line
# per pin "PIN <net> <inst|PORT> <x_um> <y_um> <master>" so the pins can be binned against pocket/strip boxes.
# env: IN_ODB PAIRS_FILE
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set fh [open $::env(PAIRS_FILE) r]
array set seen {}
while {[gets $fh ln] >= 0} {
    set p [split [string trim $ln]]
    if {[llength $p] != 3} continue
    set nn [lindex $p 1]
    if {[info exists seen($nn)]} continue
    set seen($nn) 1
    set net [$block findNet $nn]
    if {$net eq "NULL"} { puts "MISSING $nn"; continue }
    foreach it [$net getITerms] {
        set inst [$it getInst]
        set bb [$inst getBBox]
        puts [format "PIN %s %s %.1f %.1f %s" $nn [$inst getName] [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}] \
                  [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}] [[$inst getMaster] getName]]
    }
    foreach bt [$net getBTerms] {
        set bb [$bt getBBox]
        puts [format "PIN %s PORT %.1f %.1f %s" $nn [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}] \
                  [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}] [$bt getName]]
    }
}
close $fh
puts "PINS_DONE"
