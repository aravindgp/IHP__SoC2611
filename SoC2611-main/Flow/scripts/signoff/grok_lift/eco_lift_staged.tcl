# eco_lift_staged.tcl - macro move ECO on a routed db, staged so that ONE incremental global route sees the final
# geometry and re-routes every affected net (replaces eco_macroshift.tcl for K2-type moves; conventions as
# eco_macroshift/eco_sidemove: env-driven, ECO_ log lines, BTerm-without-BPin workaround, DRT left to drt_steps.tcl).
#
# Order (each step fixes one K2/K2b failure, see MORNING.md; OpenROAD dcf36133 GlobalRouter.cpp):
#   1. GRT settings (layer/region adjustments) - read by initFastRoute, so BEFORE -start_incremental
#   2. move the macros (+ their dbObstructions), fix the supply shapes (pdn_fix_moved_macros.tcl), push std cells out
#      of the new footprints along the shift direction, placement blockage on the vacated strip, legalize
#      -> all BEFORE -start_incremental: initFastRoute computes the macro blockages from the CURRENT placement.
#         (eco_macroshift called -start_incremental first; the GRT callback only marks nets dirty on a move, it never
#          recomputes capacity -> K2's 283 nets were global-routed against the OLD macro positions.)
#   3. strip set S = nets of every displaced instance + nets with wires under the new footprints (+HALO) + EXTRA_NETS
#   4. for S: destroy wire + guides and disconnect one ITerm (still before -start_incremental: no phantom wire usage,
#      and the net enters FastRoute with N-1 pins)
#   5. global_route -start_incremental ; reconnect the ITerms (dirty, pin set changed -> really re-routed)
#   6. global_route -end_incremental -allow_congestion -verbose   (GRT-0009 "rerouting N nets": N must be ~|S|)
#   7. gates: S nets without guides, S guides on Metal1-3 inside the new footprints, residual foreign wires under the
#      footprints; write_db.  DRT: drt_steps.tcl STEP_START=17 STEP_ALL_AS_INCR=1 (never a plain detailed_route).
#
# env: IN_ODB OUT_ODB SHIFT_FILE [EXTRA_NETS (names, or "x name y" lines)] [HALO_UM=0.5] [PDN_HALO_UM=2]
#      [PUSH_HALO_UM=2] [MAXDISP="150 60"] [MARGIN_UM=200] [EXHAUSTIVE=0] [BIG_PINS=10] [MAX_NETS=450] [FORCE=0]
#      [PDN_FIX=1] [VACATE_BLOCK=1] [ADJ="0.05"] [TM1_ADJ=0.30] [REGION_ADJ="L a x0 y0 x1 y1;..."] [THREADS=8]
#      [GUIDE_OUT] [STRIP_LOG=<OUT>_strip.txt] [DRT=none|plain] [END=3] [DRC_RPT]
source [file join [file dirname [file normalize [info script]]] lift_common.tcl]
source [file join [file dirname [file normalize [info script]]] pdn_fix_moved_macros.tcl]
read_db $::env(IN_ODB)
set_thread_count [env_or THREADS 8]
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set out $::env(OUT_ODB)
proc um {v} { expr {round($v * $::dbu)} }

# ---- 1. GRT settings (before start_incremental)
set_routing_layers -signal Metal2-TopMetal1
set_global_routing_layer_adjustment Metal2-Metal4 [env_or ADJ 0.05]
set_global_routing_layer_adjustment TopMetal1 [env_or TM1_ADJ 0.30]
foreach ra [split [env_or REGION_ADJ ""] ";"] {
    set ra [string trim $ra]
    if {$ra eq ""} continue
    lassign $ra l a x0 y0 x1 y1
    set_global_routing_region_adjustment [list $x0 $y0 $x1 $y1] -layer $l -adjustment $a
    puts "ECO_LIFT region adjustment $l $a ($x0 $y0 $x1 $y1)"
}

