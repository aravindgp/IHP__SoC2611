# Dump REAL transformed ITerm pin positions (not the instance centre) for the specified nets.
# This matters for 237-703 um SRAMs: a centre-based approximation can relocate the
# load hundreds of micrometres from the actual A_DOUT/A_DIN pin.
# Output format remains compatible with pins_side.py:
#   PIN <net> <inst|PORT> <x_um> <y_um> <master>
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
        # getBBox on a dbITerm is the transformed geometry of its exact pin,
        # including R0/MX orientation. Fall back only for shapeless pins.
        set bb [$it getBBox]
        if {$bb eq "NULL"} { set bb [$inst getBBox] }
        puts [format "PIN %s %s %.1f %.1f %s" $nn [$inst getName] [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}] \
                  [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}] [[$inst getMaster] getName]]
    }
    foreach bt [$net getBTerms] {
        # Empty logical ports have no physical pin position and are temporarily
        # removed during detailed placement in the existing ECO flow.
        if {[llength [$bt getBPins]] == 0} { continue }
        set bb [$bt getBBox]
        puts [format "PIN %s PORT %.1f %.1f %s" $nn [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}] \
                  [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}] [$bt getName]]
    }
}
close $fh
puts "PINS_DONE"
