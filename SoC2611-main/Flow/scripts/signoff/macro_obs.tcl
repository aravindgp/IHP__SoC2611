# Routing obstructions over every macro outline (+ MARGIN um) on LAYERS, so that neither GRT nor DRT routes those
# layers inside the SRAM macros (the RM_IHPSG13 LEF leaves Metal4 open between its power-pin stripes: 7 Nov).
# PIN_KEEP (um, default 0): on the layers in PIN_LAYERS (default Metal2) the obstruction stops PIN_KEEP um short of
# the macro's pin edge (south for R0/MY, north for MX/R180; the RM_IHPSG13 signal pins reach 0.26 um into the macro)
# so the pins stay accessible while the rest of the macro interior is blocked (8 Nov: the abstracts leave Metal2 free
# inside the macros and the global router routes crossing nets through them on Metal2).
# env: IN_ODB OUT_ODB [LAYERS="Metal4"] [MARGIN=0] [PIN_KEEP=0] [PIN_LAYERS="Metal2"]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set dbu [$block getDbUnitsPerMicron]
set layers [expr {[info exists ::env(LAYERS)] ? $::env(LAYERS) : "Metal4"}]
set margin [expr {round(([info exists ::env(MARGIN)] ? $::env(MARGIN) : 0) * $dbu)}]
set pin_keep [expr {round(([info exists ::env(PIN_KEEP)] ? $::env(PIN_KEEP) : 0) * $dbu)}]
set pin_layers [expr {[info exists ::env(PIN_LAYERS)] ? $::env(PIN_LAYERS) : "Metal2"}]
set n 0
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock]} { continue }
    set bb [$inst getBBox]
    set o [$inst getOrient]
    foreach ln $layers {
        set layer [$tech findLayer $ln]
        set y0 [expr {[$bb yMin] - $margin}]
        set y1 [expr {[$bb yMax] + $margin}]
        if {$pin_keep > 0 && [lsearch -exact $pin_layers $ln] >= 0} {
            if {$o eq "MX" || $o eq "R180"} { set y1 [expr {[$bb yMax] - $pin_keep}] } else { set y0 [expr {[$bb yMin] + $pin_keep}] }
        }
        odb::dbObstruction_create $block $layer [expr {[$bb xMin] - $margin}] $y0 [expr {[$bb xMax] + $margin}] $y1
        incr n
    }
}
puts "MACRO_OBS $n obstructions on {$layers} over [expr {$n / [llength $layers]}] macros, margin [expr {$margin / double($dbu)}] um, pin band kept [expr {$pin_keep / double($dbu)}] um on {$pin_layers}"
write_db $::env(OUT_ODB)
puts "MACRO_OBS done $::env(OUT_ODB)"
