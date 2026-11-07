# Placement geometry for density_map.py: die/core, rows, macros, pads, every std cell box with its PCORE owner.
# env: IN_ODB OUT_TXT.  Units: dbu.  Owner: PCORE n from gen_reg\[n\]_gen1_pcore in the hierarchical name, else '-'.
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set fh [open $::env(OUT_TXT) w]
set die [$block getDieArea]
puts $fh "DIE [$die xMin] [$die yMin] [$die xMax] [$die yMax]"
set core [$block getCoreArea]
puts $fh "CORE [$core xMin] [$core yMin] [$core xMax] [$core yMax]"
foreach row [$block getRows] {
    set bb [$row getBBox]
    puts $fh "ROW [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]"
}
set nc 0
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    set bb [$inst getBBox]
    if {[$m isBlock]} {
        puts $fh "MACRO [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$m getName] [$inst getName]"
    } elseif {[$m isPad] || [string match "*IO*" [$m getName]] || [string match "*Corner*" [$m getName]] || [string match "*bondpad*" [$m getName]]} {
        puts $fh "PAD [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$m getName]"
    } elseif {[$m isCore] || [$m isCoreAutocorner]} {
        set own -
        if {[regexp {gen_reg\\?\[(\d)\\?\]_gen1_pcore} [$inst getName] -> n]} { set own $n }
        puts $fh "C [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] $own"
        incr nc
    }
}
close $fh
puts "DUMP_DENSITY done cells=$nc"
