# Count nets with routing guides, nets with wires, and unrouted multi-pin signal nets in a db.  env: IN_ODB
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set ng 0; set nw 0; set nu 0; set ns 0
foreach net [$block getNets] {
    if {[$net getSigType] ne "SIGNAL"} { continue }
    incr ns
    if {[llength [$net getGuides]] > 0} { incr ng }
    if {[$net getWire] ne "NULL"} { incr nw } elseif {[llength [$net getITerms]] > 1} { incr nu }
}
puts "COUNT_GUIDES $::env(IN_ODB): signal nets $ns, with guides $ng, with wires $nw, unrouted multi-pin $nu"
