# pdn_fix_moved_macros.tcl - repair the supply shapes around macros moved on a routed db (odb surgery, no pdngen).
#
# Why (pdn.tcl of SoC2611): the core grid has Metal1 followpins (0.44 / 7.56), Metal4 stripes (1.0 / spacing 2 /
# pitch 50 / offset 10) with Via1-3 stacks at the rail crossings, and TopMetal1 straps (VDD 1.8/16/2, VSS 1.8/32/10)
# that run over the macros. The macro grids (CORE_macro_grid_1/2, -halo 2, -grid_over_boundary) only add TopVia1 at
# TopMetal1 strap x macro Metal4 pin (VDD!/VSS!/VDDARRAY!, 2.81 um, 40 per 64x16) crossings. After a move:
#   (1) core Metal1 rails / Metal4 stripes / Via1-3 under the NEW footprint now overlap the macro's Metal1-3 OBS and
#       its Metal4 power pins: a core VDD stripe across a VSS! pin is a hard VDD-VSS short. Both shapes are FIXED, so
#       TritonRoute does not report it (no marker between two fixed shapes) - it shows up in LVS / KLayout DRC.
#   (2) the macro-grid TopVia1 stay at the OLD position: for a y move they land on nothing (floating stacks, their
#       Metal4 landing pads in the new gap block signal tracks) and the moved VDDARRAY! 19 um band may get no via at
#       all (check_power_grid / PSM failure). For an x move parallel to the straps the same vias shifted by dx are
#       exactly right (the pins move by dx, the straps are continuous).
# What it does per moved macro (old box O, new box N):
#   a. destroy the VDD/VSS TopVia1 (bottom Metal4, top TopMetal1) whose centre lies inside O (macro-grid vias)
#   b. destroy core Via1-3/TopVia1 whose centre is inside N+PDN_HALO; cut Metal1-Metal4 supply boxes crossing
#      N+PDN_HALO into the pieces outside it (recreated with the same layer and shape type); TopMetal1 untouched
#   c. re-create macro-grid TopVia1: dy == 0 -> the vias of (a) translated by dx; otherwise at every crossing of a
#      TopMetal1 strap (same net) with a Metal4 power pin of the moved macro where the strap lies fully inside the pin's
#      y-extent, using the via master of (a) for that net
# Old footprint minus new (the vacated strip) gets no rails back: keep it routing-only (placement blockage, see
#   eco_lift_staged.tcl VACATE_BLOCK).
# API (dcf36133, checked): dbNet getSWires, dbSWire getWires, dbSBox isVia/getTechVia/getBlockVia/getViaXY(->{x y})/
#   getWireShapeType(->"STRIPE"|"FOLLOWPIN"|...)/getSWire/getTechLayer, odb::dbSBox_create swire layer x1 y1 x2 y2 type
#   and swire via x y type (create_sboxes.tcl / smash_vias.tcl tests), odb::dbSBox_destroy.
#   dbTransform::apply(Rect&) is NOT usable from Tcl (the swig maps "Rect & r" to an output-only argument), so the
#   pin boxes are transformed by hand (R0/MX/MY/R180 only - the SRAMs here are R0/MX).
# Usage: sourced by eco_lift_staged.tcl (proc pdnfix::fix), or standalone:
#   env: PDNFIX_STANDALONE=1 IN_ODB OUT_ODB MOVES ("inst old_x0 old_y0 dx dy" dbu, one per line - written by eco_lift_staged as
#        <OUT>_moves.txt) [PDN_HALO_UM=2] [DRY=0]   (standalone = re-apply on a db moved without the fix)
if {[info procs env_or] eq ""} { source [file join [file dirname [file normalize [info script]]] lift_common.tcl] }

namespace eval pdnfix {}

proc pdnfix::supply_sboxes {block} {
    set out {}
    foreach netname {VDD VSS} {
        set n [$block findNet $netname]
        if {$n eq "NULL"} continue
        foreach sw [$n getSWires] { foreach sb [$sw getWires] { lappend out [list $netname $sb] } }
    }
    return $out
}
proc pdnfix::via_of {sb} { expr {[$sb getTechVia] ne "NULL" ? [$sb getTechVia] : [$sb getBlockVia]} }

