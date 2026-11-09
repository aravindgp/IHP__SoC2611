# pg_check.tcl - supply connectivity after a macro move (PSM check_power_grid, dcf36133) + supply-shape audit of the
# moved macros (fixed-vs-fixed overlaps that TritonRoute never reports).
# env: IN_ODB [MOVES=<eco>_moves.txt] [ERR_DIR] [DONT_REQUIRE_TERMINALS=1]
source [file join [file dirname [file normalize [info script]]] lift_common.tcl]
source [file join [file dirname [file normalize [info script]]] pdn_fix_moved_macros.tcl]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set ed [env_or ERR_DIR [file dirname $::env(IN_ODB)]]
foreach n {VDD VSS} {
    set args [list -net $n -error_file $ed/pg_$n.rpt]
    if {[env_or DONT_REQUIRE_TERMINALS 1]} { lappend args -dont_require_terminals }
    if {[catch {check_power_grid {*}$args} e]} { puts "PG_CHECK $n FAIL: $e" } else { puts "PG_CHECK $n ok" }
}
if {[env_or MOVES ""] ne ""} {
    set insts {}
    set fh [open $::env(MOVES) r]
    while {[gets $fh ln] >= 0} { set p [split [string trim $ln]]; if {[llength $p] == 5} { lappend insts [$block findInst [lindex $p 0]] } }
    close $fh
    pdnfix::audit $block $insts
}
puts "PG_CHECK done"
