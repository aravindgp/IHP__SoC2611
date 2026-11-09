# Cross-check: place the generated pad ring with OpenROAD (padring.tcl) on a pad-only netlist,
# write DEF; compare_padring.py then checks every instance against padring.gds.
# env: PDK_ROOT, PADRING_DIR (output dir of make_padring.py)
set pdk $::env(PDK_ROOT)/ihp-sg13cmos5l/libs.ref
set pr  $::env(PADRING_DIR)
read_lef $pdk/sg13cmos5l_stdcell/lef/sg13cmos5l_tech.lef
read_lef $pdk/sg13cmos5l_stdcell/lef/sg13cmos5l_stdcell.lef
read_lef $pdk/sg13cmos5l_io/lef/sg13cmos5l_io.lef
read_lef $pr/bondpad_70x70.lef
read_verilog $pr/padring_stub.v
link_design dgrid_padring
initialize_floorplan -die_area {0 0 6600 6600} -core_area {340 340 6260 6260} -site CoreSite
source $pr/padring.tcl
write_def $pr/padring_openroad.def
puts "PADRING_OPENROAD_OK"
