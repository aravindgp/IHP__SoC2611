# Incremental global-route repair of a net list on a chip ODB that already carries global-route guides: the nets in
# NETS_FILE are marked dirty (one ITerm disconnected and reconnected), then global_route -end_incremental re-routes
# only them with every other net's guides as used capacity.  Writes the new guides to GUIDE_OUT.
# env: IN_ODB NETS_FILE GUIDE_OUT [THREADS=8] [OUT_ODB]
proc env_or {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
read_db $::env(IN_ODB)
set_thread_count [env_or THREADS 8]
set block [ord::get_db_block]
set_global_routing_layer_adjustment Metal2-TopMetal1 0.05
set_routing_layers -signal Metal2-TopMetal1
set nets {}
set fh [open $::env(NETS_FILE) r]
while {[gets $fh ln] >= 0} {
    set ln [string trim $ln]
    if {$ln eq ""} continue
    set n [$block findNet $ln]
    if {$n eq "NULL"} { puts "GRT_INCR missing net $ln"; continue }
    lappend nets $n
}
close $fh
puts "GRT_INCR [llength $nets] nets to re-route"
global_route -start_incremental
foreach n $nets {
    set its [$n getITerms]
    if {[llength $its] == 0} continue
    set it [lindex $its 0]
    $it disconnect
    $it connect $n
}
global_route -end_incremental -allow_congestion
write_guides $::env(GUIDE_OUT)
if {[info exists ::env(OUT_ODB)] && $::env(OUT_ODB) ne ""} { write_db $::env(OUT_ODB) }
puts "GRT_INCR done"
