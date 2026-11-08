# Antenna repair as an ECO on a routed chip db: repair_antennas inserts DIODE cells on the violating nets (and marks
# those nets dirty for an incremental global route), the wires of every net touching an inserted diode are deleted,
# a plain detailed_route re-routes them (END passes), then check_antennas reports the remaining violations.
# env: IN_ODB OUT_ODB [DIODE=sg13cmos5l_antennanp] [ITER=3] [END=5] [THREADS=8] [DRC_RPT] [ANT_RPT]
proc env_or {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
read_db $::env(IN_ODB)
set_thread_count [env_or THREADS 8]
set block [ord::get_db_block]
set_global_routing_layer_adjustment Metal2-TopMetal1 0.05
set_routing_layers -signal Metal2-TopMetal1
set n0 [llength [$block getInsts]]
set diode [env_or DIODE sg13cmos5l_antennanp]
set before [dict create]
foreach inst [$block getInsts] { dict set before [$inst getName] 1 }
# chip-level dbs carry pad BTerms without shapes: remove for the legalization inside repair_antennas, recreate after
set removed {}
foreach bt [$block getBTerms] {
    if {[llength [$bt getBPins]] == 0} {
        lappend removed [list [$bt getName] [[$bt getNet] getName] [$bt getIoType] [$bt getSigType]]
        odb::dbBTerm_destroy $bt
    }
}
# the placement blockages (pockets next to the macros) served the global placement only; the diodes are legalized
# right next to their cells, many of which now sit at a pocket edge, so the blockages are dropped first
if {[env_or DROP_BLOCKAGES 1]} {
    set nb 0
    foreach b [$block getBlockages] { odb::dbBlockage_destroy $b; incr nb }
    puts "ECO_ANT placement blockages removed: $nb"
}
global_route -start_incremental
repair_antennas $diode -iterations [env_or ITER 3]
global_route -end_incremental -allow_congestion
foreach r $removed {
    lassign $r bn nn io st
    set bt [odb::dbBTerm_create [$block findNet $nn] $bn]
    $bt setIoType $io
    $bt setSigType $st
}
set added {}
set touched [dict create]
foreach inst [$block getInsts] {
    if {[dict exists $before [$inst getName]]} { continue }
    lappend added $inst
    foreach it [$inst getITerms] {
        set net [$it getNet]
        if {$net ne "NULL" && [$net getSigType] eq "SIGNAL"} { dict set touched [$net getName] $net }
    }
}
puts "ECO_ANT diodes inserted: [llength $added] (insts $n0 -> [llength [$block getInsts]]), nets touched: [dict size $touched]"
set nd 0
dict for {name net} $touched {
    set w [$net getWire]
    if {$w ne "NULL"} { odb::dbWire_destroy $w; incr nd }
}
puts "ECO_ANT routing deleted on $nd nets"
set rpt [env_or DRC_RPT [file rootname $::env(OUT_ODB)]_drc.rpt]
detailed_route -output_drc $rpt -droute_end_iter [env_or END 5] -verbose 1
set ant [env_or ANT_RPT [file rootname $::env(OUT_ODB)]_antenna.rpt]
check_antennas -report_file $ant
write_db $::env(OUT_ODB)
puts "ECO_ANT done $::env(OUT_ODB)"
