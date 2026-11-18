// A simple synchronous tree arbiter.
// Author: Fabio Somenzi <Fabio@Colorado.EDU>

// The arbiter cell is a Moore machine with two inputs from children and
// two outputs to chidren; one input from parent, and one output to parent.
// If both children of a cell issue a request in the same clock cycle,
// the cell chooses one of the children, giving priority to the one
// that did not receive the last grant.  Before any grant is
// given---for instance in the initial state---the child connected to
// req1 and ack1 is given priority in case of simultaneous requests.

module cell (clk, req1, req2, ack1, ack2, req0, ack0);
    input  clk;
    input  ack0, req1, req2;
    output req0, ack1, ack2;

    parameter I1 = 3'd0;
    parameter I2 = 3'd1;
    parameter R1 = 3'd2;
    parameter R2 = 3'd3;
    parameter A1 = 3'd4;
    parameter A2 = 3'd5;

    reg [2:0] state;
    initial state = I1;

    always @ (posedge clk) begin
	case (state)
	  I1: if (req1)  state = R1; else if (req2) state = R2;
	  R1: if (ack0)  state = A1;
	  A1: if (!req1) state = I2;
	  I2: if (req2)  state = R2; else if (req1) state = R1;
	  R2: if (ack0)  state = A2;
	  A2: if (!req2) state = I1;
	endcase
    end

    assign req0 = state == R1 || state == R2 || state == A1 || state == A2;
    assign ack1 = state == A1;
    assign ack2 = state == A2;
endmodule // cell
