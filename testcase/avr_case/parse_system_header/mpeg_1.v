/*
 * This module parses the 8 bytes of the system header after the
 * system_header_start_code.
 * syshead_len_reg (2 bytes): number of bytes in header after start code.
 * rate_bnd_reg: 22 bit bound on mux rate and 2 marker bits.
 * flag_reg: audio and video bounds and some flags.
 * resvd_byte_reg: 1 reserved byte (0xFF).
 */
module parse_system_header(one_byte,start,enable,stop,syshead_len_reg,rate_bnd_reg,flag_reg,resvd_byte_reg);
input [7:0] one_byte;
input start;
input enable;
output reg stop;
output reg [15:0] syshead_len_reg;
output reg [23:0] rate_bnd_reg;
output reg [15:0] flag_reg;
output reg [7:0] resvd_byte_reg;
reg [2:0] count;
reg flag;
reg [1:0] count1;
reg [23:0] Mem[0:7];
reg [7:0] stream_id_temp;
reg [15:0] stream_temp;
reg [23:0] stream_temp1;
integer i;

initial begin
   stop = 0;
   syshead_len_reg = 0;
   rate_bnd_reg = 0;
   flag_reg = 0;
   resvd_byte_reg = 0;
   count = 3'b000;
   count1 = 0;
   flag = 0;
   Mem[0] = 0;
   Mem[1] = 0;
   Mem[2] = 0;
   Mem[3] = 0;
   Mem[4] = 0;
   Mem[5] = 0;
   Mem[6] = 0;
   Mem[7] = 0;
   stream_temp = 0;
   stream_temp1 = 0;
   stream_id_temp = 0;
end

always @(posedge enable) begin
   if ((start == 1)&&(flag == 0)) begin
      case (count)
        3'b000: begin
           syshead_len_reg[7:0] = one_byte[7:0];
           count = count + 1;
        end
        3'b001: begin
           syshead_len_reg[15:8] = one_byte[7:0];
           count = count + 1;
        end
        3'b010: begin
           rate_bnd_reg[7:0] = one_byte[7:0];
           count = count + 1;
        end
        3'b011: begin
           rate_bnd_reg[15:8] = one_byte[7:0];
           count = count + 1;
        end
        3'b100: begin
           rate_bnd_reg[23:16] = one_byte[7:0];
           count = count + 1;
        end
        3'b101: begin
           flag_reg[7:0] = one_byte[7:0];
           count = count + 1;
        end
        3'b110: begin
           flag_reg[15:8] = one_byte[7:0];
           count = count + 1;
        end
        3'b111: begin
           resvd_byte_reg[7:0] = one_byte[7:0];
           flag = 1;
           count = 3'b000;
        end
      endcase
   end
   if ((start == 1)&&(flag == 1)) begin
      if (one_byte[0:0] == 1) begin
         case (count1)
           2'b00: begin
              stream_id_temp[7:0] = one_byte[7:0];
              count1 = count1 + 1;
           end
           2'b01: begin
              stream_temp[7:0] = one_byte[7:0];
              count1 = count1 + 1;
           end
           2'b10: begin
              stream_temp[15:8] = one_byte[7:0];
              count1 = 0;
              stream_temp1[7:0] = stream_temp;
              case (stream_id_temp)
                8'b00000011: begin
                   Mem[0] = stream_temp1;
                   stop = 1;
                end
                8'b10000011: begin
                   Mem[1] = stream_temp1;
                   stop = 1;
                end
                8'b01000011: begin
                   Mem[2] = stream_temp1;
                   stop = 1;
                end
                8'b11000011: begin
                   Mem[3] = stream_temp1;
                   stop = 1;
                end
                8'b00000111: begin
                   Mem[4] = stream_temp1;
                   stop = 1;
                end
                8'b10000011: begin
                   Mem[5] = stream_temp1;
                   stop = 1;
                end
                8'b01000011: begin
                   Mem[6] = stream_temp1;
                   stop = 1;
                end
                8'b11000011: begin
                   Mem[7] = stream_temp1;
                   stop = 1;
                end
              endcase
           end
         endcase
      end
   end
   if (start == 0) stop = 0;
end
endmodule
