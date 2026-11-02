# Write Verilog + DEF of an ODB:  IN_ODB=... OUT_V=... OUT_DEF=... openroad -exit write_v.tcl
read_db $::env(IN_ODB)
write_verilog $::env(OUT_V)
write_def $::env(OUT_DEF)
