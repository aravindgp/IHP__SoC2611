# Hard west channel (option 2): shift SRAM column 1 (the 8 macros at x 365.7 um, y < 1.7 mm) east by DX um into the
# clean gap between SRAM columns 1 and 2, moving their TopMetal1->Metal4 power vias with them, deleting the PDN
# via stacks / pieces and the std-cell row segments that the new footprint covers, pushing the displaced cells into
# the remaining gap and legalising, then check_placement. Writes the lists of ripped nets for the re-route step.
# env: IN_ODB OUT_ODB [DX=32] OUTDIR
proc env_or {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set tech [[ord::get_db] getTech]
set DX [expr {int([env_or DX 32] * 1000)}]
set OUT [env_or OUTDIR .]
set CX0 365700; set CX1 782340; set CY0 365200; set CY1 1665400     ;# column-1 bbox (dbu)
set NX1 [expr {$CX1 + $DX}]                                          ;# new east edge of the column
set GX1 832260                                                       ;# east edge of the gap (column 2 starts)
# 1. the macros and their nets
set macros {}; set ripnets [dict create]
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock]} { continue }
    set bb [$inst getBBox]
    if {abs([$bb xMin] - $CX0) < 2000 && [$bb yMin] >= $CY0 - 2000 && [$bb yMax] <= $CY1 + 2000} {
        lappend macros $inst
        foreach it [$inst getITerms] { set n [$it getNet]; if {$n ne "NULL" && [$n getSigType] eq "SIGNAL"} { dict set ripnets [$n getName] 1 } }
    }
}
puts "COL1_SHIFT [llength $macros] macros, [dict size $ripnets] macro signal nets, DX = [expr {$DX/1000.0}] um"
if {[llength $macros] != 8} { puts "COL1_SHIFT ERROR expected 8 macros"; exit 1 }
# 2. std cells under the new footprint (gap x CX1..NX1) -> move +DX into the rest of the gap; their nets are ripped
set moved 0
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    if {[$m isBlock] || [$m isPad] || [$m isCover]} { continue }
    set bb [$inst getBBox]
    if {[$bb xMax] > $CX1 && [$bb xMin] < $NX1 && [$bb yMin] >= $CY0 && [$bb yMax] <= $CY1} {
        lassign [$inst getLocation] x y
        $inst setPlacementStatus PLACED
        $inst setLocation [expr {$x + $DX}] $y
        incr moved
        foreach it [$inst getITerms] { set n [$it getNet]; if {$n ne "NULL" && [$n getSigType] eq "SIGNAL"} { dict set ripnets [$n getName] 1 } }
    }
}
puts "COL1_SHIFT moved $moved std cells by +DX"
# 3. rows: shorten every row segment that lies in the gap so it starts at NX1 (site-aligned)
set nrow 0; set site_w 0; set nseen 0
foreach row [$block getRows] {
    set bb [$row getBBox]
    if {[$bb xMax] > $CX1 && [$bb xMin] < $NX1 && [$bb yMin] >= $CY0 - 5000 && [$bb yMax] <= $CY1 + 5000} {
        incr nseen
        if {$nseen <= 3} { puts "COL1_SHIFT row seen: [$row getName] x [$bb xMin]..[$bb xMax] y [$bb yMin]..[$bb yMax] sites [$row getSiteCount]" }
    }
    if {[$bb xMin] >= $CX1 - 5000 && [$bb xMin] < $NX1 && [$bb xMax] <= $GX1 + 5000 && [$bb yMin] >= $CY0 - 5000 && [$bb yMax] <= $CY1 + 5000} {
        set site [$row getSite]; set site_w [$site getWidth]
        set ox [$bb xMin]; set oy [$bb yMin]
        set nskip [expr {int(ceil(double($NX1 - $ox) / $site_w))}]
        set nsites [expr {[$row getSiteCount] - $nskip}]
        set name [$row getName]; set orient [$row getOrient]; set dir [$row getDirection]; set sp [$row getSpacing]
        odb::dbRow_destroy $row
        if {$nsites > 0} { odb::dbRow_create $block $name $site [expr {$ox + $nskip * $site_w}] $oy $orient $dir $nsites $sp }
        incr nrow
    }
}
puts "COL1_SHIFT re-cut $nrow row segments (site [expr {$site_w/1000.0}] um)"
# 4. PDN: translate the vias/pieces that sit on the macros; delete what is under the new footprint in the gap
set nmv 0; set ndel 0
foreach nn {VDD VSS} {
    set net [$block findNet $nn]
    foreach sw [$net getSWires] {
        set todo {}
        foreach b [$sw getWires] {
            set bx0 [$b xMin]; set bx1 [$b xMax]; set by0 [$b yMin]; set by1 [$b yMax]
            if {$by1 < $CY0 || $by0 > $CY1} { continue }
            set onmacro 0
            foreach mi $macros { set mb [$mi getBBox]
                if {$bx0 >= [$mb xMin] && $bx1 <= [$mb xMax] && $by0 >= [$mb yMin] && $by1 <= [$mb yMax]} { set onmacro 1; break } }
            if {$onmacro} {
                if {[$b isVia]} {
                    set tv [$b getTechVia]
                    if {$tv ne "NULL"} { set via $tv } else { set via [$b getBlockVia] }
                    set vn [$via getName]
                    if {[string match "via4_5*" $vn] || [string match "*TopVia1*" $vn]} { lappend todo [list via $b $via [expr {($bx0+$bx1)/2}] [expr {($by0+$by1)/2}]] }
                } else {
                    set ln [[$b getTechLayer] getName]
                    if {$ln eq "Metal4"} { lappend todo [list rect $b [$b getTechLayer] $bx0 $by0 $bx1 $by1] }
                }
            } elseif {$bx0 >= $CX1 - 1 && $bx1 <= $NX1 + 1} {
                # in the part of the gap the macro moves into: via stacks / pieces on Metal1-4 feed cells that leave
                if {[$b isVia]} { set tv [$b getTechVia]; if {$tv ne "NULL"} { set vn [$tv getName] } else { set vn [[$b getBlockVia] getName] }
                    if {![string match "via4_5*" $vn] && ![string match "*TopVia1*" $vn]} { lappend todo [list del $b] } else { lappend todo [list del $b] }
                } else { if {[[$b getTechLayer] getName] ne "TopMetal1"} { lappend todo [list del $b] } }
            }
        }
        foreach t $todo {
            switch [lindex $t 0] {
                via  { lassign $t _ b via cx cy; odb::dbSBox_destroy $b; odb::dbSBox_create $sw $via [expr {$cx + $DX}] $cy STRIPE; incr nmv }
                rect { lassign $t _ b l x0 y0 x1 y1; odb::dbSBox_destroy $b; odb::dbSBox_create $sw $l [expr {$x0 + $DX}] $y0 [expr {$x1 + $DX}] $y1 STRIPE; incr nmv }
                del  { odb::dbSBox_destroy [lindex $t 1]; incr ndel }
            }
        }
    }
}
puts "COL1_SHIFT PDN: moved $nmv shapes with the macros, deleted $ndel in the gap"
# 5. move the macros
foreach mi $macros {
    set st [$mi getPlacementStatus]
    $mi setPlacementStatus PLACED
    lassign [$mi getLocation] x y
    $mi setLocation [expr {$x + $DX}] $y
    $mi setPlacementStatus $st
}
puts "COL1_SHIFT macros moved: [lindex [[lindex $macros 0] getLocation] 0] .. (x of first macro, dbu)"
# 6. rip the routing of the affected nets (macro nets + moved-cell nets); wires over the old gap are handled by the
#    DEF region pass outside (def_region_nets.py) because dbWire shapes are not iterable from Tcl here
set fh [open $OUT/ripnets_shift.txt w]
set nr 0
dict for {nm _} $ripnets { set net [$block findNet $nm]; if {$net eq "NULL"} { continue }; set w [$net getWire]; if {$w ne "NULL"} { odb::dbWire_destroy $w; incr nr }; puts $fh $nm }
close $fh
puts "COL1_SHIFT ripped $nr routed nets ([dict size $ripnets] listed) -> $OUT/ripnets_shift.txt"
# 7. legalise the moved cells and check. The bondpad BPins were dropped for DRT (DRT-0302) and detailed_placement
#    refuses BTerms without shapes -> restore them from BPINS_TCL for this step, then drop them again.
if {[env_or BPINS_TCL ""] ne ""} { source $::env(BPINS_TCL); puts "COL1_SHIFT bondpad pins restored for placement" }
write_def $OUT/shift.def
detailed_placement
check_placement -verbose
puts "COL1_SHIFT placement check done"
if {[env_or BPINS_TCL ""] ne ""} {
    set nb 0
    foreach bt [$block getBTerms] {
        if {[string match *_PAD [$bt getName]] || [$bt getName] in {VDD VSS IOVDD IOVSS}} {
            foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp; incr nb }
        }
    }
    puts "COL1_SHIFT bondpad pins dropped again ($nb)"
}
write_db $::env(OUT_ODB)
puts "COL1_SHIFT wrote $::env(OUT_ODB)"
