# Fast pre-LVS connectivity check of a chip ODB (minutes; full-chip KLayout LVS sat 7 h in alignment):
#   logical : DGSE dgse_connectivity_check -- every top pin reaches an instance pin, no driverless or
#             multi-driven signal net (the split-alias bug class LVS would report as pin-match failure);
#   physical: signal nets with no routing (opens) and the DRT short count from the route DRC report.
# Shorts/opens between the routing and the netlist are what LVS adds; run KLayout LVS (run_lvs.sh --deep
# --blackbox 'RM_IHPSG13_*' --blackbox 'sg13cmos5l_IO*') only on the clean-routed final GDS.
# env: CONN_IN [CONN_DRC_RPT]
read_db $::env(CONN_IN)
source /root/.claude/jobs/658ac326/tmp/dgse/DGSE/runs/c7w32-6600-respread/build/flow/connectivity_check.tcl
set ok [expr {![catch {dgse_connectivity_check signoff} msg]}]
puts "CONN_LOGICAL [expr {$ok ? "PASS" : "FAIL: $msg"}]"
set nsig 0; set unrouted {}
foreach n [[ord::get_db_block] getNets] {
  if {[$n getSigType] ne "SIGNAL" || [llength [$n getITerms]] + [llength [$n getBTerms]] < 2} continue
  incr nsig
  if {[$n getWire] eq "NULL"} { lappend unrouted [$n getName] }
}
puts "CONN_UNROUTED [llength $unrouted] of $nsig multi-pin signal nets"
foreach u [lrange $unrouted 0 19] { puts "CONN_UNROUTED_NET $u" }
if {[info exists ::env(CONN_DRC_RPT)] && [file exists $::env(CONN_DRC_RPT)]} {
  set fh [open $::env(CONN_DRC_RPT)]; set tx [read $fh]; close $fh
  puts "CONN_DRT_SHORTS [regexp -all -line {^\s*violation type: Short} $tx]"
  puts "CONN_DRT_VIOLATIONS [regexp -all -line {^\s*violation type:} $tx]"
}
