# After the chip-level DRT (drt_steps.tcl on chip_grt.tcl's output): re-create the bondpad pins and write
# chip.odb / chip.def / chip.v (what chip_integrate.tcl stage "write" does).
# env: IN_ODB (routed chip ODB)  BPINS_TCL (from chip_grt.tcl)  OUT_DIR
read_db $::env(IN_ODB)
source $::env(BPINS_TCL)
file mkdir $::env(OUT_DIR)
write_db $::env(OUT_DIR)/chip.odb
write_def $::env(OUT_DIR)/chip.def
write_verilog $::env(OUT_DIR)/chip.v
puts "CHIP_FINISH done $::env(OUT_DIR)"
