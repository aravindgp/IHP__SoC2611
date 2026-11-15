// Pad models without tri-state, for the netlist written by strip_netlist.py --split-pads (13 November 2026).
// Function as in sg13cmos5l_io.v of the PDK: an input pad passes the pad to the core, an output pad the core to
// the pad, a bidirectional pad drives the pad while c2p_en is high. The pad wire of a bidirectional pad is split:
// pad_i is what the board drives, pad_o and pad_oe what the chip drives and when; the core sees its own value
// while it drives, as on a real pad.
`timescale 1ns/1ps
module sg13cmos5l_IOPadIn (pad, p2c);
    input pad; output p2c;
    assign p2c = pad;
endmodule
module sg13cmos5l_IOPadOut4mA (pad, c2p);
    output pad; input c2p;
    assign pad = c2p;
endmodule
module sg13cmos5l_IOPadOut16mA (pad, c2p);
    output pad; input c2p;
    assign pad = c2p;
endmodule
module sg13cmos5l_IOPadOut30mA (pad, c2p);
    output pad; input c2p;
    assign pad = c2p;
endmodule
module sg13cmos5l_IOPadInOut4mA (pad_i, pad_o, pad_oe, c2p, p2c, c2p_en);
    input pad_i; output pad_o, pad_oe; input c2p, c2p_en; output p2c;
    assign pad_o = c2p;
    assign pad_oe = c2p_en;
    assign p2c = c2p_en ? c2p : pad_i;
endmodule
module sg13cmos5l_IOPadInOut16mA (pad_i, pad_o, pad_oe, c2p, p2c, c2p_en);
    input pad_i; output pad_o, pad_oe; input c2p, c2p_en; output p2c;
    assign pad_o = c2p;
    assign pad_oe = c2p_en;
    assign p2c = c2p_en ? c2p : pad_i;
endmodule
module sg13cmos5l_IOPadInOut30mA (pad_i, pad_o, pad_oe, c2p, p2c, c2p_en);
    input pad_i; output pad_o, pad_oe; input c2p, c2p_en; output p2c;
    assign pad_o = c2p;
    assign pad_oe = c2p_en;
    assign p2c = c2p_en ? c2p : pad_i;
endmodule
