# Post-route chip integration: core ODB (top-level pins on the die edge, no pads) -> chip ODB with the
# IO pad ring, bondpads, pad-to-core signal routing and pad-to-core-ring power straps.
#
#   openroad -no_init -no_splash -exit chip_integrate.tcl     (env below; see README "Chip integration")
#
# env:
#   IN_ODB      routed core ODB (e.g. DGSE build/final.odb or the last DRT checkpoint)
#   OUT_DIR     output directory (chip.odb, chip.def, chip.v, route_drc.rpt, integrate.log lines)
#   PADRING_DIR make_padring.py --portmap output (padring.tcl, pad_connect.tcl, bondpad_70x70.lef)
#   PDK_ROOT    IHP-Open-PDK root (sg13cmos5l_io.lef)
#   THREADS     (default 2)
#   STOP_AFTER  optional: "connect" (netlist only), "place" (pads placed, no PDN/routing), "pdn"
#   START_AT    optional: "pdn" = IN_ODB is chip_placed.odb (skip netlist + pad placement)
#   STRAPS_TCL  Tcl from pad_pdn_straps.tcl (pad->core-ring power straps), sourced at stage pdn
#   DRT_END_ITER detailed_route -droute_end_iter (default 64)
#
# What it does
#   1. reads the IO and bondpad LEFs into the ODB's database;
#   2. for every pad in pad_connect.tcl: creates the pad instance, moves each mapped core net from its
#      top-level BTerm to the pad's core-side pin (p2c / c2p / c2p_en), deletes those BTerms, and
#      creates the external net + BTerm <pad>_PAD on the pad pin;
#   3. destroys the existing routing (dbWire) of every core net it re-connected -- those wires ran to
#      the old die-edge pins through the pad ring area;
#   4. sources padring.tcl (IO sites, pads, corners, IO fill, abutment, bondpads), ties supply
#      bondpads to VDD/VSS/IOVDD/IOVSS, places the BTerm pins on the bondpads;
#   5. PDN: sources STRAPS_TCL: straps from the pad ring's vdd/vss rails to
#      the core ring, computed by pdngen in pad_pdn_straps.tcl;
#   6. global_route + detailed_route (only the unrouted pad nets have no routing; see README for the
#      measured behaviour on already-routed nets), then writes chip.odb / chip.def / chip.v.

