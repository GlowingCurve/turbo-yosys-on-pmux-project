// The alphabet consists of the uppercase letters and the space.
// Author: Fabio Somenzi <Fabio@Colorado.EDU>
// Modified by: Rajdeep Mukherjee <rajdeep.mukherjee@cs.ox.ac.uk>

module huffmanEnc (clk, addr, cipher, character);
    input        clk;
    input [4:0]  addr;
    output 	 cipher;
    output [7:0] character;

    reg [7:0] 	 character;
    reg [9:0] shiftreg;

    always @ (posedge clk) begin
	if (shiftreg[9:1] == 1) begin
	    character = addr < 26 ?
	      65 + {3'b0, addr} : 32;
	    shiftreg = (character == 69)? 10'b0000001010:
	      character == 32 ? 10'b0000001011: // space
	      character == 83 ? 10'b0000010100: // S
	      character == 65 ? 10'b0000011110:
	      character == 73 ? 10'b0000010001:
	      character == 79 ? 10'b0000011001:
	      character == 82 ? 10'b0000010101: // R
	      character == 78 ? 10'b0000011101:
        character == 84 ? 10'b0000011111:
	      character == 85 ? 10'b0000100000:
	      character == 80 ? 10'b0000110000:
	      character == 70 ? 10'b0000101000:
	      character == 67 ? 10'b0000111000: // C
	      character == 76 ? 10'b0000111100: // L
	      character == 72 ? 10'b0000100110: // H
	      character == 68 ? 10'b0000100111: // D
	      character == 87 ? 10'b0001101100: // W
	      character == 71 ? 10'b0001010110: // G
	      character == 89 ? 10'b0001110110: // Y
	      character == 77 ? 10'b0001110111: // M
	      character == 66 ? 10'b0010010111: // B
	      character == 86 ? 10'b0011010111: // V
	      character == 81 ? 10'b0100001100: // Q
	      character == 75 ? 10'b0101001100: // K
	      character == 88 ? 10'b0111001100: // X
	      character == 90 ? 10'b1010001100: // Z
	      character == 74 ? 10'b1110001100: // J
	      10'b0;
	end else begin
	    shiftreg = {1'b0, shiftreg[9:1]}; // shift right
	end
    end
    assign cipher = shiftreg[0];
endmodule // huffmanEnc
