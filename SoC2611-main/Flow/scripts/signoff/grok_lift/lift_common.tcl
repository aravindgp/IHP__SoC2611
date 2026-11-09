# lift_common.tcl - shared procs for the staged macro-move ECO (SoC2611 elbow knot, 10 Nov 2026 loop).
# Sourced by nets_under_footprint.tcl, eco_lift_staged.tcl and pdn_fix_moved_macros.tcl.
#
# odb API used here, checked against OpenROAD dcf36133 (src/odb/include/odb/db.h, dbWireCodec.h, the Tcl swig
# odb.i/dbtypes.i and the Tcl tests test_wire_codec.tcl, create_sboxes.tcl, smash_vias.tcl, gcd_pdn_def_access.tcl):
#   odb::dbWireDecoder: begin/next/getLayer/getPoint (-> {x y})/getPoint_ext (-> {x y ext})/getVia/getTechVia,
#     opcodes $odb::dbWireDecoder_PATH ... _END_DECODE  (used exactly like this in src/odb/test/test_wire_codec.tcl)
#   NOT used: odb::dbWireShapeItr / odb::dbShape - dbShape.h is only #included in odb.i, not %included, so
#     these classes are not wrapped in the Tcl API of dcf36133 (C++ only).
#   NOT used: dbWire::getBBox (returns std::optional<Rect>, no Tcl typemap for it).
#   dbWireDecoder::getRect (RECT patch opcode) has plain int& out-args without an OUTPUT typemap -> skipped
#     (patches are pin-access stubs < 1 um; harmless for this purpose).
proc env_or {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }

namespace eval lift {
    variable OP
    foreach o {PATH JUNCTION SHORT VWIRE POINT POINT_EXT VIA TECH_VIA RECT ITERM BTERM RULE END_DECODE} {
        set OP($o) [set ::odb::dbWireDecoder_$o]
    }
}

# shift file "<inst> <dx_um> <dy_um>" (same format as eco_macroshift.tcl); returns list of {inst dx_dbu dy_dbu}
proc lift::read_shifts {block file dbu} {
    set out {}
    set fh [open $file r]
    while {[gets $fh ln] >= 0} {
        set ln [string trim $ln]
        if {$ln eq "" || [string index $ln 0] eq "#"} continue
        set p [split $ln]
        if {[llength $p] != 3} continue
        set inst [$block findInst [lindex $p 0]]
        if {$inst eq "NULL"} { puts "LIFT missing instance [lindex $p 0]"; continue }
        lappend out [list $inst [expr {round([lindex $p 1] * $dbu)}] [expr {round([lindex $p 2] * $dbu)}]]
    }
    close $fh
    return $out
}