# Metal4 power-pin boxes of a placed macro in chip dbu: list of {net x0 y0 x1 y1}
proc pdnfix::macro_power_pins {inst} {
    set m [$inst getMaster]
    set W [$m getWidth]; set H [$m getHeight]
    lassign [lift::bbox $inst] X0 Y0 X1 Y1
    set o [$inst getOrient]
    set out {}
    foreach mt [$m getMTerms] {
        if {[$mt getSigType] ni {POWER GROUND}} continue
        set it [$inst findITerm [$mt getName]]
        if {$it eq "NULL" || [$it getNet] eq "NULL"} continue
        set net [[$it getNet] getName]
        foreach mp [$mt getMPins] {
            foreach b [$mp getGeometry] {
                if {[$b getTechLayer] eq "NULL" || [[$b getTechLayer] getName] ne "Metal4"} continue
                set x0 [$b xMin]; set y0 [$b yMin]; set x1 [$b xMax]; set y1 [$b yMax]
                switch -- $o {
                    R0   { set r [list [expr {$X0+$x0}] [expr {$Y0+$y0}] [expr {$X0+$x1}] [expr {$Y0+$y1}]] }
                    MX   { set r [list [expr {$X0+$x0}] [expr {$Y0+$H-$y1}] [expr {$X0+$x1}] [expr {$Y0+$H-$y0}]] }
                    MY   { set r [list [expr {$X0+$W-$x1}] [expr {$Y0+$y0}] [expr {$X0+$W-$x0}] [expr {$Y0+$y1}]] }
                    R180 { set r [list [expr {$X0+$W-$x1}] [expr {$Y0+$H-$y1}] [expr {$X0+$W-$x0}] [expr {$Y0+$H-$y0}]] }
                    default { error "pdnfix: orientation $o of [$inst getName] not handled" }
                }
                lappend out [list $net {*}$r]
            }
        }
    }
    return $out
}

# moves: list of {inst old_box dx dy} (old_box in dbu, inst ALREADY at its new location). Returns a stats dict.
proc pdnfix::fix {block moves halo dry} {
    set st [dict create]
    set sbs [supply_sboxes $block]
    foreach mv $moves {
        lassign $mv inst ob dx dy
        set nb [lift::bbox $inst]
        set nbh [lift::bloat $nb $halo]
        set iname [$inst getName]
        # a. macro-grid vias inside the old box
        set oldvias {}
        set keep {}
        set near [lift::union_bbox [list $ob $nbh]]
        foreach e $sbs {
            lassign $e net sb
            if {![lift::ovl [list [$sb xMin] [$sb yMin] [$sb xMax] [$sb yMax]] $near]} { lappend keep $e; continue }
            if {[$sb isVia]} {
                set v [via_of $sb]
                lassign [$sb getViaXY] vx vy
                set inold [lift::ovl [list $vx $vy [expr {$vx+1}] [expr {$vy+1}]] $ob]
                set innew [lift::ovl [list $vx $vy [expr {$vx+1}] [expr {$vy+1}]] $nbh]
                set isTop [expr {[[$v getBottomLayer] getName] eq "Metal4" && [[$v getTopLayer] getName] eq "TopMetal1"}]
                if {$inold && $isTop} {
                    lappend oldvias [list $net [$sb getSWire] $v $vx $vy [$sb getWireShapeType]]
                    if {!$dry} { odb::dbSBox_destroy $sb }
                    dict incr st "$iname old_macro_vias_removed"
                    continue
                }
                if {$innew} {
                    if {!$dry} { odb::dbSBox_destroy $sb }
                    dict incr st "$iname core_vias_removed_[[$v getBottomLayer] getName]"
                    continue
                }
            } else {
                set l [[$sb getTechLayer] getName]
                set r [list [$sb xMin] [$sb yMin] [$sb xMax] [$sb yMax]]
                if {$l ne "TopMetal1" && [lift::ovl $r $nbh]} {
                    set pieces [lift::subtract $r $nbh]
                    set sw [$sb getSWire]; set ty [$sb getWireShapeType]; set lay [$sb getTechLayer]
                    if {!$dry} {
                        odb::dbSBox_destroy $sb
                        foreach p $pieces {
                            lassign $p x0 y0 x1 y1
                            if {$x1 - $x0 > 0 && $y1 - $y0 > 0} { odb::dbSBox_create $sw $lay $x0 $y0 $x1 $y1 $ty }
                        }
                    }
                    dict incr st "$iname cut_${l}_$ty"
                    continue
                }
            }
            lappend keep $e
        }
        set sbs $keep
        # c. new macro-grid vias
        set vianet [dict create]
        foreach ov $oldvias { lassign $ov net sw v; if {![dict exists $vianet $net]} { dict set vianet $net [list $sw $v [lindex $ov 5]] } }
        set nnew 0
        if {$dy == 0} {
            foreach ov $oldvias {
                lassign $ov net sw v vx vy ty
                if {!$dry} { odb::dbSBox_create $sw $v [expr {$vx + $dx}] $vy $ty }
                incr nnew
            }
        } else {
            set pins [macro_power_pins $inst]
            foreach e $sbs {
                lassign $e net sb
                if {[$sb isVia] || [[$sb getTechLayer] getName] ne "TopMetal1"} continue
                set r [list [$sb xMin] [$sb yMin] [$sb xMax] [$sb yMax]]
                if {![lift::ovl $r $nb] || ![dict exists $vianet $net]} continue
                lassign [dict get $vianet $net] sw v ty
                lassign $r sx0 sy0 sx1 sy1
                foreach p $pins {
                    lassign $p pnet px0 py0 px1 py1
                    if {$pnet ne $net || $py0 > $sy0 || $py1 < $sy1 || $px1 <= $sx0 || $px0 >= $sx1} continue
                    set cx [expr {($px0 + $px1) / 2}]; set cy [expr {($sy0 + $sy1) / 2}]
                    if {!$dry} { odb::dbSBox_create $sw $v $cx $cy $ty }
                    incr nnew
                }
            }
        }
        dict set st "$iname new_macro_vias" $nnew
        if {[llength $oldvias] == 0} { puts "ECO_PDN WARNING $iname: no macro-grid TopVia1 found in the old box - nothing to copy, run pdngen-based repair" }
    }
    dict for {k v} $st { puts "ECO_PDN $k $v" }
    return $st
}