proc env_or {name default} { if {[info exists ::env($name)] && $::env($name) ne ""} { return $::env($name) }; return $default }
proc stage {s} { puts "CHIP_INTEGRATE_STAGE $s t=[clock seconds]" }
set in_odb  $::env(IN_ODB)
set out_dir [env_or OUT_DIR chip_integrate_out]
set prd     $::env(PADRING_DIR)
set io_lef  $::env(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/lef/sg13cmos5l_io.lef
set threads [env_or THREADS 2]
set stop    [env_or STOP_AFTER ""]
file mkdir $out_dir
set_thread_count $threads

stage read
read_db $in_odb
set db    [ord::get_db]
set block [ord::get_db_block]
if {[$db findMaster sg13cmos5l_IOPadIn] eq "NULL"} { read_lef $io_lef }
source $prd/pad_connect.tcl
if {[$db findMaster $bondpad_master] eq "NULL"} { read_lef $prd/$bondpad_master.lef }

set start [env_or START_AT ""]
if {$start eq "pdn"} {
    puts "CHIP_INTEGRATE_INFO START_AT=pdn: $in_odb is taken as already pad-placed"
} else {
# ---------------------------------------------------------------- 2. netlist
stage connect
set supplies {VDD VSS IOVDD IOVSS}
# ODB keeps Verilog bus bits escaped (acc\[0\]); index BTerms by their plain name
set bterm_by_name [dict create]
foreach bt [$block getBTerms] { dict set bterm_by_name [string map [list "\\" ""] [$bt getName]] $bt }
set dead_bterms {}
set touched {}
set nerr 0
foreach p $pad_list {
    lassign $p inst master sig pinmap
    set m [$db findMaster $master]
    if {$m eq "NULL"} { puts "ERROR no master $master"; incr nerr; continue }
    if {[$block findInst $inst] ne "NULL"} { puts "ERROR instance $inst exists already (ODB integrated twice?)"; incr nerr; continue }
    set i [odb::dbInst_create $block $m $inst]
    if {[lsearch $supplies $sig] >= 0} { continue }
    foreach {pin port} $pinmap {
        set bt [expr {[dict exists $bterm_by_name $port] ? [dict get $bterm_by_name $port] : "NULL"}]
        if {$bt eq "NULL"} { puts "ERROR chip port $port (pad $sig.$pin) not in the ODB"; incr nerr; continue }
        set n [$bt getNet]
        set it [$i findITerm $pin]
        if {$it eq "NULL"} { puts "ERROR $master has no pin $pin"; incr nerr; continue }
        $it connect $n
        lappend dead_bterms $bt
        lappend touched $n
    }
    set pname ${sig}_PAD
    if {[$block findNet $pname] ne "NULL"} { puts "ERROR net $pname exists"; incr nerr; continue }
    set pn [odb::dbNet_create $block $pname]
    [$i findITerm pad] connect $pn
    set nb [odb::dbBTerm_create $pn $pname]
    $nb setIoType INOUT
    $nb setSigType SIGNAL
}
foreach bt [lsort -unique $dead_bterms] { odb::dbBTerm_destroy $bt }
# leftover signal BTerms = chip ports without a pad
foreach bt [$block getBTerms] {
    set n [$bt getNet]
    if {[$n getSigType] in {POWER GROUND}} { continue }
    if {![string match *_PAD [$bt getName]]} { puts "ERROR chip port [$bt getName] has no pad"; incr nerr }
}
if {$nerr} { puts "CHIP_INTEGRATE_FAIL $nerr netlist error(s)"; exit 1 }
set nwire 0
foreach n [lsort -unique $touched] {
    set w [$n getWire]
    if {$w ne "NULL"} { odb::dbWire_destroy $w; incr nwire }
}
puts "CHIP_INTEGRATE_INFO [llength $pad_list] pads, [llength [lsort -unique $dead_bterms]] core ports moved to pads, $nwire core-net wires removed for re-routing"
if {$stop eq "connect"} { write_db $out_dir/chip_connect.odb; exit 0 }

# ---------------------------------------------------------------- 4. pad placement
stage place
source $prd/padring.tcl
global_connect
foreach p $pad_list {
    lassign $p inst master sig pinmap
    if {[lsearch $supplies $sig] < 0} { continue }
    set n [$block findNet $sig]
    if {$n eq "NULL"} { set n [odb::dbNet_create $block $sig]; $n setSpecial; $n setSigType [expr {[string match *SS $sig] ? "GROUND" : "POWER"}] }
    set b [$block findInst IO_BOND_$inst]
    if {$b ne "NULL"} { [$b findITerm pad] connect $n }
    if {[$block findBTerm $sig] eq "NULL"} {
        set bt [odb::dbBTerm_create $n $sig]; $bt setIoType INOUT; $bt setSigType [$n getSigType]
    }
}
place_io_terminals IO_BOND_*/pad
if {$stop eq "place"} { write_db $out_dir/chip_placed.odb; write_def $out_dir/chip_placed.def; exit 0 }
}

# ---------------------------------------------------------------- 5. pad <-> core ring power
# Straps precomputed by pad_pdn_straps.tcl (pdngen on a scratch copy of chip_placed.odb, see there).
stage pdn
if {[env_or STRAPS_TCL ""] eq ""} {
    puts "CHIP_INTEGRATE_WARN STRAPS_TCL not set: NO power connection between pad ring and core ring"
} else {
    set ns0 0
    foreach nn {VDD VSS} { foreach sw [[$block findNet $nn] getSWires] { incr ns0 [llength [$sw getWires]] } }
    source $::env(STRAPS_TCL)
    # an empty SWIRE is written to DEF as a bare "+ ROUTED" that KLayout's DEF reader rejects
    foreach nn {VDD VSS} { foreach sw [[$block findNet $nn] getSWires] { if {[llength [$sw getWires]] == 0} { odb::dbSWire_destroy $sw } } }
    set ns 0
    foreach nn {VDD VSS} { foreach sw [[$block findNet $nn] getSWires] { incr ns [llength [$sw getWires]] } }
    puts "CHIP_INTEGRATE_INFO merged straps from $::env(STRAPS_TCL): VDD+VSS special shapes $ns0 -> $ns"
}
if {$stop eq "pdn"} { write_db $out_dir/chip_pdn.odb; write_def $out_dir/chip_pdn.def; exit 0 }

# ---------------------------------------------------------------- 6. route the pad nets
stage global_route
set_global_routing_layer_adjustment Metal2-TopMetal1 0.05
set_routing_layers -signal Metal2-TopMetal1
global_route -guide_file $out_dir/route.guide -allow_congestion -verbose
stage detailed_route
# DRT-0302 "Unsupported multiple pins on bterm": the supply BTerms carry one pin per bondpad. The
# bondpad pins need no routing (abutment), so save + drop all bondpad BPins for DRT, re-create after
# (a second place_io_terminals after DRT created no pins -- measured).
set saved_bpins {}
foreach bt [$block getBTerms] {
    if {[string match *_PAD [$bt getName]] || [$bt getName] in {VDD VSS IOVDD IOVSS}} {
        foreach bp [$bt getBPins] {
            foreach bx [$bp getBoxes] {
                lappend saved_bpins [list [$bt getName] [[$bx getTechLayer] getName] [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]
            }
            odb::dbBPin_destroy $bp
        }
    }
}
detailed_route -output_drc $out_dir/route_drc.rpt -droute_end_iter [env_or DRT_END_ITER 64] -verbose 1
stage write
set tech [[ord::get_db] getTech]
foreach sp $saved_bpins {
    lassign $sp bn ln x0 y0 x1 y1
    set bp [odb::dbBPin_create [$block findBTerm $bn]]
    odb::dbBox_create $bp [$tech findLayer $ln] $x0 $y0 $x1 $y1
    $bp setPlacementStatus FIRM
}
puts "CHIP_INTEGRATE_INFO re-created [llength $saved_bpins] bondpad pins"
write_db $out_dir/chip.odb
write_def $out_dir/chip.def
write_verilog $out_dir/chip.v
puts "CHIP_INTEGRATE_DONE"
