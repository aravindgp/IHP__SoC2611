# Chip-level global route of the pad nets on an integrated chip ODB (chip_integrate.tcl STOP_AFTER=pdn), prepared
# for a detailed route with per-pass snapshots (dgse drt_steps.tcl) instead of chip_integrate.tcl's single call.
# env: IN_ODB (chip_pdn.odb)  OUT_ODB (for DRT)  BPINS_TCL (written: re-creates the bondpad pins after DRT)
#      GUIDE (route.guide path)  THREADS (default 8)
proc env_or {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
read_db $::env(IN_ODB)
set_thread_count [env_or THREADS 8]
set block [ord::get_db_block]
# Margin-spilled core nets are stripped before this step (chip_drt_prep.sh STRIP_MARGIN=1: def_margin_nets.py +
# chip_strip_margin.tcl); the pads/IO cells are real obstacles here, so GRT/DRT route around them.
# NOTE: set_global_routing_region_adjustment over the margin strips UNDERFLOWED the capacity to 65535 (GRT-0113,
# negative "Resource Reduction") on the chip ODB (3 Nov) -> not used.
set_global_routing_layer_adjustment Metal2-TopMetal1 0.05
# LAYER_ADJUST: per-layer GRT capacity derate from the per-layer congestion (e.g. "Metal2 0.30 Metal3 0.30 Metal4 0.15
# TopMetal1 0.0"): pushes demand off the congested M2/M3 onto M4/TM1 (TM1 is free over the SRAMs). Applied after the
# range-wide value so it wins (same as pnr.tcl DGSE_LAYER_ADJUST).
foreach {lyr val} [split [string trim [env_or LAYER_ADJUST ""]]] {
    set_global_routing_layer_adjustment $lyr $val
    puts "CHIP_GRT per-layer adjustment $lyr = $val"
}
set_routing_layers -signal Metal2-TopMetal1
# CONG_ITERS caps the overflow-removal iterations (default 50 took 3:51 h on the stripped chip, 3 Nov)
# NDR clearing (5 Nov): nets that still carry a non-default rule (clock NDR from CTS, net17209) make GRT disable
# them after the last iteration and RESTART the whole overflow loop (chipH2: 50 iterations, then again from 1).
set _nndr 0
foreach _n [[ord::get_db_block] getNets] {
    if {[$_n getNonDefaultRule] ne "NULL" && [$_n getNonDefaultRule] ne ""} { $_n setNonDefaultRule NULL; incr _nndr }
}
puts "CHIP_GRT cleared NDR on $_nndr net(s)"
global_route -guide_file [env_or GUIDE route.guide] -allow_congestion -verbose \
    -congestion_iterations [env_or CONG_ITERS 15]
# DRT-0302 "Unsupported multiple pins on bterm": save + drop the bondpad BPins (same as chip_integrate.tcl stage 6)
set fh [open $::env(BPINS_TCL) w]
puts $fh "set _blk \[ord::get_db_block\]; set _tech \[\[ord::get_db\] getTech\]"
set n 0
foreach bt [$block getBTerms] {
    if {[string match *_PAD [$bt getName]] || [$bt getName] in {VDD VSS IOVDD IOVSS}} {
        foreach bp [$bt getBPins] {
            foreach bx [$bp getBoxes] {
                puts $fh "set _bp \[odb::dbBPin_create \[\$_blk findBTerm {[$bt getName]}\]\]; odb::dbBox_create \$_bp \[\$_tech findLayer [[$bx getTechLayer] getName]\] [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]; \$_bp setPlacementStatus FIRM"
                incr n
            }
            odb::dbBPin_destroy $bp
        }
    }
}
close $fh
puts "CHIP_GRT saved $n bondpad pins to $::env(BPINS_TCL)"
write_db $::env(OUT_ODB)
puts "CHIP_GRT done $::env(OUT_ODB)"
