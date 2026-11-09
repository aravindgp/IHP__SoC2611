# For the instances listed in INSTS_FILE (one name per line), check that every connected signal/clock ITerm touches a
# shape of its net's wire (same layer, overlapping the pin's bbox, or a via whose bbox overlaps).  Reports the pins
# whose wire never reaches them: the opens a side-move ECO leaves when a moved cell's net is not re-routed.
# env: IN_ODB INSTS_FILE [OUT=open_pins.txt]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set fh [open $::env(INSTS_FILE) r]
set insts {}
while {[gets $fh ln] >= 0} {
    set ln [string trim $ln]
    if {$ln eq ""} continue
    set i [$block findInst $ln]
    if {$i ne "NULL"} { lappend insts $i }
}
close $fh
set out [expr {[info exists ::env(OUT)] ? $::env(OUT) : "open_pins.txt"}]
set fo [open $out w]
set nopen 0; set nchk 0; set nowire 0
foreach inst $insts {
    foreach it [$inst getITerms] {
        set net [$it getNet]
        if {$net eq "NULL"} continue
        if {[$net getSigType] in {POWER GROUND}} continue
        if {[llength [$net getITerms]] < 2 && [llength [$net getBTerms]] == 0} continue
        incr nchk
        set pb [$it getBBox]
        set w [$net getWire]
        if {$w eq "NULL"} { incr nowire; puts $fo "NOWIRE [$inst getName] [[$it getMTerm] getName] [$net getName]"; continue }
        # walk the wire with the decoder: a segment (between consecutive points on a path) or a via whose outline,
        # grown by the layer half-width, overlaps the pin's bbox counts as touching; an explicit ITERM record too
        set px0 [$pb xMin]; set py0 [$pb yMin]; set px1 [$pb xMax]; set py1 [$pb yMax]
        set hit 0
        set dec [odb::dbWireDecoder]
        $dec begin $w
        set hw 100; set prev ""
        while {1} {
            set op [$dec next]
            if {$op == 12} break
            if {$op == 0 || $op == 1 || $op == 2 || $op == 3} {
                set prev ""
                set ly [$dec getLayer]
                if {$ly ne "NULL"} { set hw [expr {[$ly getWidth] / 2}] }
                continue
            }
            if {$op == 4 || $op == 5} {
                set pt [$dec getPoint]
                set x [lindex $pt 0]; set y [lindex $pt 1]
                if {$prev ne ""} {
                    lassign $prev x0 y0
                    set sx0 [expr {min($x0, $x) - $hw}]; set sx1 [expr {max($x0, $x) + $hw}]
                    set sy0 [expr {min($y0, $y) - $hw}]; set sy1 [expr {max($y0, $y) + $hw}]
                } else {
                    set sx0 [expr {$x - $hw}]; set sx1 [expr {$x + $hw}]; set sy0 [expr {$y - $hw}]; set sy1 [expr {$y + $hw}]
                }
                if {!($sx1 <= $px0 || $sx0 >= $px1 || $sy1 <= $py0 || $sy0 >= $py1)} { set hit 1; break }
                set prev [list $x $y]
                continue
            }
            if {$op == 6 || $op == 7} {
                if {$prev ne ""} {
                    lassign $prev x y
                    set vh 300
                    if {!($x + $vh <= $px0 || $x - $vh >= $px1 || $y + $vh <= $py0 || $y - $vh >= $py1)} { set hit 1; break }
                }
                set ly [$dec getLayer]
                if {$ly ne "NULL"} { set hw [expr {[$ly getWidth] / 2}] }
                continue
            }
            if {$op == 9} {
                if {[$dec getITerm] eq $it} { set hit 1; break }
            }
        }
        if {!$hit} { incr nopen; puts $fo "OPEN [$inst getName] [[$it getMTerm] getName] [$net getName] sig=[$net getSigType]" }
    }
}
close $fo
puts "PIN_CONNECT insts=[llength $insts] pins_checked=$nchk open=$nopen no_wire=$nowire -> $out"
