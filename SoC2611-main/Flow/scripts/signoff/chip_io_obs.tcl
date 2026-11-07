# Routing obstructions over the IO-cell band (pad ring) on the layers where the IO cells carry their supply rails as
# PINs (Metal3/Metal4/TopMetal1 over local y 7..178 um): GRT does not count those pin shapes as blockage and routed
# core nets over the IO cells -> DRT shorts with IOVDD/IOVSS/VDD/VSS (3 Nov run B pass 12: 63 % of all violations in
# the margin, 92 % of those on the west band). Metal2 and the innermost IO_PIN_KEEP um stay open for the pad pins.
# Optionally strips the routing of the nets listed in NETS_TXT (def_margin_nets.py) so they are re-routed.
# env: IN_ODB OUT_ODB [NETS_TXT] [IO_OFFSET=140] [IO_H=180] [IO_PIN_KEEP=2] [OBS_LAYERS="Metal3 Metal4 TopMetal1"]
proc env_or {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set tech [[ord::get_db] getTech]
set dbu [$tech getDbUnitsPerMicron]
set die [$block getDieArea]
set W [$die xMax]; set H [$die yMax]
set o [expr {int([env_or IO_OFFSET 140] * $dbu)}]
set i [expr {int(([env_or IO_OFFSET 140] + [env_or IO_H 180] - [env_or IO_PIN_KEEP 2]) * $dbu)}]
# four bands (corners included): west, east, south, north
set bands [list [list $o $o $i [expr {$H - $o}]] [list [expr {$W - $i}] $o [expr {$W - $o}] [expr {$H - $o}]] \
                [list $o $o [expr {$W - $o}] $i] [list $o [expr {$H - $i}] [expr {$W - $o}] [expr {$H - $o}]]]
set nobs 0
foreach ln [env_or OBS_LAYERS "Metal3 Metal4 TopMetal1"] {
    set l [$tech findLayer $ln]
    foreach bd $bands {
        lassign $bd x0 y0 x1 y1
        odb::dbObstruction_create $block $l $x0 $y0 $x1 $y1
        incr nobs
    }
}
puts "CHIP_IO_OBS $nobs obstructions on [env_or OBS_LAYERS {Metal3 Metal4 TopMetal1}], band [expr {$o/double($dbu)}]..[expr {$i/double($dbu)}] um from each die edge"
if {[env_or NETS_TXT ""] ne ""} {
    set fh [open $::env(NETS_TXT) r]
    set names [split [string trim [read $fh]] "\n"]
    close $fh
    set n 0
    foreach nm $names {
        set net [$block findNet $nm]
        if {$net eq "NULL"} { continue }
        set w [$net getWire]
        if {$w eq "NULL"} { continue }
        odb::dbWire_destroy $w
        incr n
    }
    puts "CHIP_IO_OBS stripped the routing of $n nets ([llength $names] listed)"
}
write_db $::env(OUT_ODB)
puts "CHIP_IO_OBS wrote $::env(OUT_ODB)"
