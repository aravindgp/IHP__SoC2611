# nets_under_footprint.tcl - DRY RUN (read-only; writes no db): for a shift list, compute every moved macro's new
# footprint (+HALO) and list what a staged move must strip / push / fix:
#   1. signal nets whose existing wires (Metal1-4 segments, vias touching Metal1-4) intersect the new footprints
#   2. signal nets with a pin on a moved macro (their pins move -> full re-route anyway)
#   3. standard cells under the new footprints (+PUSH_HALO) that must be pushed out
#   4. supply shapes under the new footprints (core Metal1 rails / Metal4 stripes / Via1-3 / TopVia1) and macro-grid
#      TopVia1 vias inside the old footprints (see pdn_fix_moved_macros.tcl)
# Output STRIP_OUT lines: "<net> <class> <terms> <macro_pins> <reason> <hits> <layers>"
#   class CLOCK | BIG (>= BIG_PINS terms or >= 3 macro pins) | MED (>= 5 terms) | SMALL; reason FOOT | PIN | FOOT+PIN
# env: IN_ODB SHIFT_FILE STRIP_OUT [HALO_UM=0.5] [PUSH_HALO_UM=2] [PDN_HALO_UM=2] [MARGIN_UM=200] [EXHAUSTIVE=0]
#      [BIG_PINS=10] [LAYERS="Metal1 Metal2 Metal3 Metal4"]
source [file join [file dirname [file normalize [info script]]] lift_common.tcl]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set halo [expr {round([env_or HALO_UM 0.5] * $dbu)}]
set phalo [expr {round([env_or PUSH_HALO_UM 2] * $dbu)}]
set pdnhalo [expr {round([env_or PDN_HALO_UM 2] * $dbu)}]
set margin [expr {round([env_or MARGIN_UM 200] * $dbu)}]
set layers [env_or LAYERS "Metal1 Metal2 Metal3 Metal4"]
set big [env_or BIG_PINS 10]
set shifts [lift::read_shifts $block $::env(SHIFT_FILE) $dbu]
set moved [dict create]
set foot {}; set newb {}; set oldb {}
foreach s $shifts {
    lassign $s inst dx dy
    dict set moved [$inst getName] 1
    if {![[$inst getMaster] isBlock]} continue
    set ob [lift::bbox $inst]; set nb [lift::shift_box $ob $dx $dy]
    lappend oldb $ob; lappend newb $nb; lappend foot [lift::bloat $nb $halo]
    set uncovered [lift::subtract $nb $ob]
    set a 0.0; foreach u $uncovered { lassign $u x0 y0 x1 y1; set a [expr {$a + double($x1-$x0)*($y1-$y0)/$dbu/$dbu}] }
    puts [format "FOOT %s old (%.2f %.2f %.2f %.2f) new (%.2f %.2f %.2f %.2f) newly covered %.0f um2" [$inst getName] \
        {*}[lmap v $ob {expr {double($v)/$dbu}}] {*}[lmap v $nb {expr {double($v)/$dbu}}] $a]
}
# overlaps with other (unmoved) macros
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isBlock] || [dict exists $moved [$inst getName]]} continue
    set b [lift::bbox $inst]
    if {[lift::ovl_any $b [lmap n $newb {lift::bloat $n $pdnhalo}]]} { puts "FOOT ERROR new footprint (+PDN halo) overlaps macro [$inst getName]" }
}
# 1. wires under the new footprints
set under [lift::nets_under $block $foot $layers $margin [env_or EXHAUSTIVE 0]]
# 2. pin nets of moved instances
set pinnets [dict create]
foreach s $shifts {
    foreach it [[lindex $s 0] getITerms] {
        set n [$it getNet]
        if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} { dict set pinnets [$n getName] $n }
    }
}
set all [dict create]
dict for {k v} $under { dict set all $k [lindex $v 0] }
dict for {k v} $pinnets { dict set all $k $v }
set cnt [dict create]
set fh [open $::env(STRIP_OUT) w]
puts $fh "# net class terms macro_pins reason hits layers   (dry run of $::env(SHIFT_FILE) on $::env(IN_ODB))"
dict for {name net} $all {
    lassign [lift::classify $net $big] c nt nm
    set r [expr {[dict exists $under $name] ? ([dict exists $pinnets $name] ? "FOOT+PIN" : "FOOT") : "PIN"}]
    set h 0; set ls "-"
    if {[dict exists $under $name]} { lassign [dict get $under $name] _ h ls; set ls [join $ls ,] }
    puts $fh "$name $c $nt $nm $r $h $ls"
    dict incr cnt "$r/$c"
}
close $fh
puts "STRIP nets total [dict size $all] (under footprints [dict size $under], pin nets [dict size $pinnets])"
foreach k [lsort [dict keys $cnt]] { puts "STRIP   $k [dict get $cnt $k]" }
# 3. std cells under the new footprints
set ncell 0; set cellnets [dict create]
set pbox [lmap n $newb {lift::bloat $n $phalo}]
foreach inst [$block getInsts] {
    if {![[$inst getMaster] isCore] || [dict exists $moved [$inst getName]]} continue
    if {![lift::ovl_any [lift::bbox $inst] $pbox]} continue
    incr ncell
    foreach it [$inst getITerms] { set n [$it getNet]; if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} { dict set cellnets [$n getName] 1 } }
}
puts "PUSH std cells under new footprints (+[env_or PUSH_HALO_UM 2] um): $ncell, their signal nets: [dict size $cellnets] (re-routed too; legalizer adds more)"
# 4. supply shapes
set pbx [lmap n $newb {lift::bloat $n $pdnhalo}]
set pc [dict create]
foreach netname {VDD VSS} {
    set n [$block findNet $netname]
    if {$n eq "NULL"} continue
    foreach sw [$n getSWires] {
        foreach sb [$sw getWires] {
            set r [list [$sb xMin] [$sb yMin] [$sb xMax] [$sb yMax]]
            if {[$sb isVia]} {
                set v [expr {[$sb getTechVia] ne "NULL" ? [$sb getTechVia] : [$sb getBlockVia]}]
                set key "via:[[$v getBottomLayer] getName]-[[$v getTopLayer] getName]"
                lassign [$sb getViaXY] vx vy
                set pt [list $vx $vy [expr {$vx+1}] [expr {$vy+1}]]
                if {[lift::ovl_any $pt $oldb]} { dict incr pc "$netname old-footprint $key" }
                if {[lift::ovl_any $pt $pbx] && ![lift::ovl_any $pt $oldb]} { dict incr pc "$netname new-footprint $key" }
            } else {
                set key [[$sb getTechLayer] getName]
                if {$key eq "TopMetal1"} { if {[lift::ovl_any $r $newb]} { dict incr pc "$netname straps-crossing-new TopMetal1" } ; continue }
                if {[lift::ovl_any $r $pbx]} { dict incr pc "$netname new-footprint [set key]([$sb getWireShapeType])" }
            }
        }
    }
}
foreach k [lsort [dict keys $pc]] { puts "PDN $k [dict get $pc $k]" }
puts "NETS_UNDER_FOOTPRINT done $::env(STRIP_OUT)"
