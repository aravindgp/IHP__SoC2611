// Testbench for the routed netlist of the chip, pad to pad (13 November 2026).
// The same test as ../cocotb/test_fw.py on ../vhdl/tb_soc2611_hb.vhd, but around the netlist that goes
// into the GDS: input clock on the clock pad, reset pad, boot strap on the button pads, one HyperRAM device with the
// firmware image on the HyperBus pads, a UART receiver on the TX pad, one byte sent to the RX pad when the firmware
// asks for it, the LED pads recorded. Optionally a camera drives one frame on the camera pads (CAM_* parameters).
// The UART bit time is that of the chip configuration: main_clock_c / 115200 = 1085 system clock cycles.
`timescale 1ns/1ps
module tb_chip_gl;
    parameter real    CLK_X2_NS     = 10.0;        // input clock period (the system clock is half this rate)
    parameter integer TICKS_PER_BIT = 1085;        // system clock cycles per UART bit in the chip
    parameter real    RWDS_DELAY    = 5.0;         // board delay of RWDS from the memory to the chip, about 1/4 CK
    // camera: frames of CAM_W x CAM_H pixels, two bytes per pixel, after CAM_START_MS
    parameter integer CAM_W         = 640;
    parameter integer CAM_H         = 4;
    parameter real    CAM_PCLK_NS   = 80.0;
    parameter real    CAM_START_MS  = 1.0;
    localparam real   BIT_NS        = TICKS_PER_BIT * 2.0 * CLK_X2_NS;
    // set at run time, so that one compiled simulator serves every test:
    //   +mem=<file>  firmware image for the HyperRAM (read by the memory model), +expect=<n> checks that must pass,
    //   +timeout_ms=<ms>, +cam=<n> number of camera frames to send (0 = camera pads quiet)
    integer EXPECT_PASS = 6;
    integer CAM_FRAMES  = 0;
    real    TIMEOUT_MS  = 400.0;
    initial begin
        void'($value$plusargs("expect=%d", EXPECT_PASS));
        void'($value$plusargs("cam=%d", CAM_FRAMES));
        void'($value$plusargs("timeout_ms=%f", TIMEOUT_MS));
    end

    reg clk_x2 = 1'b0;
    always #(CLK_X2_NS / 2.0) clk_x2 = ~clk_x2;
    reg porst_n = 1'b1, uart_rx = 1'b1;
    reg [3:0] gpio_in = 4'h9;                      // bit 3 = boot strap: start the image in the external memory
    reg cam_pclk = 1'b0, cam_vs = 1'b0, cam_hs = 1'b0;
    reg [7:0] cam_d = 8'h00;

    wire w_clk = clk_x2, w_rst = porst_n, w_rx = uart_rx, w_zero = 1'b0;
    wire [3:0] w_gpio_in = gpio_in;
    wire w_pclk = cam_pclk, w_vs = cam_vs, w_hs = cam_hs;
    wire [7:0] w_cam_d = cam_d;
    wire uart_tx, hb_ck, hb_csn, hb_resetn;
    wire [3:0] gpio_out;
    wire cam_mclk, cam_reset, cam_pwdn, cam_scl, spi_sclk, spi_mosi, spi_csn, jtag_tdo;

    // The netlist comes from strip_netlist.py --split-pads: a bidirectional pad pin NAME is three ports, NAME_i
    // (from the board), NAME_o and NAME_oe (what the chip drives, and when). The board wires are resolved here:
    // the chip when it drives, else the memory when it drives, else the pull-down of the board.
    wire [7:0] c_dq_o, c_dq_oe;
    wire c_rwds_o, c_rwds_oe, c_sda_o, c_sda_oe;
    wire [7:0] m_dq_o;
    wire m_dq_oe, m_rwds_o, m_rwds_oe, m_err;
    wire #(RWDS_DELAY) m_rwds_o_d = m_rwds_o;          // RWDS from the memory reaches the chip after the board delay
    wire #(RWDS_DELAY) m_rwds_oe_d = m_rwds_oe;
    wire [7:0] dq_to_chip = m_dq_oe ? m_dq_o : 8'h00;
    wire rwds_to_chip = m_rwds_oe_d ? m_rwds_o_d : 1'b0;
    wire [7:0] pin_dq = (c_dq_oe & c_dq_o) | (~c_dq_oe & dq_to_chip);
    wire pin_rwds = c_rwds_oe ? c_rwds_o : (m_rwds_oe ? m_rwds_o : 1'b0);
    hyperram_model u_ram (
        .ck(hb_ck), .csn(hb_csn), .resetn(hb_resetn), .rwds_i(pin_rwds), .rwds_o(m_rwds_o), .rwds_oe(m_rwds_oe),
        .dq_i(pin_dq), .dq_o(m_dq_o), .dq_oe(m_dq_oe), .error_out(m_err));
    // both sides driving a board wire at the same time is an error of the bus protocol
    integer n_contention = 0;
    always @(c_dq_oe or m_dq_oe or c_rwds_oe or m_rwds_oe)
        if (porst_n && (((|c_dq_oe) && m_dq_oe) || (c_rwds_oe && m_rwds_oe))) n_contention = n_contention + 1;

    SoC2611 dut (
        .clk_x2_PAD(w_clk), .porst_n_PAD(w_rst),
        .hb_ck_PAD(hb_ck), .hb_csn0_PAD(hb_csn), .hb_resetn_PAD(hb_resetn),
        .hb_rwds_PAD_i(rwds_to_chip), .hb_rwds_PAD_o(c_rwds_o), .hb_rwds_PAD_oe(c_rwds_oe),
        .hb_dq0_PAD_i(dq_to_chip[0]), .hb_dq0_PAD_o(c_dq_o[0]), .hb_dq0_PAD_oe(c_dq_oe[0]),
        .hb_dq1_PAD_i(dq_to_chip[1]), .hb_dq1_PAD_o(c_dq_o[1]), .hb_dq1_PAD_oe(c_dq_oe[1]),
        .hb_dq2_PAD_i(dq_to_chip[2]), .hb_dq2_PAD_o(c_dq_o[2]), .hb_dq2_PAD_oe(c_dq_oe[2]),
        .hb_dq3_PAD_i(dq_to_chip[3]), .hb_dq3_PAD_o(c_dq_o[3]), .hb_dq3_PAD_oe(c_dq_oe[3]),
        .hb_dq4_PAD_i(dq_to_chip[4]), .hb_dq4_PAD_o(c_dq_o[4]), .hb_dq4_PAD_oe(c_dq_oe[4]),
        .hb_dq5_PAD_i(dq_to_chip[5]), .hb_dq5_PAD_o(c_dq_o[5]), .hb_dq5_PAD_oe(c_dq_oe[5]),
        .hb_dq6_PAD_i(dq_to_chip[6]), .hb_dq6_PAD_o(c_dq_o[6]), .hb_dq6_PAD_oe(c_dq_oe[6]),
        .hb_dq7_PAD_i(dq_to_chip[7]), .hb_dq7_PAD_o(c_dq_o[7]), .hb_dq7_PAD_oe(c_dq_oe[7]),
        .cam_pclk_PAD(w_pclk), .cam_vs_PAD(w_vs), .cam_hs_PAD(w_hs),
        .cam_d0_PAD(w_cam_d[0]), .cam_d1_PAD(w_cam_d[1]), .cam_d2_PAD(w_cam_d[2]), .cam_d3_PAD(w_cam_d[3]),
        .cam_d4_PAD(w_cam_d[4]), .cam_d5_PAD(w_cam_d[5]), .cam_d6_PAD(w_cam_d[6]), .cam_d7_PAD(w_cam_d[7]),
        .cam_mclk_PAD(cam_mclk), .cam_reset_PAD(cam_reset), .cam_pwdn_PAD(cam_pwdn), .cam_scl_PAD(cam_scl),
        .cam_sda_PAD_i(1'b1), .cam_sda_PAD_o(c_sda_o), .cam_sda_PAD_oe(c_sda_oe),     // pull-up on the board
        .uart_tx_PAD(uart_tx), .uart_rx_PAD(w_rx),
        .spi_sclk_PAD(spi_sclk), .spi_mosi_PAD(spi_mosi), .spi_miso_PAD(w_zero), .spi_csn_PAD(spi_csn),
        .gpio_out0_PAD(gpio_out[0]), .gpio_out1_PAD(gpio_out[1]), .gpio_out2_PAD(gpio_out[2]), .gpio_out3_PAD(gpio_out[3]),
        .gpio_in0_PAD(w_gpio_in[0]), .gpio_in1_PAD(w_gpio_in[1]), .gpio_in2_PAD(w_gpio_in[2]), .gpio_in3_PAD(w_gpio_in[3]),
        .jtag_tck_PAD(w_zero), .jtag_tms_PAD(w_zero), .jtag_tdi_PAD(w_zero), .jtag_tdo_PAD(jtag_tdo));

    // activity on the pads that no test reads back, as plain counts for the report
    integer n_scl = 0, n_mclk = 0;
    always @(posedge cam_scl) n_scl = n_scl + 1;
    always @(posedge cam_mclk) n_mclk = n_mclk + 1;

    function automatic bit has(input string s, input string sub);
        int i;
        for (i = 0; i + sub.len() <= s.len(); i++)
            if (s.substr(i, i + sub.len() - 1) == sub) return 1;
        return 0;
    endfunction

    // ---------------------------------------------------------------- UART receiver on the TX pad
    string line = "";
    string led_seq = "";
    integer n_lines = 0, n_pass = 0, n_fail = 0, n_chars = 0, bi;
    reg [7:0] ch;
    reg rx_busy = 1'b0, send_k = 1'b0, summary_seen = 1'b0, summary_ok = 1'b0, banner_seen = 1'b0;
    realtime t_fall = 0, min_low = 1.0e15, t_first_char = 0, t_summary = 0;

    always @(negedge uart_tx) t_fall = $realtime;
    always @(posedge uart_tx) if (porst_n && t_fall > 0 && ($realtime - t_fall) < min_low) min_low = $realtime - t_fall;

    always @(negedge uart_tx) if (porst_n && !rx_busy) begin
        rx_busy = 1'b1;
        if (t_first_char == 0) t_first_char = $realtime;
        #(BIT_NS * 1.5);
        for (bi = 0; bi < 8; bi = bi + 1) begin
            ch[bi] = uart_tx;
            #(BIT_NS);
        end
        rx_busy = 1'b0;
        n_chars = n_chars + 1;
        if (ch == 8'h0A) begin
            if (line.len() > 0) begin
                n_lines = n_lines + 1;
                $display("UART %8.3f ms| %s", $realtime / 1.0e6, line);
                if (has(line, "FW smoke") || has(line, "FW ")) banner_seen = 1'b1;
                if (line.len() > 4 && line.substr(0, 0) == "T" && has(line, " PASS")) n_pass = n_pass + 1;
                if (line.len() > 4 && line.substr(0, 0) == "T" && has(line, " FAIL")) n_fail = n_fail + 1;
                if (has(line, "uart_rx WAIT") || line == "W") send_k = 1'b1;
                if (has(line, "SUMMARY")) begin
                    summary_seen = 1'b1;
                    t_summary = $realtime;
                    summary_ok = has(line, $sformatf("pass=%0d fail=0", EXPECT_PASS));
                end else if (line.len() == 4 && line.substr(0, 0) == "P" && line.substr(2, 2) == "F") begin
                    // short summary of the quick firmware: P<passed>F<failed>
                    summary_seen = 1'b1;
                    t_summary = $realtime;
                    summary_ok = (line == $sformatf("P%0dF0", EXPECT_PASS));
                end
            end
            line = "";
        end else if (ch != 8'h0D) line = $sformatf("%s%c", line, ch);
    end

    // ---------------------------------------------------------------- one byte to the RX pad when asked
    task uart_send(input [7:0] b);
        integer i;
        begin
            uart_rx = 1'b0; #(BIT_NS);
            for (i = 0; i < 8; i = i + 1) begin uart_rx = b[i]; #(BIT_NS); end
            uart_rx = 1'b1; #(BIT_NS);
        end
    endtask
    always @(posedge send_k) begin
        #(2.0 * BIT_NS);
        uart_send(8'h4B);                           // 'K'
    end

    // ---------------------------------------------------------------- LED pads
    always @(gpio_out) if (porst_n) led_seq = $sformatf("%s %0x", led_seq, gpio_out);

    // ---------------------------------------------------------------- camera: frames on the camera pads
    // VSYNC high between frames, HREF high during a line, data changes on the falling edge of PCLK, the chip
    // samples on the rising edge. Pixel bytes are a counter pattern, the same in every frame, so the bytes the
    // chip writes to the memory are known whichever frame it starts with (it starts at the first VSYNC after
    // its own set-up of the camera over I2C has finished and the firmware has enabled the stream).
    integer cf, cy, cx, cam_bytes = 0;
    task cam_clk(input integer n);
        integer j;
        begin
            for (j = 0; j < n; j = j + 1) begin
                #(CAM_PCLK_NS / 2.0) cam_pclk = 1'b1;
                #(CAM_PCLK_NS / 2.0) cam_pclk = 1'b0;
            end
        end
    endtask
    initial begin
        #1.0;                                       // after the run-time settings have been read
        if (CAM_FRAMES > 0) begin
            #(CAM_START_MS * 1.0e6);
            for (cf = 0; cf < CAM_FRAMES; cf = cf + 1) begin
                cam_vs = 1'b1; cam_clk(8); cam_vs = 1'b0; cam_clk(8);
                for (cy = 0; cy < CAM_H; cy = cy + 1) begin
                    cam_hs = 1'b1;
                    for (cx = 0; cx < 2 * CAM_W; cx = cx + 1) begin
                        cam_d = 8'((cy * 7 + cx * 3 + 1) & 255);     // the same in every frame (cam_expect.py)
                        cam_bytes = cam_bytes + 1;
                        cam_clk(1);
                    end
                    cam_hs = 1'b0; cam_d = 8'h00; cam_clk(8);
                end
                cam_clk(8);
            end
            cam_vs = 1'b1; cam_clk(8); cam_vs = 1'b0;
            forever cam_clk(1);
        end
    end

    // ---------------------------------------------------------------- run
    task report(input string why);
        begin
            $display("GLSIM end: %s at %0.3f ms of simulated time", why, $realtime / 1.0e6);
            $display("GLSIM uart: %0d characters, %0d lines, first character at %0.3f ms", n_chars, n_lines, t_first_char / 1.0e6);
            $display("GLSIM uart bit time: shortest low pulse %0.1f ns = %0.1f input clock cycles = %0.1f system clock cycles",
                     min_low, min_low / CLK_X2_NS, min_low / (2.0 * CLK_X2_NS));
            $display("GLSIM tests: %0d PASS lines, %0d FAIL lines, summary seen %0d, summary as expected %0d",
                     n_pass, n_fail, summary_seen, summary_ok);
            $display("GLSIM leds:%s", led_seq);
            $display("GLSIM hyperram: %0d transactions (%0d register, %0d read, %0d write), %0d bytes read, %0d bytes written, error flag %0d",
                     u_ram.n_txn, u_ram.n_reg, u_ram.n_rd, u_ram.n_wr, u_ram.n_bytes_rd, u_ram.n_bytes_wr, m_err);
            $display("GLSIM pads: %0d times two drivers on a HyperBus wire; camera I2C clock rose %0d times, camera master clock %0d times",
                     n_contention, n_scl, n_mclk);
            if (CAM_FRAMES > 0) $display("GLSIM camera: %0d bytes driven on the camera pads", cam_bytes);
            if (summary_seen && summary_ok && n_fail == 0 && m_err == 1'b0 && n_contention == 0)
                $display("GLSIM VERDICT: PASS");
            else
                $display("GLSIM VERDICT: FAIL");
        end
    endtask

    // The reset pad goes low 200 ns after the start and stays low for 1 us. The falling edge matters in a
    // simulation: a flip-flop model clears on the falling EDGE of its reset pin, while the real cell clears as long
    // as the pin is LOW. With the pad low from time 0 a flip-flop whose clock does not run during the reset (the
    // JTAG, camera and memory-strobe clock domains) would keep its start value, which the chip cannot do.
    initial begin
        #200.0 porst_n = 1'b0;
        #1000.0 porst_n = 1'b1;
        $display("GLSIM reset released at 1.2 us; input clock %0.1f ns; UART bit %0.0f ns", CLK_X2_NS, BIT_NS);
    end
    always @(posedge summary_seen) begin
        #(2.0 * BIT_NS);                            // let the last LED write happen
        report("summary line received");
        $finish;
    end
    initial begin
        #1.0;
        #(TIMEOUT_MS * 1.0e6);
        report("TIMEOUT");
        $finish;
    end
    // +tick_us=<n>: a line every n microseconds. The simulation with delays advances a few hundred microseconds
    // per hour, so the 5 ms line below never comes; with this line its pace and the first activity can be seen.
    real TICK_US = 0.0;
    initial begin
        void'($value$plusargs("tick_us=%f", TICK_US));
        if (TICK_US > 0.0) forever begin
            #(TICK_US * 1.0e3);
            $display("GLSIM tick %0.3f ms: %0d characters, hyperram transactions %0d, leds:%s",
                     $realtime / 1.0e6, n_chars, u_ram.n_txn, led_seq);
        end
    end
    // a line every 5 ms, so that a silent run can be told from a hung one
    always begin
        #5.0e6;
        $display("GLSIM %0.0f ms: %0d characters so far, hyperram transactions %0d, leds:%s",
                 $realtime / 1.0e6, n_chars, u_ram.n_txn, led_seq);
    end
endmodule
