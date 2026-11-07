# Floorplan geometry for floorplan_svg.py: die/core, macros, pad cells, wide PDN stripes. env: IN_ODB OUT_TXT
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set fh [open $::env(OUT_TXT) w]
set die [$block getDieArea]
puts $fh "DIE [$die xMin] [$die yMin] [$die xMax] [$die yMax]"
set core [$block getCoreArea]
puts $fh "CORE [$core xMin] [$core yMin] [$core xMax] [$core yMax]"
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    set bb [$inst getBBox]
    if {[$m isBlock]} {
        puts $fh "MACRO [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$m getName] [$inst getOrient] [$inst getName]"
    } elseif {[$m isPad] || [string match "*IO*" [$m getName]] || [string match "*Corner*" [$m getName]] || [string match "*bondpad*" [$m getName]]} {
        puts $fh "PAD [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$m getName] [$inst getName]"
    }
}
foreach nn {VDD VSS} {
    set net [$block findNet $nn]
    if {$net eq "NULL"} { continue }
    foreach sw [$net getSWires] {
        foreach b [$sw getWires] {
            if {[$b isVia]} { continue }
            set l [[$b getTechLayer] getName]
            set w [expr {min([$b getDX], [$b getDY])}]
            if {$w < 1500} { continue }
            puts $fh "PDN $nn $l [$b xMin] [$b yMin] [$b xMax] [$b yMax]"
        }
    }
}
close $fh
puts "DUMP_FLOORPLAN done"
