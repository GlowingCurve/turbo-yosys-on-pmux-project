// The alphabet consists of the uppercase letters and the space.
// Author: Fabio Somenzi <Fabio@Colorado.EDU>
// Modified by: Rajdeep Mukherjee <rajdeep.mukherjee@cs.ox.ac.uk>

// The output plain is 0 except for one clock cycle when a character has
// been decoded.
module huffmanDec (clk,cipher,plain);
    input        clk;
    input 	 cipher;
    output [7:0] plain;
    reg [9:0] 	 state;

    wire 	 leaf;
    wire [7:0] 	 character;

    initial state = 0;

    // This function maps states to characters.  All non-leaf states are
    // mapped to NUL.  The leaf states are mapped to the ASCII code of the
    // corresponding symbol.
    assign plain = (state == 9)?69: (state==13)?32: (state==17)?83: (state==22)?65:
    (state==23)?73: (state==24)?79: (state==25)?82: (state==26)?78: (state==30)?84:
    (state==31)?85: (state==32)?80: (state==33)?70: (state==34)?67: (state==38)?76:
    (state==43)?72: (state==59)?68: (state==76)?87: (state==89)?71: (state==90)?89:
    (state==122)?77: (state==243)?66: (state==244)?86: (state==303)?81: (state==305)?75:
    (state==306)?88: (state==609)?90: (state==610)?74:0;

    assign leaf = plain != 0;

    always @ (posedge clk) begin
	state = (leaf ? 0 : {state[8:0],1'b0}) + (cipher ? 2 : 1);
    end
endmodule // huffmanDec
