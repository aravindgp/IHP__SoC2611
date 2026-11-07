# Replace the route guides stored in an ODB (what detailed_route uses when no -guide file is given) with a guide
# file, e.g. one rewritten by guide_clamp.py. env: IN_ODB OUT_ODB GUIDE
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set n 0
foreach net [$block getNets] {
    foreach g [$net getGuides] { odb::dbGuide_destroy $g; incr n }
}
puts "CHIP_LOAD_GUIDES removed $n db guides"
read_guides $::env(GUIDE)
set m 0
foreach net [$block getNets] { set m [expr {$m + [llength [$net getGuides]]}] }
puts "CHIP_LOAD_GUIDES db guides now $m"
write_db $::env(OUT_ODB)
puts "CHIP_LOAD_GUIDES wrote $::env(OUT_ODB)"
