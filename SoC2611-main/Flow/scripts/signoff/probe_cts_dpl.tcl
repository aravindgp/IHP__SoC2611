# Reproduce the engine's CTS + post-CTS detailed_placement on a ck_dplace.odb and locate the cells that fail to
# legalise (DPL-0034/0036 on "clkload" dummy loads, DPASS A-bands 5 Nov).  env: P_IN P_SDC [P_DISP="x y" um] [P_THREADS]
set_thread_count [expr {[info exists ::env(P_THREADS)] ? $::env(P_THREADS) : 8}]
read_liberty /root/.claude/jobs/658ac326/tmp/dgse/DGSE/pdk/cmos5l_fo40/sg13cmos5l_stdcell_typ_1p20V_25C_fo40.lib
foreach f [glob /root/.claude/jobs/658ac326/tmp/pdk_root/ihp-sg13cmos5l/libs.ref/sg13cmos5l_sram/lib/RM_IHPSG13_*_typ_1p20V_25C.lib] { read_liberty $f }
read_db $::env(P_IN)
read_sdc $::env(P_SDC)
source /root/.claude/jobs/658ac326/tmp/dgse/DGSE/engine/flow/platforms/ihp-sg13cmos5l-dgse/setRC.tcl
foreach c {sg13cmos5l_lgcp_1 sg13cmos5l_sighold sg13cmos5l_slgcp_1 sg13cmos5l_dfrbp_2 sg13cmos5l_sdfbbp_1} { catch {set_dont_use $c} }
set_placement_padding -global -left 1 -right 1
set t0 [clock seconds]
repair_clock_inverters
clock_tree_synthesis -root_buf sg13cmos5l_buf_8 -buf_list {sg13cmos5l_buf_2 sg13cmos5l_buf_4 sg13cmos5l_buf_8} -sink_clustering_enable -balance_levels
set_propagated_clock [all_clocks]
estimate_parasitics -placement
repair_clock_nets
puts "PROBE cts done t=[expr {[clock seconds]-$t0}]s"
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
# where are the clkload cells?  classify each against macros / blockages / rows
set macros {}
foreach i [$block getInsts] { if {[[$i getMaster] isBlock]} { lappend macros [$i getBBox] } }
set blks [$block getBlockages]
set n 0; set inmac 0; set inblk 0; set other 0
set fh [open clkload_loc.txt w]
foreach i [$block getInsts] {
    set nm [$i getName]
    if {![string match "clkload*" $nm]} { continue }
    incr n
    lassign [$i getLocation] x y
    set cls other
    foreach bb $macros { if {$x >= [$bb xMin] && $x <= [$bb xMax] && $y >= [$bb yMin] && $y <= [$bb yMax]} { set cls macro; break } }
    if {$cls eq "other"} {
        foreach b $blks { set bb [$b getBBox]; if {$x >= [$bb xMin] && $x <= [$bb xMax] && $y >= [$bb yMin] && $y <= [$bb yMax]} { set cls blockage; break } }
    }
    incr $cls
    puts $fh "$nm [expr {$x/1000.0}] [expr {$y/1000.0}] $cls [$i getPlacementStatus]"
}
close $fh
puts "PROBE clkload n=$n in_macro=$inmac in_blockage=$inblk other=$other (names in clkload_loc.txt)"
set disp [expr {[info exists ::env(P_DISP)] ? $::env(P_DISP) : ""}]
if {$disp ne ""} {
    puts "PROBE detailed_placement -max_displacement {$disp}"
    set rc [catch {detailed_placement -max_displacement $disp} err]
} else {
    puts "PROBE detailed_placement (default displacement)"
    set rc [catch {detailed_placement} err]
}
puts "PROBE dpl rc=$rc $err"
if {$rc} {
    puts "PROBE retry with -max_displacement {1500 1500}"
    set rc2 [catch {detailed_placement -max_displacement {1500 1500}} err2]
    puts "PROBE dpl2 rc=$rc2 $err2"
}
puts "PROBE_DONE t=[expr {[clock seconds]-$t0}]s"
