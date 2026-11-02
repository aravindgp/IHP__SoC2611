# HW/asic/constraints/dgrid_soc1_chip.sdc adapted to the Yosys netlist names and to the engine's clock block
# (pnr.tcl already did: create_clock core_clock 10 ns on clk_x2_in, uncertainty, default IO delays vs core_clock).
# Yosys renamed the divider flops: clk_div2_i/div_r_reg -> clk_div2_i/_2_, camera sys_clk_reg -> _1577_.
create_generated_clock -name clk_main -divide_by 2 -source [get_ports clk_x2_in] [get_pins clk_div2_i/_2_/Q]
create_generated_clock -name clk_camera -divide_by 2 -source [get_pins clk_div2_i/_2_/Q] [get_pins clk_cam_i/_2_/Q]
create_generated_clock -name cam_mclk -divide_by 2 -source [get_pins clk_cam_i/_2_/Q] \
    [get_pins soc_i/gen_camera_camera_inst/_1577_/Q]
create_generated_clock -name hb_ck -divide_by 2 -edges {2 4 6} -source [get_pins clk_div2_i/_2_/Q] [get_ports hb_ck_out]
create_clock -name cam_pclk -period 41.666 [get_ports cam_pclk_in]
create_clock -name hb_rwds  -period 40.000 [get_ports hb_rwds_in]
# JTAG TCK (not in the project SDC): 10 MHz, asynchronous
create_clock -name jtag_tck -period 100.0 [get_ports jtag_tck_in]

set_clock_groups -asynchronous \
   -group {core_clock clk_main clk_camera cam_mclk hb_ck} \
   -group {hb_rwds} -group {cam_pclk} -group {jtag_tck}

set_false_path -from [get_ports porst_n_in]
# replace the engine's blanket IO delays on the project ports
unset_input_delay -clock core_clock [get_ports {cam_pclk_in hb_rwds_in jtag_tck_in}]
set_output_delay -clock hb_ck -max  3.0 [get_ports {hb_csn_out* hb_resetn_out hb_rwds_out hb_rwds_oe_out hb_dq_out* hb_dq_oe_out}]
set_output_delay -clock hb_ck -min -1.0 [get_ports {hb_csn_out* hb_resetn_out hb_rwds_out hb_rwds_oe_out hb_dq_out* hb_dq_oe_out}]
set_input_delay  -clock hb_rwds -max 2.0 [get_ports {hb_dq_in*}]
set_input_delay  -clock hb_rwds -min 0.5 [get_ports {hb_dq_in*}]
# OpenSTA has no set_max_delay -datapath_only; the hb_rwds <-> clk_main crossing is covered by the async groups
# (the project SDC's 10 ns bound is not applied here)
set_input_delay  -clock cam_pclk 5.0 [get_ports {cam_d_in* cam_vs_in cam_hs_in}]
set_input_delay  -clock clk_main 2.0 [get_ports {gpio_in* uart_rx_in spi_miso_in}]
set_output_delay -clock clk_main 2.0 [get_ports {gpio_out* uart_tx_out spi_*_out}]
set_input_delay  -clock jtag_tck 20.0 [get_ports {jtag_tms_in jtag_tdi_in}]
set_output_delay -clock jtag_tck 20.0 [get_ports {jtag_tdo_out}]
set_false_path -to [get_ports {cam_scl_out cam_sda_out cam_sda_oe_out cam_reset_out cam_pwdn_out cam_mclk_out hb_ck_out}]
set_clock_uncertainty 0.15 [get_clocks {clk_main clk_camera cam_mclk hb_ck cam_pclk hb_rwds jtag_tck}]
