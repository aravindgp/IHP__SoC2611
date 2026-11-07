# Nets connected to the instances listed in CELLS_TXT: signal nets, plus clock/other non-supply nets when
# ALLNETS=1 (a moved flop's CLK pin is on a CLOCK net; 4 Nov run F v2 died on exactly that).
# env: IN_ODB CELLS_TXT OUT_TXT [ALLNETS=0]
proc env_or {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
set allnets [env_or ALLNETS 0]
read_db $::env(IN_ODB)
set block [ord::get_db_block]
set fh [open $::env(CELLS_TXT) r]
set names [split [string trim [read $fh]] "\n"]
close $fh
set nets [dict create]
set n 0
foreach nm $names {
    set inst [$block findInst $nm]
    if {$inst eq "NULL"} { continue }
    incr n
    foreach it [$inst getITerms] {
        set net [$it getNet]
        if {$net eq "NULL"} { continue }
        set st [$net getSigType]
        if {$st eq "SIGNAL" || ($allnets && $st ni {POWER GROUND})} { dict set nets [$net getName] 1 }
    }
}
set fo [open $::env(OUT_TXT) w]
dict for {k _} $nets { puts $fo $k }
close $fo
puts "CELLS_TO_NETS $n instances -> [dict size $nets] signal nets -> $::env(OUT_TXT)"
