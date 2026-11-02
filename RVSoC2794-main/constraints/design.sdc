###############################################################################
# Created by write_sdc
# Sat Oct 31 21:49:00 2026
###############################################################################
current_design dgrid_soc1_chip_top
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name core_clock -period 10.0000 [get_ports {clk_x2_in}]
set_clock_uncertainty 0.1500 core_clock
create_generated_clock -name clk_main -source [get_ports {clk_x2_in}] -edges {1 2 5} [get_pins {clk_gen_i/icg_main_i/u_icg/GCLK}]
set_clock_uncertainty 0.1500 clk_main
create_generated_clock -name clk_camera -source [get_ports {clk_x2_in}] -edges {1 2 9} [get_pins {clk_gen_i/icg_cam_i/u_icg/GCLK}]
set_clock_uncertainty 0.1500 clk_camera
create_generated_clock -name cam_mclk -source [get_pins {clk_gen_i/icg_cam_i/u_icg/GCLK}] -divide_by 2 [get_pins {soc_i/gen_camera_camera_inst/_1577_/Q}]
set_clock_uncertainty 0.1500 cam_mclk
create_generated_clock -name hb_ck -source [get_pins {clk_gen_i/icg_main_i/u_icg/GCLK}] -edges {2 4 6} [get_ports {hb_ck_out}]
set_clock_uncertainty 0.1500 hb_ck
create_clock -name cam_pclk -period 41.6660 [get_ports {cam_pclk_in}]
set_clock_uncertainty 0.1500 cam_pclk
create_clock -name hb_rwds -period 40.0000 [get_ports {hb_rwds_in}]
set_clock_uncertainty 0.1500 hb_rwds
create_clock -name jtag_tck -period 100.0000 [get_ports {jtag_tck_in}]
set_clock_uncertainty 0.1500 jtag_tck
set_clock_groups -name group1 -asynchronous \
 -group [get_clocks {cam_pclk}]\
 -group [get_clocks {hb_rwds}]\
 -group [get_clocks {jtag_tck}]\
 -group [list [get_clocks {cam_mclk}]\
           [get_clocks {clk_camera}]\
           [get_clocks {clk_main}]\
           [get_clocks {core_clock}]\
           [get_clocks {hb_ck}]]