proc lift::bbox {inst} {
    set b [$inst getBBox]
    return [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}
proc lift::bloat {r d} { lassign $r a b c e; list [expr {$a - $d}] [expr {$b - $d}] [expr {$c + $d}] [expr {$e + $d}] }
proc lift::shift_box {r dx dy} { lassign $r a b c e; list [expr {$a + $dx}] [expr {$b + $dy}] [expr {$c + $dx}] [expr {$e + $dy}] }
# strict overlap (touching edges do not count)
proc lift::ovl {a b} {
    lassign $a ax0 ay0 ax1 ay1; lassign $b bx0 by0 bx1 by1
    expr {$ax0 < $bx1 && $bx0 < $ax1 && $ay0 < $by1 && $by0 < $ay1}
}
proc lift::ovl_any {r boxes} { foreach b $boxes { if {[ovl $r $b]} { return 1 } }; return 0 }
proc lift::union_bbox {boxes} {
    set x0 1e18; set y0 1e18; set x1 -1e18; set y1 -1e18
    foreach b $boxes { lassign $b a c d e
        if {$a < $x0} {set x0 $a}; if {$c < $y0} {set y0 $c}; if {$d > $x1} {set x1 $d}; if {$e > $y1} {set y1 $e} }
    list $x0 $y0 $x1 $y1
}
# box minus box (axis-aligned) -> up to 4 rectangles
proc lift::subtract {r c} {
    if {![ovl $r $c]} { return [list $r] }
    lassign $r x0 y0 x1 y1; lassign $c cx0 cy0 cx1 cy1
    set out {}
    if {$cy0 > $y0} { lappend out [list $x0 $y0 $x1 $cy0] }
    if {$cy1 < $y1} { lappend out [list $x0 $cy1 $x1 $y1] }
    set my0 [expr {max($y0, $cy0)}]; set my1 [expr {min($y1, $cy1)}]
    if {$cx0 > $x0} { lappend out [list $x0 $my0 $cx0 $my1] }
    if {$cx1 < $x1} { lappend out [list $cx1 $my0 $x1 $my1] }
    return $out
}

# Walk one dbWire with the decoder; count the segments / vias / patches whose box overlaps any of BOXES on a layer in
# LAYERS (routing layer names; a via counts if its bottom or top layer is in LAYERS). Segment box = centreline bloated
# by half the layer's default width (+ ext for POINT_EXT). Returns {hits layer_list}.
proc lift::wire_hits {wire boxes layers {via_half 300}} {
    variable OP
    set dec [odb::dbWireDecoder]
    $dec begin $wire
    set lname ""; set hw 0; set have 0; set px 0; set py 0
    set hits 0; set hl [dict create]
    while {1} {
        set op [$dec next]
        if {$op == $OP(END_DECODE)} break
        if {$op == $OP(PATH) || $op == $OP(JUNCTION) || $op == $OP(SHORT) || $op == $OP(VWIRE)} {
            set l [$dec getLayer]
            set lname [$l getName]; set hw [expr {[$l getWidth] / 2}]
            set have 0
        } elseif {$op == $OP(POINT) || $op == $OP(POINT_EXT)} {
            if {$op == $OP(POINT)} { lassign [$dec getPoint] x y; set e 0 } else { lassign [$dec getPoint_ext] x y e }
            if {$have && $lname in $layers} {
                set d [expr {$hw + $e}]
                set r [list [expr {min($px,$x) - $d}] [expr {min($py,$y) - $d}] [expr {max($px,$x) + $d}] [expr {max($py,$y) + $d}]]
                if {[ovl_any $r $boxes]} { incr hits; dict incr hl $lname }
            }
            set px $x; set py $y; set have 1
        } elseif {$op == $OP(VIA) || $op == $OP(TECH_VIA)} {
            set v [expr {$op == $OP(VIA) ? [$dec getVia] : [$dec getTechVia]}]
            set bl [[$v getBottomLayer] getName]; set tl [[$v getTopLayer] getName]
            if {$have && ($bl in $layers || $tl in $layers)} {
                set r [list [expr {$px - $via_half}] [expr {$py - $via_half}] [expr {$px + $via_half}] [expr {$py + $via_half}]]
                if {[ovl_any $r $boxes]} { incr hits; dict incr hl "$bl/$tl" }
            }
            set l [$dec getLayer]
            if {$l ne "NULL"} { set lname [$l getName]; set hw [expr {[$l getWidth] / 2}] }
        }
        # RECT / ITERM / BTERM / RULE: ignored (see header)
    }
    return [list $hits [dict keys $hl]]
}

# pin bbox of a net (instance boxes of its ITerms + BTerm boxes); {} if none
proc lift::net_pin_bbox {net} {
    set bs {}
    foreach it [$net getITerms] { lappend bs [bbox [$it getInst]] }
    foreach bt [$net getBTerms] { set r [$bt getBBox]; lappend bs [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]] }
    if {[llength $bs] == 0} { return {} }
    return [union_bbox $bs]
}

