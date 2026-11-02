# Fast full-chip antenna check on a routed ODB (OpenROAD, LEF antenna data, multithreaded): minutes,
# vs hours for the KLayout antenna deck (2 Nov: 9 h single-threaded and still on TopMetal1).
# env: ANT_IN ANT_RPT [ANT_THREADS=4]
read_db $::env(ANT_IN)
set_thread_count [expr {[info exists ::env(ANT_THREADS)] ? $::env(ANT_THREADS) : 4}]
set n [check_antennas -report_file $::env(ANT_RPT) -verbose]
puts "ANTENNA_VIOLATIONS $n -> $::env(ANT_RPT)"
