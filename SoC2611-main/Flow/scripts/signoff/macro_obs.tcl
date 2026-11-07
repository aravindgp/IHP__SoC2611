# Routing obstructions over every macro outline (+ MARGIN um) on LAYERS, so that neither GRT nor DRT routes those
# layers inside the SRAM macros (the RM_IHPSG13 LEF leaves Metal4 open between its power-pin stripes: 7 Nov).
# env: IN_ODB OUT_ODB [LAYERS="Metal4"] [MARGIN=0]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set dbu [$block getDbUnitsPerMicron]
set layers [expr {[info exists ::env(LAYERS)] ? $::env(LAYERS) : "Metal4"}]
set margin [expr {round(([info exists ::env(MARGIN)] ? $::env(MARGIN) : 0) * $dbu)}]
set n 0
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock]} { continue }
    set bb [$inst getBBox]
    foreach ln $layers {
        set layer [$tech findLayer $ln]
        odb::dbObstruction_create $block $layer [expr {[$bb xMin] - $margin}] [expr {[$bb yMin] - $margin}] \
            [expr {[$bb xMax] + $margin}] [expr {[$bb yMax] + $margin}]
        incr n
    }
}
puts "MACRO_OBS $n obstructions on {$layers} over [expr {$n / [llength $layers]}] macros, margin [expr {$margin / double($dbu)}] um"
write_db $::env(OUT_ODB)
puts "MACRO_OBS done $::env(OUT_ODB)"
