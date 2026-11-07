# Instance locations in a window, for loc_diff_nets.py (pre/post legalisation). env: IN_ODB OUT_TXT [XMAX_UM=1200] [YMAX_UM=6600]
proc env_or {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set xmax [expr {int([env_or XMAX_UM 1200] * 1000)}]
set ymax [expr {int([env_or YMAX_UM 6600] * 1000)}]
set fh [open $::env(OUT_TXT) w]
foreach inst [$block getInsts] {
    set bb [$inst getBBox]
    if {[$bb xMin] > $xmax || [$bb yMin] > $ymax} { continue }
    lassign [$inst getLocation] x y
    puts $fh "[$inst getName] $x $y [$inst getOrient]"
}
close $fh
puts "DUMP_LOC done"
