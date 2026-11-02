# Post-route hold/setup ECO on a routed core ODB (placement RC: there are no CMOS5L RCX rules).
# Inserts hold buffers outside any incremental GRT session (EST-0104), legalises them with a bounded
# displacement and writes ECO_OUT; the buffered/moved nets are then re-routed by global_route +
# detailed_route on the existing routing (as in chip_integrate.tcl step 3).
# env: ECO_IN ECO_SDC ECO_OUT [ECO_HOLD_MARGIN=0.05] [ECO_BUF_PCT=10] [ECO_THREADS=4]
set PD /root/.claude/jobs/658ac326/tmp/pdk_root/ihp-sg13cmos5l/libs.ref
read_liberty $PD/sg13cmos5l_stdcell/lib/sg13cmos5l_stdcell_typ_1p20V_25C.lib
foreach f [glob $PD/sg13cmos5l_sram/lib/RM_IHPSG13_*_typ_1p20V_25C.lib] { read_liberty $f }
read_db $::env(ECO_IN)
read_sdc $::env(ECO_SDC)
source /root/.claude/jobs/658ac326/tmp/dgse/DGSE/engine/flow/platforms/ihp-sg13cmos5l-dgse/setRC.tcl
set_thread_count [expr {[info exists ::env(ECO_THREADS)] ? $::env(ECO_THREADS) : 4}]
set_propagated_clock [all_clocks]
estimate_parasitics -placement
proc slacks {tag} {
    puts [format "ECO_SLACK %-6s hold WNS %.3f TNS %.1f | setup WNS %.3f TNS %.1f" $tag \
        [sta::worst_slack -min] [sta::total_negative_slack -min] [sta::worst_slack -max] [sta::total_negative_slack -max]]
}
slacks before
set n0 [llength [get_cells *]]
set margin [expr {[info exists ::env(ECO_HOLD_MARGIN)] ? $::env(ECO_HOLD_MARGIN) : 0.05}]
set pct [expr {[info exists ::env(ECO_BUF_PCT)] ? $::env(ECO_BUF_PCT) : 10}]
repair_timing -hold -hold_margin $margin -max_buffer_percent $pct -allow_setup_violations -verbose
puts "ECO_INFO hold buffers inserted: [expr {[llength [get_cells *]] - $n0}]"
detailed_placement -max_displacement {40 4}
check_placement -verbose
estimate_parasitics -placement
slacks after
write_db $::env(ECO_OUT)
puts "ECO_DONE -> $::env(ECO_OUT)"
