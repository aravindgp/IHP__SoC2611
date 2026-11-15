// Behavioural HyperRAM model in Verilog (HyperBus 1.0, S27KL0641 class), for the simulation of the routed netlist.
// A port of HW/asic/tb/hyperram_model.vhd, edge for edge:
//  * CS# low with CK low starts a transaction. The 48-bit command/address is taken on the first six CK edges
//    (CA[47:40] on the first rising edge). While the CA runs the model drives RWDS high: fixed 2x latency.
//  * First data byte on CK edge 4 + 4*INITIAL_LATENCY, counted from the edge that took CA[47:40].
//  * Read: one byte per CK edge on DQ, RWDS high for the first byte of a 16-bit word, TCKD after the edge, until
//    CS# rises. Write: DQ taken on every CK edge when RWDS is low.
//  * Register space (CA[46] = 1): zero-latency write of CR0 at word address 0x1000, reads of ID0 and CR0.
//  * Checks, sticky on error_out: transaction while RESET# is low or before tVCS after RESET# high, RESET# pulse
//    under tRP = 200 ns, CS# low longer than tCSM = 4 us, wrapped burst, CK not low at CS# fall.
// Byte order: the first byte of a 16-bit word on the bus is the byte at the even address.
// The memory is loaded from MEM_FILE ($readmemh format, one byte per entry) at time 0.
`timescale 1ns/1ps
module hyperram_model #(
    parameter MEM_BYTES = 1048576,
    parameter INITIAL_LATENCY = 6,
    parameter MEM_FILE = "",
    parameter real TCKD = 2.0,           // CK edge to DQ/RWDS output, ns
    parameter real TVCS_NS = 150000.0,
    parameter TCSM_CHECK = 1
) (
    input  wire       ck,
    input  wire       csn,
    input  wire       resetn,
    input  wire       rwds_i,
    output wire       rwds_o,
    output wire       rwds_oe,
    input  wire [7:0] dq_i,
    output wire [7:0] dq_o,
    output wire       dq_oe,
    output reg        error_out
);
    reg [7:0] mem [0:MEM_BYTES-1];
    reg [7:0] dq_r = 8'h00;
    reg dq_oe_r = 1'b0, rwds_r = 1'b0, rwds_oe_r = 1'b0;
    assign #(TCKD) dq_o = dq_r;
    assign #(TCKD) dq_oe = dq_oe_r;
    assign #(TCKD) rwds_o = rwds_r;
    assign #(TCKD) rwds_oe = rwds_oe_r;

    integer ei = 0, first = 0, baddr = 0, k = 0;
    reg [47:0] ca = 48'h0;
    reg is_read = 1'b0, is_reg = 1'b0, active = 1'b0, reset_seen = 1'b0;
    reg [31:0] waddr = 32'h0;
    reg [15:0] word = 16'h0, cr0 = 16'h8F1F;
    realtime t_reset_hi = 0, t_reset_lo = 0, t_cs_fall = 0;
    // counters for the report of the testbench
    integer n_txn = 0, n_rd = 0, n_wr = 0, n_reg = 0, n_bytes_rd = 0, n_bytes_wr = 0;

    integer i;
    string mem_file;
    initial begin
        error_out = 1'b0;
        for (i = 0; i < MEM_BYTES; i = i + 1) mem[i] = 8'h00;
        // +mem=<file> at run time has priority over the parameter
        if (!$value$plusargs("mem=%s", mem_file)) mem_file = MEM_FILE;
        if (mem_file != "") begin
            $readmemh(mem_file, mem);
            $display("HYPERRAM image %0s loaded", mem_file);
        end
    end

    task err(input [8*64-1:0] msg);
        begin
            $display("HYPERRAM ERROR at %0t ps: %0s", $time, msg);
            error_out = 1'b1;
        end
    endtask

    always @(negedge resetn) t_reset_lo = $realtime;
    always @(posedge resetn) begin
        if (t_reset_lo > 0 && ($realtime - t_reset_lo) < 200.0) err("RESET# pulse shorter than tRP (200 ns)");
        t_reset_hi = $realtime;
        reset_seen = 1'b1;
    end

    always @(negedge csn) begin
        t_cs_fall = $realtime;
        ei = 0; active = 1'b1; n_txn = n_txn + 1;
        if (resetn !== 1'b1) err("transaction while RESET# is low");
        else if (!reset_seen || ($realtime - t_reset_hi) < TVCS_NS) err("transaction before tVCS after RESET# high");
        if (ck !== 1'b0) err("CS# fell while CK was not low");
        rwds_oe_r <= 1'b1;
        rwds_r <= 1'b1;                    // fixed 2x latency
    end

    always @(posedge csn) begin
        if (TCSM_CHECK != 0 && active && ($realtime - t_cs_fall) > 4000.0) err("CS# low longer than tCSM (4 us)");
        active = 1'b0;
        dq_oe_r <= 1'b0;
        rwds_oe_r <= 1'b0;
        rwds_r <= 1'b0;
    end

    task ck_edge;
        begin
            if (ei < 6) begin
                ca[47 - 8*ei -: 8] = dq_i;
                if (ei == 5) begin
                    is_read = ca[47];
                    is_reg = ca[46];
                    if (!ca[45]) err("wrapped burst not supported by this model");
                    waddr = {ca[44:16], ca[2:0]};
                    if (is_read) rwds_r <= 1'b0;          // keep driving RWDS low through the latency
                    else rwds_oe_r <= 1'b0;               // release RWDS to the master
                    first = 4 + 4*INITIAL_LATENCY;
                    baddr = {waddr[30:0], 1'b0} % MEM_BYTES;
                    if (is_reg) n_reg = n_reg + 1;
                    else if (is_read) n_rd = n_rd + 1;
                    else n_wr = n_wr + 1;
                end
            end else if (is_reg && !is_read) begin
                if (ei == 6) word[15:8] = dq_i;
                else if (ei == 7) begin
                    word[7:0] = dq_i;
                    if (waddr == 32'h00001000) begin
                        cr0 = word;
                        $display("HYPERRAM CR0 <= 0x%04x at %0t ps", word, $time);
                    end
                end
            end else if (ei >= first) begin
                k = ei - first;
                if (is_read) begin
                    if (is_reg) begin
                        if (k % 2 == 0) word = (waddr == 32'h0) ? 16'h0C81 : (waddr == 32'h00001000) ? cr0 : 16'h0000;
                        dq_r <= (k % 2 == 0) ? word[15:8] : word[7:0];
                    end else begin
                        dq_r <= mem[(baddr + k) % MEM_BYTES];
                        n_bytes_rd = n_bytes_rd + 1;
                    end
                    dq_oe_r <= 1'b1;
                    rwds_r <= (k % 2 == 0);
                end else if (rwds_i === 1'b0) begin
                    mem[(baddr + k) % MEM_BYTES] = dq_i;
                    n_bytes_wr = n_bytes_wr + 1;
                end
            end
            ei = ei + 1;
        end
    endtask

    always @(posedge ck) if (csn === 1'b0 && active && (ei % 2) == 0) ck_edge;
    always @(negedge ck) if (csn === 1'b0 && active && (ei % 2) == 1) ck_edge;
endmodule