# ---- 2. moves
set before [dict create]
foreach inst [$block getInsts] { dict set before [$inst getName] [$inst getLocation] }
set shifts [lift::read_shifts $block $::env(SHIFT_FILE) $dbu]
set moves {}; set newb {}; set oldb {}; set shifted [dict create]
set mfh [open "[file rootname $out]_moves.txt" w]
foreach s $shifts {
    lassign $s inst dx dy
    set ob [lift::bbox $inst]
    lassign [$inst getLocation] x y
    set isblk [[$inst getMaster] isBlock]
    if {$isblk} { $inst setPlacementStatus PLACED }
    $inst setLocation [expr {$x + $dx}] [expr {$y + $dy}]
    dict set shifted [$inst getName] 1
    if {$isblk} {
        set nmv 0
        foreach o [$block getObstructions] {
            set b [$o getBBox]
            if {[$b xMin] >= [lindex $ob 0] - 1 && [$b xMax] <= [lindex $ob 2] + 1 && [$b yMin] >= [lindex $ob 1] - 1 && [$b yMax] <= [lindex $ob 3] + 1} {
                odb::dbObstruction_create $block [$b getTechLayer] [expr {[$b xMin] + $dx}] [expr {[$b yMin] + $dy}] [expr {[$b xMax] + $dx}] [expr {[$b yMax] + $dy}]
                odb::dbObstruction_destroy $o
                incr nmv
            }
        }
        $inst setPlacementStatus FIRM
        lappend moves [list $inst $ob $dx $dy]
        lappend oldb $ob; lappend newb [lift::bbox $inst]
        puts $mfh "[$inst getName] [lindex $ob 0] [lindex $ob 1] $dx $dy"
        puts "ECO_LIFT macro [$inst getName] by ($dx,$dy) dbu, obstructions moved: $nmv"
    } else {
        $inst setPlacementStatus PLACED
    }
}
close $mfh
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock] || [dict exists $shifted [$inst getName]]} continue
    if {[lift::ovl_any [lift::bbox $inst] [lmap n $newb {lift::bloat $n [um 2]}]]} { error "ECO_LIFT new footprint overlaps macro [$inst getName]" }
}
if {[env_or PDN_FIX 1]} { pdnfix::fix $block $moves [um [env_or PDN_HALO_UM 2]] 0 }
# push std cells out of the new footprints (+PUSH_HALO) along the dominant shift direction
set ph [um [env_or PUSH_HALO_UM 2]]
set npush 0
foreach mv $moves {
    lassign $mv m ob dx dy
    lassign [lift::bloat [lift::bbox $m] $ph] mx0 my0 mx1 my1
    foreach inst [$block getInsts] {
        if {![[$inst getMaster] isCore] || [dict exists $shifted [$inst getName]]} continue
        lassign [lift::bbox $inst] bx0 by0 bx1 by1
        if {$bx1 <= $mx0 || $bx0 >= $mx1 || $by1 <= $my0 || $by0 >= $my1} continue
        lassign [$inst getLocation] x y
        if {abs($dx) >= abs($dy)} {
            set nx [expr {$dx > 0 ? $mx1 + ($x - $bx0) : $mx0 - ($bx1 - $x)}]; set ny $y
        } else {
            set ny [expr {$dy > 0 ? $my1 + ($y - $by0) : $my0 - ($by1 - $y)}]; set nx $x
        }
        $inst setLocation $nx $ny
        $inst setPlacementStatus PLACED
        incr npush
    }
}
puts "ECO_LIFT std cells pushed out of the new footprints: $npush"
if {[env_or VACATE_BLOCK 1]} {
    set nb 0
    foreach mv $moves {
        lassign $mv m ob dx dy
        foreach r [lift::subtract $ob [lift::bbox $m]] {
            lassign $r x0 y0 x1 y1
            if {$x1 - $x0 > 0 && $y1 - $y0 > 0} { odb::dbBlockage_create $block $x0 $y0 $x1 $y1; incr nb }
        }
    }
    puts "ECO_LIFT placement blockages on vacated strips (no core rails there): $nb"
}
set removed {}
foreach bt [$block getBTerms] {
    if {[llength [$bt getBPins]] == 0} {
        lappend removed [list [$bt getName] [[$bt getNet] getName] [$bt getIoType] [$bt getSigType]]
        odb::dbBTerm_destroy $bt
    }
}
set_placement_padding -global -left 1 -right 1
detailed_placement -max_displacement [env_or MAXDISP "150 60"]
check_placement -verbose
foreach r $removed {
    lassign $r bn nn io st
    set bt [odb::dbBTerm_create [$block findNet $nn] $bn]
    $bt setIoType $io
    $bt setSigType $st
}

