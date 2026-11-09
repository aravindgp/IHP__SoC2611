# IHP SG13CMOS5L power grid for DGSE pnr.tcl (pdngen command form, same shape as sky130hd/pdn.tcl and
# the gf180-dgse overlay: this file only DEFINES the grid; pnr.tcl runs pdngen and check_power_grid).
#
# Stack: Metal1 (H) Metal2 (V) Metal3 (H) Metal4 (V) TopMetal1 (H, 2 um thick). No Metal5 / TopMetal2,
# so the ORFS ihp-sg13g2 grid (TopMetal1 + TopMetal2 straps, ring on both) cannot be used as is.
# Layer choice follows IHP's own LibreLane config for this PDK (libs.tech/librelane/config.tcl):
#   rails            Metal1   followpins              (FP_PDN_RAIL_LAYER)
#   vertical straps  Metal4   width 1.0 spacing 2.0 pitch 50 offset 10   (FP_PDN_V*)
#   horizontal straps TopMetal1 width 2.0 spacing 4.0 pitch 50 offset 10  (FP_PDN_H*)
#   core ring        Metal4 (vertical sides) + TopMetal1 (horizontal sides)
# Rail width 0.44 is the std-cell VDD/VSS pin height (sg13cmos5l_stdcell.lef: RECT 0 3.56 1.92 4.0),
# pitch 7.56 = 2 rows of 3.78 -- the same numbers ORFS uses for sg13g2.
# Ring widths/spacings are ORFS's (5.0 / 2.0), NOT LibreLane's core-ring defaults (2.0 / 1.0): a 1.0 um
# spacing is below TopMetal1's minimum spacing of 1.64 um (tech LEF), so LibreLane's value would DRC.
#
# SRAM macros (RM_IHPSG13_1P/2P_*, LEF from sg13g2_sram): power pins are VDD! / VSS! / VDDARRAY!
# (LEF names end in '!'; Liberty pg_pins VDD / VSS / VDDARRAY), all on Metal4 as VERTICAL stripes
# (2.81 um wide, 40+ per macro) running the full macro height; OBS on Metal1..Metal4, nothing on
# TopMetal1. So the macro grid connects Metal4 (macro pins) to the TopMetal1 horizontal straps that
# cross over the macro (-grid_over_boundary). This only works for macros in R0/R180/MX/MY: a R90/R270
# macro turns its Metal4 pins horizontal, parallel to TopMetal1, and gets NO connection (pdngen cannot
# draw vertical TopMetal1). macro_floorplan.py therefore emits R0/MX only. VDDARRAY! is the array
# supply (separate pg_pin for retention); it is tied to VDD here (one 1.2 V domain).
# IR drop: 274 macros + 20 mm2 of cells on a ~40 mm2 die with 1 um Metal4 / 2 um TopMetal1 straps at
# 50 um pitch is the LibreLane starting point, not a verdict -- judge it with `dgse-pd pdn` on the
# floorplan checkpoint; the denser alternative is commented below.
#
# SoC2611 run variant (HW/asic/dgse/runs/cmos5l-01, config pdn_tcl): TopMetal1 straps at 16 um pitch (see the
# macro grid note) and row slivers removed. cut_rows on the explicit-placement path has no -row_min_width, so the
# gaps between shelf-packed macros leave row fragments a few um wide that no Metal4 strap reaches (PSM-0038 on VSS).
set _dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set _ndel 0
foreach _r [[ord::get_db_block] getRows] {
    set _b [$_r getBBox]
    if {([$_b xMax] - [$_b xMin]) / double($_dbu) < 60.0} { odb::dbRow_destroy $_r; incr _ndel }
}
puts "DGSE_INFO pdn_c5l_sram: removed $_ndel row fragment(s) narrower than 60 um"

####################################
# global connections
####################################
# standard cells (sg13cmos5l_stdcell: pins VDD / VSS)
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSSE$}
# SRAM macros (RM_IHPSG13_*): VDD! VDDARRAY! VSS!
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD!$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDARRAY!$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS!$} -ground
# pad ring (sg13cmos5l_io: vdd / vss core supply pins, iovdd / iovss 3.3 V supply pins), only when the
# netlist instantiates pads -- otherwise the IOVDD/IOVSS nets must not be created (check_power_grid
# would then fail on an empty net).
set _dgse_has_pads 0
foreach _i [[ord::get_db_block] getInsts] {
    if {[string match "sg13cmos5l_IOPad*" [[$_i getMaster] getName]]} { set _dgse_has_pads 1; break }
}
if {$_dgse_has_pads} {
    add_global_connection -net {VDD}   -inst_pattern {.*} -pin_pattern {^vdd$} -power
    add_global_connection -net {VSS}   -inst_pattern {.*} -pin_pattern {^vss$} -ground
    add_global_connection -net {IOVDD} -inst_pattern {.*} -pin_pattern {^iovdd$} -power
    add_global_connection -net {IOVSS} -inst_pattern {.*} -pin_pattern {^iovss$} -ground
    puts "DGSE_INFO pdn: pad ring present -- IOVDD/IOVSS connected, core ring connects to pads"
}
global_connect

