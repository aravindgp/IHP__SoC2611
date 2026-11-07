# Windowed DRC map: drt::check_drc -box (DBU) over a grid of windows, each small enough to stay under the checker's
# 10,000-per-type cap, prints one line per window: DRC_GRID x0 y0 x1 y1 <markers>.  env: IN_ODB GRID_UM (default
# 1000) OUT_DIR [THREADS=4] [X0 Y0 X1 Y1 um, default the core 340..6260].
read_db $::env(IN_ODB)
set_thread_count [expr {[info exists ::env(THREADS)] ? $::env(THREADS) : 4}]
set g [expr {[info exists ::env(GRID_UM)] ? $::env(GRID_UM) : 1000}]
set out $::env(OUT_DIR)
file mkdir $out
set t0 [clock seconds]
set X0 [expr {[info exists ::env(X0)] ? $::env(X0) : 340}]; set Y0 [expr {[info exists ::env(Y0)] ? $::env(Y0) : 340}]
set X1 [expr {[info exists ::env(X1)] ? $::env(X1) : 6260}]; set Y1 [expr {[info exists ::env(Y1)] ? $::env(Y1) : 6260}]
for {set y $Y0} {$y < $Y1} {incr y $g} {
    for {set x $X0} {$x < $X1} {incr x $g} {
        set x1 [expr {min($x + $g, $X1)}]; set y1 [expr {min($y + $g, $Y1)}]
        set f $out/w_${x}_${y}.rpt
        drt::check_drc -box [list [expr {$x*1000}] [expr {$y*1000}] [expr {$x1*1000}] [expr {$y1*1000}]] -output_file $f
        set fh [open $f r]; set n 0
        while {[gets $fh ln] >= 0} { if {[string match "violation type:*" $ln]} { incr n } }
        close $fh
        puts "DRC_GRID $x $y $x1 $y1 $n"
        flush stdout
    }
}
puts "DRC_GRID_DONE t=[expr {[clock seconds]-$t0}]s"