set_input_delay 5.0000 -clock [get_clocks {cam_pclk}] -add_delay [get_ports {cam_d_in[0]}]
set_input_delay 5.0000 -clock [get_clocks {cam_pclk}] -add_delay [get_ports {cam_d_in[1]}]
set_input_delay 5.0000 -clock [get_clocks {cam_pclk}] -add_delay [get_ports {cam_d_in[2]}]
set_input_delay 5.0000 -clock [get_clocks {cam_pclk}] -add_delay [get_ports {cam_d_in[3]}]
set_input_delay 5.0000 -clock [get_clocks {cam_pclk}] -add_delay [get_ports {cam_d_in[4]}]
set_input_delay 5.0000 -clock [get_clocks {cam_pclk}] -add_delay [get_ports {cam_d_in[5]}]
set_input_delay 5.0000 -clock [get_clocks {cam_pclk}] -add_delay [get_ports {cam_d_in[6]}]
set_input_delay 5.0000 -clock [get_clocks {cam_pclk}] -add_delay [get_ports {cam_d_in[7]}]
set_input_delay 5.0000 -clock [get_clocks {cam_pclk}] -add_delay [get_ports {cam_hs_in}]
set_input_delay 5.0000 -clock [get_clocks {cam_pclk}] -add_delay [get_ports {cam_vs_in}]
set_input_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {gpio_in[0]}]
set_input_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {gpio_in[1]}]
set_input_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {gpio_in[2]}]
set_input_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {gpio_in[3]}]
set_input_delay 0.5000 -clock [get_clocks {hb_rwds}] -min -add_delay [get_ports {hb_dq_in[0]}]
set_input_delay 2.0000 -clock [get_clocks {hb_rwds}] -max -add_delay [get_ports {hb_dq_in[0]}]
set_input_delay 0.5000 -clock [get_clocks {hb_rwds}] -min -add_delay [get_ports {hb_dq_in[1]}]
set_input_delay 2.0000 -clock [get_clocks {hb_rwds}] -max -add_delay [get_ports {hb_dq_in[1]}]
set_input_delay 0.5000 -clock [get_clocks {hb_rwds}] -min -add_delay [get_ports {hb_dq_in[2]}]
set_input_delay 2.0000 -clock [get_clocks {hb_rwds}] -max -add_delay [get_ports {hb_dq_in[2]}]
set_input_delay 0.5000 -clock [get_clocks {hb_rwds}] -min -add_delay [get_ports {hb_dq_in[3]}]
set_input_delay 2.0000 -clock [get_clocks {hb_rwds}] -max -add_delay [get_ports {hb_dq_in[3]}]
set_input_delay 0.5000 -clock [get_clocks {hb_rwds}] -min -add_delay [get_ports {hb_dq_in[4]}]
set_input_delay 2.0000 -clock [get_clocks {hb_rwds}] -max -add_delay [get_ports {hb_dq_in[4]}]
set_input_delay 0.5000 -clock [get_clocks {hb_rwds}] -min -add_delay [get_ports {hb_dq_in[5]}]
set_input_delay 2.0000 -clock [get_clocks {hb_rwds}] -max -add_delay [get_ports {hb_dq_in[5]}]
set_input_delay 0.5000 -clock [get_clocks {hb_rwds}] -min -add_delay [get_ports {hb_dq_in[6]}]
set_input_delay 2.0000 -clock [get_clocks {hb_rwds}] -max -add_delay [get_ports {hb_dq_in[6]}]
set_input_delay 0.5000 -clock [get_clocks {hb_rwds}] -min -add_delay [get_ports {hb_dq_in[7]}]
set_input_delay 2.0000 -clock [get_clocks {hb_rwds}] -max -add_delay [get_ports {hb_dq_in[7]}]
set_input_delay 20.0000 -clock [get_clocks {jtag_tck}] -add_delay [get_ports {jtag_tdi_in}]
set_input_delay 20.0000 -clock [get_clocks {jtag_tck}] -add_delay [get_ports {jtag_tms_in}]
set_input_delay 2.0000 -clock [get_clocks {core_clock}] -add_delay [get_ports {porst_n_in}]
set_input_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {spi_miso_in}]
set_input_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {uart_rx_in}]
set_output_delay 2.0000 -clock [get_clocks {core_clock}] -add_delay [get_ports {cam_mclk_out}]
set_output_delay 2.0000 -clock [get_clocks {core_clock}] -add_delay [get_ports {cam_pwdn_out}]
set_output_delay 2.0000 -clock [get_clocks {core_clock}] -add_delay [get_ports {cam_reset_out}]
set_output_delay 2.0000 -clock [get_clocks {core_clock}] -add_delay [get_ports {cam_scl_out}]
set_output_delay 2.0000 -clock [get_clocks {core_clock}] -add_delay [get_ports {cam_sda_oe_out}]
set_output_delay 2.0000 -clock [get_clocks {core_clock}] -add_delay [get_ports {cam_sda_out}]
set_output_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {gpio_out[0]}]
set_output_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {gpio_out[1]}]
set_output_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {gpio_out[2]}]
set_output_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {gpio_out[3]}]
set_output_delay 2.0000 -clock [get_clocks {core_clock}] -add_delay [get_ports {hb_ck_out}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_csn_out}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_csn_out}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_dq_oe_out}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_dq_oe_out}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_dq_out[0]}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_dq_out[0]}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_dq_out[1]}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_dq_out[1]}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_dq_out[2]}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_dq_out[2]}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_dq_out[3]}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_dq_out[3]}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_dq_out[4]}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_dq_out[4]}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_dq_out[5]}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_dq_out[5]}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_dq_out[6]}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_dq_out[6]}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_dq_out[7]}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_dq_out[7]}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_resetn_out}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_resetn_out}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_rwds_oe_out}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_rwds_oe_out}]
set_output_delay -1.0000 -clock [get_clocks {hb_ck}] -min -add_delay [get_ports {hb_rwds_out}]
set_output_delay 3.0000 -clock [get_clocks {hb_ck}] -max -add_delay [get_ports {hb_rwds_out}]
set_output_delay 20.0000 -clock [get_clocks {jtag_tck}] -add_delay [get_ports {jtag_tdo_out}]
set_output_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {spi_csn_out}]
set_output_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {spi_mosi_out}]
set_output_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {spi_sclk_out}]
set_output_delay 2.0000 -clock [get_clocks {clk_main}] -add_delay [get_ports {uart_tx_out}]
set_false_path\
    -from [get_ports {porst_n_in}]
set_false_path\
    -to [list [get_ports {cam_mclk_out}]\
           [get_ports {cam_pwdn_out}]\
           [get_ports {cam_reset_out}]\
           [get_ports {cam_scl_out}]\
           [get_ports {cam_sda_oe_out}]\
           [get_ports {cam_sda_out}]\
           [get_ports {hb_ck_out}]]
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################
