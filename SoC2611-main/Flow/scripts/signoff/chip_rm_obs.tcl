# Remove every routing obstruction (dbObstruction) from the block: GRT UNDERFLOWS the capacity of gcells that are
# already reduced (IO cells) when an obstruction is added on top, which made the IO band look free (3-4 Nov).
# GRT must therefore run WITHOUT the band obstructions; they are re-added for DRT (chip_io_obs.tcl). env: IN_ODB OUT_ODB
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set n 0
foreach o [$block getObstructions] { odb::dbObstruction_destroy $o; incr n }
puts "CHIP_RM_OBS removed $n obstructions"
write_db $::env(OUT_ODB)
puts "CHIP_RM_OBS wrote $::env(OUT_ODB)"