# ---- 3. strip set
set S [dict create]; set why [dict create]
set ndisp 0
foreach inst [$block getInsts] {
    if {[dict get $before [$inst getName]] eq [$inst getLocation]} continue
    incr ndisp
    foreach it [$inst getITerms] {
        set n [$it getNet]
        if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} { dict set S [$n getName] $n; dict set why [$n getName] PIN }
    }
}
puts "ECO_LIFT instances displaced (shifted + pushed + legalizer): $ndisp, their nets: [dict size $S]"
set halo [um [env_or HALO_UM 0.5]]
set foot [lmap n $newb {lift::bloat $n $halo}]
set layers {Metal1 Metal2 Metal3 Metal4}
set under [lift::nets_under $block $foot $layers [um [env_or MARGIN_UM 200]] [env_or EXHAUSTIVE 0]]
dict for {k v} $under {
    dict set S $k [lindex $v 0]
    dict set why $k [expr {[dict exists $why $k] ? "FOOT+PIN" : "FOOT"}]
}
set nx 0
if {[env_or EXTRA_NETS ""] ne ""} {
    set fh [open $::env(EXTRA_NETS) r]
    while {[gets $fh ln] >= 0} {
        set p [split [string trim $ln]]
        if {[llength $p] == 0 || [string index [lindex $p 0] 0] eq "#"} continue
        set name [expr {[llength $p] == 3 ? [lindex $p 1] : [lindex $p 0]}]
        if {[dict exists $S $name]} continue
        set n [$block findNet $name]
        if {$n eq "NULL" || [$n getSigType] in {POWER GROUND}} continue
        dict set S $name $n; dict set why $name EXTRA; incr nx
    }
    close $fh
}
puts "ECO_LIFT extra nets: $nx"
set cnt [dict create]
set sfh [open [env_or STRIP_LOG "[file rootname $out]_strip.txt"] w]
dict for {name net} $S {
    lassign [lift::classify $net [env_or BIG_PINS 10]] c nt nm
    puts $sfh "$name $c $nt $nm [dict get $why $name]"
    dict incr cnt "[dict get $why $name]/$c"
}
close $sfh
foreach k [lsort [dict keys $cnt]] { puts "ECO_LIFT strip $k [dict get $cnt $k]" }
puts "ECO_LIFT strip set total [dict size $S]"
if {[dict size $S] > [env_or MAX_NETS 450] && ![env_or FORCE 0]} {
    error "ECO_LIFT strip set [dict size $S] > MAX_NETS - not writing anything (FORCE=1 to override)"
}

# ---- 4./5./6. one incremental global route on the final geometry
set rec [lift::predisconnect $S]
global_route -start_incremental
lift::reconnect $rec
global_route -end_incremental -allow_congestion -verbose
puts "ECO_LIFT incremental global route done"

# ---- 7. gates
set noguide 0; set gin 0
set inner [lmap n $newb {lift::bloat $n [um -7.2]}]
dict for {name net} $S {
    set nt [expr {[llength [$net getITerms]] + [llength [$net getBTerms]]}]
    set gs [$net getGuides]
    if {[llength $gs] == 0 && $nt > 1} { incr noguide; continue }
    foreach g $gs {
        set l [[$g getLayer] getName]
        if {$l ni {Metal1 Metal2 Metal3}} continue
        set r [$g getBox]
        if {[lift::ovl_any [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]] $inner]} { incr gin }
    }
}
puts "ECO_LIFT gate: stripped multi-pin nets without guides: $noguide (want 0)"
puts "ECO_LIFT gate: stripped-net guides on Metal1-3 inside the new footprints (shrunk 1 gcell): $gin (want ~0)"
set res [lift::nets_under $block $foot $layers [um [env_or MARGIN_UM 200]] [env_or EXHAUSTIVE 0]]
puts "ECO_LIFT gate: nets with wires still under the new footprints: [dict size $res] (want 0)"
pdnfix::audit $block [lmap m $moves {lindex $m 0}]
if {[env_or GUIDE_OUT ""] ne ""} { write_guides $::env(GUIDE_OUT) }
if {[env_or DRT none] eq "plain"} {
    set rpt [env_or DRC_RPT "[file rootname $out]_drc.rpt"]
    detailed_route -output_drc $rpt -droute_end_iter [env_or END 3] -verbose 1
}
set unrouted 0
foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} continue
    if {[$net getWire] eq "NULL" && [llength [$net getITerms]] > 1} { incr unrouted }
}
puts "ECO_LIFT unrouted multi-pin signal nets in the db: $unrouted (= strip set before DRT)"
write_db $out
puts "ECO_LIFT done $out"