proc lift::is_clock {net} {
    expr {[$net getSigType] eq "CLOCK" || [regexp {(^|/)clknet_|clk} [$net getName]]}
}
# class: CLOCK | BIG (>= big_pins terms or >= 3 macro pins) | MED (>= 5 terms) | SMALL
proc lift::classify {net big_pins} {
    set nt [expr {[llength [$net getITerms]] + [llength [$net getBTerms]]}]
    set nm 0
    foreach it [$net getITerms] { if {[[[$it getInst] getMaster] isBlock]} { incr nm } }
    if {[is_clock $net]} { set c CLOCK } elseif {$nt >= $big_pins || $nm >= 3} { set c BIG } elseif {$nt >= 5} { set c MED } else { set c SMALL }
    return [list $c $nt $nm]
}

# Signal nets whose existing wires lie under BOXES (dbu) on LAYERS. Prefilter: the net's pin bbox bloated by MARGIN
# must touch the union of the boxes (EXHAUSTIVE=1 scans every routed net). Returns dict net_name -> {net hits layers}.
proc lift::nets_under {block boxes layers margin exhaustive} {
    set ub [union_bbox $boxes]
    set res [dict create]
    set ncand 0
    foreach net [$block getNets] {
        if {[$net getSigType] in {POWER GROUND}} continue
        set w [$net getWire]
        if {$w eq "NULL"} continue
        if {!$exhaustive} {
            set pb [net_pin_bbox $net]
            if {$pb eq "" || ![ovl [bloat $pb $margin] $ub]} continue
        }
        incr ncand
        lassign [wire_hits $w $boxes $layers] h ls
        if {$h > 0} { dict set res [$net getName] [list $net $h $ls] }
    }
    puts "LIFT scanned $ncand candidate nets, [dict size $res] with wires under the boxes"
    return $res
}

# Mark nets for a REAL re-route by the incremental GRT (OpenROAD dcf36133 GlobalRouter.cpp):
#  - updateDirtyNets() re-routes a dirty net only if pinPositionsChanged(net) (or it is an uncovered merged net);
#    otherwise it only destroys its wire and KEEPS ITS OLD GUIDES. A disconnect+reconnect of one ITerm while the
#    incremental callback is active (what eco_macroshift/eco_sidemove EXTRA_NETS do) saves the pin set at
#    PreDisconnect and finds the same set at the end -> NOT re-routed (this is what happened to the 563 nets of K2b).
#  - so: disconnect one ITerm BEFORE global_route -start_incremental (initFastRoute then builds the net with N-1 pins),
#    reconnect AFTER it (inDbITermPostConnect -> addDirtyNet saves the N-1 set; the end sees N pins -> changed).
#  - wires are destroyed BEFORE -start_incremental too: initFastRoute -> findNetsObstructions turns every existing
#    wire into capacity usage; a wire deleted by script after start_incremental stays as phantom usage
#    (destroyNetWire/removeWireUsage only runs on wires that still exist).
proc lift::predisconnect {nets_dict} {
    set rec {}; set nowire 0; set noit {}
    dict for {name net} $nets_dict {
        set its [$net getITerms]
        if {[llength $its] == 0} { lappend noit $name; continue }
        set w [$net getWire]
        if {$w ne "NULL"} { odb::dbWire_destroy $w } else { incr nowire }
        foreach g [$net getGuides] { odb::dbGuide_destroy $g }
        # prefer a std-cell ITerm (keeps macro pins untouched)
        set it [lindex $its 0]
        foreach i $its { if {![[[$i getInst] getMaster] isBlock]} { set it $i; break } }
        set modnet [$it getModNet]
        $it disconnect
        lappend rec [list $it $net $modnet]
    }
    puts "LIFT pre-disconnected [llength $rec] nets (wires destroyed before GRT init; $nowire had no wire), [llength $noit] nets without ITerms left alone"
    return $rec
}
proc lift::reconnect {rec} {
    foreach r $rec {
        lassign $r it net modnet
        if {$modnet ne "NULL"} { $it connect $net $modnet } else { $it connect $net }
    }
    puts "LIFT reconnected [llength $rec] ITerms (nets now dirty with changed pin sets)"
}
