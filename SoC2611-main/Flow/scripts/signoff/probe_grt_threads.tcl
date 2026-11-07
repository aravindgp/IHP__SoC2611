# Global-route probe on an engine ck_cts.odb with the engine's settings (NDR off, 0.05 adjustment on Metal2-TopMetal1,
# 15 congestion iterations, -allow_congestion) at a chosen thread count: GRT overflow depends on the thread count
# (DGSE note: +125 percent between 7 and 12 threads), so a baseline must be measured with the probes' thread count.
# env: P_IN P_THREADS [P_ITER=15] [P_RPT=congestion.rpt]
set_thread_count $::env(P_THREADS)
read_db $::env(P_IN)
foreach net [[ord::get_db_block] getNets] {
    if {[$net getNonDefaultRule] ne "NULL" && [$net getNonDefaultRule] ne ""} { $net setNonDefaultRule NULL }
}
set_global_routing_layer_adjustment Metal2-TopMetal1 0.05
set_routing_layers -signal Metal2-TopMetal1 -clock Metal3-TopMetal1
set it [expr {[info exists ::env(P_ITER)] ? $::env(P_ITER) : 15}]
set rpt [expr {[info exists ::env(P_RPT)] ? $::env(P_RPT) : "congestion.rpt"}]
set t0 [clock seconds]
global_route -congestion_iterations $it -allow_congestion -congestion_report_file $rpt -verbose
puts "PROBE_GRT threads=$::env(P_THREADS) iters=$it t=[expr {[clock seconds]-$t0}]s"