####################################
# voltage domain
####################################
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}

####################################
# standard-cell grid
####################################
define_pdn_grid -name {grid} -voltage_domains {CORE}
if {$_dgse_has_pads} {
    add_pdn_ring -grid {grid} -layers {Metal4 TopMetal1} -widths {5.0 5.0} -spacings {2.0 2.0} \
        -core_offsets {4.5} -connect_to_pads
} else {
    add_pdn_ring -grid {grid} -layers {Metal4 TopMetal1} -widths {5.0 5.0} -spacings {2.0 2.0} \
        -core_offsets {4.5}
}
# Metal1 rails on the cell rows
add_pdn_stripe -grid {grid} -layer {Metal1} -width {0.44} -pitch {7.56} -offset {0} -followpins \
    -extend_to_core_ring
# Metal4 vertical straps (LibreLane FP_PDN_V*: 1.0 / 2.0 / 50 / 10)
add_pdn_stripe -grid {grid} -layer {Metal4} -width {1.0} -spacing {2.0} -pitch {50.0} -offset {10.0} \
    -extend_to_core_ring
# TopMetal1 horizontal straps (LibreLane FP_PDN_H*: 2.0 / 4.0 / 50 / 10). Every macro (min height
# 64.36 um) is crossed by at least one VDD/VSS pair at this pitch.
# v2 (congestion): only VDD needs the dense pitch (VDDARRAY! 19 um band); VSS! spans 0-38.8 um of every macro.
add_pdn_stripe -grid {grid} -layer {TopMetal1} -nets {VDD} -width {1.8} -pitch {16.0} -offset {2.0} -extend_to_core_ring
add_pdn_stripe -grid {grid} -layer {TopMetal1} -nets {VSS} -width {1.8} -pitch {32.0} -offset {10.0} -extend_to_core_ring
# denser alternative for IR (uncomment, comment the two lines above):
# add_pdn_stripe -grid {grid} -layer {Metal4}    -width {2.0} -spacing {2.0} -pitch {40.0} -offset {10.0} -extend_to_core_ring
# add_pdn_stripe -grid {grid} -layer {TopMetal1} -width {4.0} -spacing {4.0} -pitch {30.0} -offset {10.0} -extend_to_core_ring
# Via stacks: Metal1 -> Via1 -> Metal2 -> Via2 -> Metal3 -> Via3 -> Metal4 (via1Array..via3Array
# GENERATE rules in the tech LEF), Metal4 -> TopVia1 -> TopMetal1 (viaTop1Array). Plain connects, as in
# gf180-dgse (no -max_columns/-split_cuts).
add_pdn_connect -grid {grid} -layers {Metal1 Metal4}
add_pdn_connect -grid {grid} -layers {Metal4 TopMetal1}

####################################
# macro grids (SRAM): Metal4 pins to the TopMetal1 straps crossing the macro
####################################
define_pdn_grid -name {CORE_macro_grid_1} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} \
    -halo {2.0 2.0 2.0 2.0} -default -grid_over_boundary
# 2026-10-30 (c2 runs): the 64-row SRAMs (1P_64x16/64x64, 2P_64x22/64x32) have VDDARRAY! only in a 19 um band
# (y 45.5-64.4 of the LEF); the 50 um core TopMetal1 pitch missed it on 63 macros (PSM-0069). Own dense
# core TopMetal1 straps at 16 um pitch (width 1.8, spacing 2.0): a 1.8 um VDD strap lies fully inside any 18.9 um
# band. (A macro-grid stripe set instead cut the core straps over the macros and left them as islands.)
add_pdn_connect -grid {CORE_macro_grid_1} -layers {Metal4 TopMetal1}
# Rotated macros would not connect (see header); keep the grid so pdngen reports them instead of
# silently skipping, and let check_power_grid fail the run.
define_pdn_grid -name {CORE_macro_grid_2} -voltage_domains {CORE} -macro -orient {R90 R270 MXR90 MYR90} \
    -halo {2.0 2.0 2.0 2.0} -default -grid_over_boundary
add_pdn_connect -grid {CORE_macro_grid_2} -layers {Metal4 TopMetal1}
