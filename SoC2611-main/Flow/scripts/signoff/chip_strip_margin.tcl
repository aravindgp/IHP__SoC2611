# Destroy the routing of the nets listed in NETS_TXT (def_margin_nets.py: routing outside the core box), so GRT/DRT
# re-route them inside the core. env: IN_ODB OUT_ODB NETS_TXT
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set fh [open $::env(NETS_TXT) r]
set names [split [string trim [read $fh]] "\n"]
close $fh
set n 0
set miss 0
foreach nm $names {
    set net [$block findNet $nm]
    if {$net eq "NULL"} { incr miss; continue }
    set w [$net getWire]
    if {$w eq "NULL"} { continue }
    odb::dbWire_destroy $w
    incr n
}
puts "CHIP_STRIP destroyed the routing of $n nets ([llength $names] listed, $miss not found)"
write_db $::env(OUT_ODB)
puts "CHIP_STRIP wrote $::env(OUT_ODB)"