# Audit (read-only): supply shapes on Metal1-Metal4 / Via1-3 overlapping any macro box, per macro. Must be 0 for the
# moved macros after the fix (other macros: compare with the pre-move value; pin-landing TopVia1 are expected).
proc pdnfix::audit {block insts} {
    set sbs [supply_sboxes $block]
    foreach inst $insts {
        set b [lift::bbox $inst]
        set c [dict create]
        foreach e $sbs {
            lassign $e net sb
            set r [list [$sb xMin] [$sb yMin] [$sb xMax] [$sb yMax]]
            if {![lift::ovl $r $b]} continue
            if {[$sb isVia]} { set v [via_of $sb]; set k "via_[[$v getBottomLayer] getName]-[[$v getTopLayer] getName]" } else { set k [[$sb getTechLayer] getName] }
            if {$k eq "TopMetal1"} continue
            dict incr c "$net:$k"
        }
        puts "ECO_PDN_AUDIT [$inst getName] [expr {[dict size $c] ? $c : {clean}}]"
    }
}

# standalone mode
if {[env_or PDNFIX_STANDALONE 0]} {
    read_db $::env(IN_ODB)
    set block [ord::get_db_block]
    set dbu [$block getDbUnitsPerMicron]
    set moves {}
    set fh [open $::env(MOVES) r]
    while {[gets $fh ln] >= 0} {
        set p [split [string trim $ln]]
        if {[llength $p] != 5} continue
        set inst [$block findInst [lindex $p 0]]
        if {$inst eq "NULL"} { puts "ECO_PDN missing [lindex $p 0]"; continue }
        lassign [lift::bbox $inst] x0 y0 x1 y1
        set w [expr {$x1 - $x0}]; set h [expr {$y1 - $y0}]
        set ox [lindex $p 1]; set oy [lindex $p 2]
        lappend moves [list $inst [list $ox $oy [expr {$ox + $w}] [expr {$oy + $h}]] [lindex $p 3] [lindex $p 4]]
    }
    close $fh
    pdnfix::fix $block $moves [expr {round([env_or PDN_HALO_UM 2] * $dbu)}] [env_or DRY 0]
    pdnfix::audit $block [lmap m $moves {lindex $m 0}]
    if {![env_or DRY 0]} { write_db $::env(OUT_ODB); puts "ECO_PDN done $::env(OUT_ODB)" }
}
