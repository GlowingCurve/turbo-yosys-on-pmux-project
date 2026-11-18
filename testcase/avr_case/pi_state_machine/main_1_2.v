`define IDLE 3'b000
`define WAT 3'b001
`define RDM 3'b010
`define ERR 3'b011
`define RDY 3'b100
`define RTR 3'b101
`define RESET 2'b00
`define ADDRESS 2'b01
`define DATA_WAIT 2'b10

module pi_state_machine( clk, Din, A, ACK, OPC, READ, filled, data_ready, error, TOUT, Dout, SEL_0, state, dataout);
   input [31:0] Din;
   input [29:0] A;
   input [3:0] OPC;
   input READ;
   input SEL_0;
   input TOUT;
   input clk;
   input filled;
   input data_ready;
   input error;
   output [31:0] Dout;
   output ACK;
   wire ACK;
   output [1:0] state;
   output [31:0] dataout;
   reg [29:0] address;
   reg [3:0] opc;
   reg read_or_write;
   reg [31:0] dataout;
   reg [31:0] datain;
   reg [31:0] data;
   reg acknowledge;
   reg [1:0] state;

   initial state = `RESET;
   initial acknowledge = `IDLE;
   initial address = 30'b000000000000000000000000000000;
   initial opc = 4'b0000;
   initial read_or_write = 0;
   initial data = {32{1'b1}};
   initial datain = 0;
   initial dataout = 0;
   assign Dout = dataout;
   assign ACK = acknowledge;

   always @(posedge clk) begin
      case (state)
        `RESET: begin
           dataout = 0;
           acknowledge = `IDLE;
           if (SEL_0 == 1) begin
              address = A;
              opc = OPC;
              read_or_write = READ;
              state = `ADDRESS;
           end else begin
              state = `ADDRESS;
              dataout = 0;
           end
        end
        `ADDRESS: begin
           if (error == 1) begin
              dataout = {32{1'b0}};
              acknowledge = `ERR;
              state = `ADDRESS;
           end else begin
              if (SEL_0 == 0) begin
                 dataout = {32{1'b0}};
                 acknowledge = `IDLE;
                 if (SEL_0 == 1) begin
                    address = A;
                    opc = OPC;
                    read_or_write = READ;
                    state = `ADDRESS;
                 end else begin
                    state = `ADDRESS;
                 end
              end else begin
                 if ((READ && data_ready)||((!READ)&&(!filled))) begin
                    if (READ) begin
                       dataout = data;
                       acknowledge = `RDY;
                       if (SEL_0 == 1) begin
                          address = A;
                          opc = OPC;
                          read_or_write = READ;
                          state = `ADDRESS;
                       end else begin
                          state = `ADDRESS;
                       end
                    end else begin
                       datain = Din;
                       acknowledge = `RDY;
                       if (SEL_0 == 1) begin
                          address = A;
                          opc = OPC;
                          read_or_write = READ;
                          state = `ADDRESS;
                          dataout = {32{1'b0}};
                       end else begin
                          state = `ADDRESS;
                       end
                    end
                 end
                 if ((READ && (!data_ready))||((!READ) && filled)) begin
                    acknowledge = `WAT;
                    state = `DATA_WAIT;
                 end
              end
           end
        end
        `DATA_WAIT: begin
           if ((TOUT == 1)||(error == 1)) begin
              dataout = {32{1'b0}};
              if (error == 1) begin
                 acknowledge = `ERR;
                 state = `ADDRESS;
              end else begin
                 acknowledge = `IDLE;
                 state = `ADDRESS;
              end
           end
           if ((READ && data_ready)||((!READ)&&(!filled))) begin
              if (READ) begin
                 dataout = data;
                 acknowledge = `RDY;
                 if (SEL_0 == 1) begin
                    address = A;
                    opc = OPC;
                    read_or_write = READ;
                    state = `ADDRESS;
                 end else begin
                    state = `ADDRESS;
                 end
              end else begin
                 datain = Din;
                 acknowledge = `RDY;
                 if (SEL_0 == 1) begin
                    address = A;
                    opc = OPC;
                    read_or_write = READ;
                    state = `ADDRESS;
                 end else begin
                    state = `ADDRESS;
                 end
              end
           end
           if ((READ && (!data_ready))||((!READ) && filled)) begin
              acknowledge = `WAT;
              state = `DATA_WAIT;
           end
        end
      endcase
   end
endmodule // pi_state_machine
