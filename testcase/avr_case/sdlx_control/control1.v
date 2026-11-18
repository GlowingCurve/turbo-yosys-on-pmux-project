
// Parameter declaration

`define BYTE            1:0
`define DATAWIDTH       2
`define ADDRWIDTH       2
`define DATA            `DATAWIDTH-1:0
`define ADDR            `ADDRWIDTH-1:0
`define REGWIDTH        4
`define RDDR            `REGWIDTH-1:0
`define MAXREGS         1<<`REGWIDTH
`define IMEMSIZE         4
`define DMEMSIZE        4
`define DATAWIDTH1      32
`define DATA1           `DATAWIDTH1-1:0
`define CLOCKPERIOD     20

// Instruction fields

`define OPCODE          IR[31:26]

// I-Type Instruction
`define IRS             IR[23:21]
`define IRD             IR[18:16]
`define IMM             IR[1:0]

// R-Type Instruction
`define RRS1            IR[23:21]
`define RRS2            IR[18:16]
`define RRD             IR[13:11]
`define SHAMT           IR[7:6]
`define FUNC            IR[5:0]

// J-Type Instruction
`define OFFSET          IR[1:0]

// Address modes

`define DSPLTYPE        0
`define IMMTYPE         1

// OPcode map

// OPcodes
`define NOP     00000000000000000000000000000000

`define FSEL    6'b000000
`define J       6'b000010
`define BEQZ    6'b000100
`define BNEZ    6'b000101
`define ADDI    6'b001000
`define LW      6'b100011
`define SW      6'b101011
`define HLT     6'b001101

// func
`define AND     6'b100100
`define OR      6'b100101
`define SLL     6'b000000
`define SRL     6'b000010
`define ADD     6'b100000
`define SUB     6'b100010
`define MUL     6'b011000

// Execution steps

`define IDLE    0
`define IF      1
`define ID      2
`define EX      3
`define MEM     4
`define WB      5

// Miscellaneous

`define TRUE            1
`define FALSE           0

`define LEFT            1
`define RIGHT           0


`define ALUOPWIDTH      2
`define ALUO            `ALUOPWIDTH-1:0

`define MEMACC          2'b00
`define BRANCH          2'b01
`define RTYPE           2'b10
`define ITYPE           2'b11

// ALU actions

`define ALUCTRLWIDTH    3
`define ALUC            `ALUCTRLWIDTH-1:0

`define ALUAND          3'b000
`define ALUOR           3'b001
`define ALUADD          3'b010
`define ALUSUB          3'b011
`define ALUMUL          3'b100
`define ALUSHL          3'b101
`define ALUSHR          3'b110




module sdlx_control(
	      IR,
	       
	       IRRW,
	       PCRW,
	       NPCRW,
	       ARW,
	       BRW,
	       IRW,
	       ALUoutRW,
	       MDRW,
	       BCRW,
	       ZSel,
	       BraE,
	       JmpE,
	       RegDst,
	       ALUInA,
	       ALUInB,
	       SESel,
	       WBSel,
	       ALUOp,
	       RegRW,
	       MemRW,
	       Reset,
	       Clk );

   input   [`DATA1] IR;
  
     
   // Internal Registers
   output 	   IRRW;
   output 	   PCRW;
   output 	   NPCRW;
   output 	   ARW;
   output 	   BRW;
   output 	   IRW;
   output 	   ALUoutRW;
   output 	   MDRW;
   output 	   BCRW;
   
   // MUXs
   output 	   ZSel;
   output 	   BraE;
   output 	   JmpE;
   output 	   RegDst;
   output 	   ALUInA;
   output 	   ALUInB;
   output 	   WBSel;
   
   // Sign Extension
   output 	SESel;
   
   // ALU
   output [`ALUO] ALUOp;
   
   // Register File
   output 	  RegRW;
   
   // Data memory
   output 	  MemRW;
   
   input 	  Reset, Clk;
   
   wire [5:0] 	  OPcode;
   reg 		  IRRW, PCRW, NPCRW, ARW, BRW, IRW, ALUoutRW, MDRW, BCRW;
   reg 		  ZSel, BraE, JmpE, RegDst, ALUInA, ALUInB, SESel, WBSel, RegRW, MemRW;
   reg [`ALUO] 	  ALUOp;
   
   reg [5:0] 	  State, NextState;

   
   
   initial begin
      State     = `IDLE;
      NextState = `IDLE;
      ALUOp    = 2'b00;
      IRRW     = 0;
      PCRW     = 0;
      NPCRW    = 0;
      ARW      = 0;
      BRW      = 0;
      IRW      = 0;
      ALUoutRW = 0;
      MDRW     = 0;
      BCRW     = 0;
      ZSel     = 0;
      BraE     = 0;
      JmpE     = 0;
      RegDst   = 0;
      ALUInA   = 0;
      ALUInB   = 0;
      SESel    = 0;
      WBSel    = 0;
      RegRW    = 0;
      MemRW    = 0;
      
      
      
   
   end
   
   
   always @(posedge Clk) begin
      
     State = NextState;


      
      case (State)
	`IDLE: begin
	   ALUOp    = 2'b00;
	   IRRW     = 0;
	   PCRW     = 0;
	   NPCRW    = 0;
	   ARW      = 0;
	   BRW      = 0;
	   IRW      = 0;
	   ALUoutRW = 0;
	   MDRW     = 0;
	   BCRW     = 0;
	   ZSel     = 0;
	   BraE     = 0;
	   JmpE     = 0;
	   RegDst   = 0;
	   ALUInA   = 0;
	   ALUInB   = 0;
	   SESel    = 0;
	   WBSel    = 0;
	   RegRW    = 0;
	   MemRW    = 0;
	   NextState = Reset ? `IDLE : `IF;
	end // case: `IDLE
	
	`IF:   begin
	   // IR  <- IMEM[PC]
	   // NPC <- [PC] + 4
	   ALUOp    = 2'b00;
	   IRRW     = 1;
	   PCRW     = 0;
	   NPCRW    = 1;
	   ARW      = 0;
	   BRW      = 0;
	   IRW      = 0;
	   ALUoutRW = 0;
	   MDRW     = 0;
	   BCRW     = 0;
	   ZSel     = 0;
	   BraE     = 0;
	   JmpE     = 0;
	   RegDst   = 0;
	   ALUInA   = 0;
	   ALUInB   = 0;
	   SESel    = 0;
	   WBSel    = 0;
	   RegRW    = 0;
	   MemRW    = 0;
	   NextState = Reset ? `IDLE : `ID;
	end
	`ID:   begin
        
       
	   // A  <- Reg[IRS]
	   // B  <- Reg[IRD]
	   // I  <- signext ## IMM
	   // PC <- NPC
	   if (`OPCODE == `J)  // I <- signext ## IR[25:0]
	      begin
		 ALUOp    = 2'b00;
		 IRRW     = 0;
		 PCRW     = 1;
		 NPCRW    = 0;
		 ARW      = 1;
		 BRW      = 1;
		 IRW      = 1;
		 ALUoutRW = 0;
		 MDRW     = 0;
		 BCRW     = 0;
		 ZSel     = 0;
		 BraE     = 0;
		 JmpE     = 0;
		 RegDst   = 0;
		 ALUInA   = 0;
		 ALUInB   = 0;
		 SESel    = 1;
		 WBSel    = 0;
		 RegRW    = 0;
		 MemRW    = 0;
	      end
	   else                   // I <- signext ## IR[15:0]
	      
	      begin
		 ALUOp    = 2'b00;
		 IRRW     = 0;
		 PCRW     = 1;
		 NPCRW    = 0;
		 ARW      = 1;
		 BRW      = 1;
		 IRW      = 1;
		 ALUoutRW = 0;
		 MDRW     = 0;
		 BCRW     = 0;
		 ZSel     = 0;
		 BraE     = 0;
		 JmpE     = 0;
		 RegDst   = 0;
		 ALUInA   = 0;
		 ALUInB   = 0;
		 SESel    = 0;
		 WBSel    = 0;
		 RegRW    = 0;
		 MemRW    = 0;
	      end
	   NextState = Reset ? `IDLE : `EX;
	end
	`EX:   begin
	   
	   if (IR == `NOP) 
	      
	      begin
		 ALUOp    = 2'b00;
		 IRRW     = 0;
		 PCRW     = 0;
		 NPCRW    = 0;
		 ARW      = 0;
		 BRW      = 0;
		 IRW      = 0;
		 ALUoutRW = 0;
		 MDRW     = 0;
		 BCRW     = 0;
		 ZSel     = 0;
		 BraE     = 0;
		 JmpE     = 0;
		 RegDst   = 0;
		 ALUInA   = 0;
		 ALUInB   = 0;
		 SESel    = 0;
		 WBSel    = 0;
		 RegRW    = 0;
		 MemRW    = 0;  	
		 NextState = Reset ? `IDLE : `IF;
	      end
	   else begin
	      case (`OPCODE)
		`FSEL: begin
		   
		   // ALUout <- [A] op [B]
		   case (`FUNC)
		     `SLL: 
			begin
			   ALUOp    = 2'b10;
			   IRRW     = 0;
			   PCRW     = 0;
			   NPCRW    = 0;
			   ARW      = 0;
			   BRW      = 0;
			   IRW      = 0;
			   ALUoutRW = 1;
			   MDRW     = 0;
			   BCRW     = 0;
			   ZSel     = 0;
			   BraE     = 0;
			   JmpE     = 0;
			   RegDst   = 0;
			   ALUInA   = 1;
			   ALUInB   = 1;
			   SESel    = 0;
			   WBSel    = 0;
			   RegRW    = 0;
			   MemRW    = 0;
			end
		     `SRL: 
			begin
			   ALUOp    = 2'b10;
			   IRRW     = 0;
			   PCRW     = 0;
			   NPCRW    = 0;
			   ARW      = 0;
			   BRW      = 0;
			   IRW      = 0;
			   ALUoutRW = 1;
			   MDRW     = 0;
			   BCRW     = 0;
			   ZSel     = 0;
			   BraE     = 0;
			   JmpE     = 0;
			   RegDst   = 0;
			   ALUInA   = 1;
			   ALUInB   = 1;
			   SESel    = 0;
			   WBSel    = 0;
			   RegRW    = 0;
			   MemRW    = 0;
			end
		     default:
			begin
			   ALUOp    = 2'b10;
			   IRRW     = 0;
			   PCRW     = 0;
			   NPCRW    = 0;
			   ARW      = 0;
			   BRW      = 0;
			   IRW      = 0;
			   ALUoutRW = 1;
			   MDRW     = 0;
			   BCRW     = 0;
			   ZSel     = 0;
			   BraE     = 0;
			   JmpE     = 0;
			   RegDst   = 0;
			   ALUInA   = 1;
			   ALUInB   = 0;
			   SESel    = 0;
			   WBSel    = 0;
			   RegRW    = 0;
			   MemRW    = 0;
			end
		   endcase
		   NextState = Reset ? `IDLE : `WB;
		end
		`J: begin
	
	   
		   // ALUout <- [NPC] + [Imm]
		   ALUOp    = 2'b01;
		   IRRW     = 0;
		   PCRW     = 0;
		   NPCRW    = 0;
		   ARW      = 0;
		   BRW      = 0;
		   IRW      = 0;
		   ALUoutRW = 1;
		   MDRW     = 0;
		   BCRW     = 0;
		   ZSel     = 0;
		   BraE     = 0;
		   JmpE     = 0;
		   RegDst   = 0;
		   ALUInA   = 0;
		   ALUInB   = 1;
		   SESel    = 0;
		   WBSel    = 0;
		   RegRW    = 0;
		   MemRW    = 0;
		   NextState = Reset ? `IDLE : `WB;
		end
		`BEQZ: begin
		   
		   // ALUout <- ([A] == 0) ? [NPC] + [Imm] : [NPC]
		   ALUOp    = 2'b01;
		   IRRW     = 0;
		   PCRW     = 0;
		   NPCRW    = 0;
		   ARW      = 0;
		   BRW      = 0;
		   IRW      = 0;
		   ALUoutRW = 1;
		   MDRW     = 0;
		   BCRW     = 1;
		   ZSel     = 0;
		   BraE     = 0;
		   JmpE     = 0;
		   RegDst   = 0;
		   ALUInA   = 0;
		   ALUInB   = 1;
		   SESel    = 0;
		   WBSel    = 0;
		   RegRW    = 0;
		   MemRW    = 0;
		   NextState = Reset ? `IDLE : `WB;
		end
		`BNEZ: begin
		
   
		   // ALUout <- ([A] != 0) ? [NPC] + [Imm] : [NPC]
		   ALUOp    = 2'b01;
		   IRRW     = 0;
		   PCRW     = 0;
		   NPCRW    = 0;
		   ARW      = 0;
		   BRW      = 0;
		   IRW      = 0;
		   ALUoutRW = 1;
		   MDRW     = 0;
		   BCRW     = 1;
		   ZSel     = 1;
		   BraE     = 0;
		   JmpE     = 0;
		   RegDst   = 0;
		   ALUInA   = 0;
		   ALUInB   = 1;
		   SESel    = 0;
		   WBSel    = 0;
		   RegRW    = 0;
		   MemRW    = 0;
		   NextState = Reset ? `IDLE : `WB;
		end
		`ADDI: begin
		
   
		   // ALUout <- [RS] + [Imm]
		   ALUOp    = 2'b11;
		   IRRW     = 0;
		   PCRW     = 0;
		   NPCRW    = 0;
		   ARW      = 0;
		   BRW      = 0;
		   IRW      = 0;
		   ALUoutRW = 1;
		   MDRW     = 0;
		   BCRW     = 0;
		   ZSel     = 0;
		   BraE     = 0;
		   JmpE     = 0;
		   RegDst   = 0;
		   ALUInA   = 1;
		   ALUInB   = 1;
		   SESel    = 0;
		   WBSel    = 0;
		   RegRW    = 0;
		   MemRW    = 0;
		   NextState = Reset ? `IDLE : `WB;
		end
		`LW: begin
		
   
		   // ALUout <- [RS]+[Imm]
		   ALUOp    = 2'b00;
		   IRRW     = 0;
		   PCRW     = 0;
		   NPCRW    = 0;
		   ARW      = 0;
		   BRW      = 0;
		   IRW      = 0;
		   ALUoutRW = 1;
		   MDRW     = 0;
		   BCRW     = 0;
		   ZSel     = 0;
		   BraE     = 0;
		   JmpE     = 0;
		   RegDst   = 0;
		   ALUInA   = 1;
		   ALUInB   = 1;
		   SESel    = 0;
		   WBSel    = 0;
		   RegRW    = 0;
		   MemRW    = 0;
		   
		   NextState = Reset ? `IDLE : `MEM;
		end
		`SW: begin
		   
		   // ALUout <- [RS]+[Imm]
		   
		   ALUOp    = 2'b00;
		   IRRW     = 0;
		   PCRW     = 0;
		   NPCRW    = 0;
		   ARW      = 0;
		   BRW      = 0;
		   IRW      = 0;
		   ALUoutRW = 1;
		   MDRW     = 0;
		   BCRW     = 0;
		   ZSel     = 0;
		   BraE     = 0;
		   JmpE     = 0;
		   RegDst   = 0;
		   ALUInA   = 1;
		   ALUInB   = 1;
		   SESel    = 0;
		   WBSel    = 0;
		   RegRW    = 0;
		   MemRW    = 0;
		   
		   NextState = Reset ? `IDLE : `MEM;
		end
		`HLT: begin
		   
		end
		default: begin
		   
		end
	      endcase
	   end
	end
	`MEM:  begin
	   
	   case (`OPCODE)
	     `LW: begin
		// MD <- DMEM[ALUout]
		ALUOp    = 2'b00;
		IRRW     = 0;
		PCRW     = 0;
		NPCRW    = 0;
		ARW      = 0;
		BRW      = 0;
		IRW      = 0;
 		ALUoutRW = 0;
		MDRW     = 1;
		BCRW     = 0;
		ZSel     = 0;
		BraE     = 0;
		JmpE     = 0;
		RegDst   = 0;
		ALUInA   = 0;
		ALUInB   = 0;
		SESel    = 0;
		WBSel    = 0;
		RegRW    = 0;
		MemRW    = 0;
		NextState = Reset ? `IDLE : `WB;
	     end // case: `LW
	     
	     `SW: begin
		ALUOp    = 2'b00;
		IRRW     = 0;
		PCRW     = 0;
		NPCRW    = 0;
		ARW      = 0;
		BRW      = 0;
		IRW      = 0;
		ALUoutRW = 0;
		MDRW     = 0;
		BCRW     = 0;
		ZSel     = 0;
		BraE     = 0;
		JmpE     = 0;
		RegDst   = 0;
		ALUInA   = 0;
		ALUInB   = 0;
   		SESel    = 0;
		WBSel    = 0;
		RegRW    = 0;
   		MemRW    = 1;
                          // DMEM[ALUout] <- [RD]
		NextState = Reset ? `IDLE : `IF;
	     end
	   endcase
	end
	`WB:   begin
	   case (`OPCODE)
	     `FSEL: begin
		
		// RD <- [ALUout]
		ALUOp    = 2'b00;
		IRRW     = 0;
   		PCRW     = 0;
   		NPCRW    = 0;
   		ARW      = 0;
   		BRW      = 0;
   		IRW      = 0;
   		ALUoutRW = 0;
   		MDRW     = 0;
   		BCRW     = 0;
   		ZSel     = 0;
   		BraE     = 0;
   		JmpE     = 0;
   		RegDst   = 1;
   		ALUInA   = 0;
   		ALUInB   = 0;
   		SESel    = 0;
   		WBSel    = 1;
   		RegRW    = 1;
   		MemRW    = 0;
		
	     end
	     `J: begin
		
		// Jump completion: could be in MEM too
		// PC <- [ALUout]
		ALUOp    = 2'b00;
		IRRW     = 0;
   		PCRW     = 1;
   		NPCRW    = 0;
   		ARW      = 0;
   		BRW      = 0;
   		IRW      = 0;
   		ALUoutRW = 0;
   		MDRW     = 0;
   		BCRW     = 0;
   		ZSel     = 0;
   		BraE     = 0;
   		JmpE     = 1;
   		RegDst   = 0;
   		ALUInA   = 0;
   		ALUInB   = 0;
   		SESel    = 0;
   		WBSel    = 0;
   		RegRW    = 0;
		MemRW    = 0;
	     end
	     `BEQZ: begin
		
		// Branch completion: could be in MEM too
		// PC <- [ALUout]
		ALUOp    = 2'b00;
		IRRW     = 0;
		PCRW     = 1;
		NPCRW    = 0;
		ARW      = 0;
   		BRW      = 0;
   		IRW      = 0;
   		ALUoutRW = 0;
   		MDRW     = 0;
   		BCRW     = 0;
   		ZSel     = 0;
   		BraE     = 1;
   		JmpE     = 0;
   		RegDst   = 0;
   		ALUInA   = 0;
   		ALUInB   = 0;
   		SESel    = 0;
   		WBSel    = 0;
   		RegRW    = 0;
   		MemRW    = 0;
	     end
	     `BNEZ: begin
		
		// Branch completion: could be in MEM too
		// PC <- [ALUout]
		ALUOp    = 2'b00;
		IRRW     = 0;
		PCRW     = 1;
		NPCRW    = 0;
		ARW      = 0;
		BRW      = 0;
		IRW      = 0;
   		ALUoutRW = 0;
   		MDRW     = 0;
   		BCRW     = 0;
   		ZSel     = 0;
   		BraE     = 1;
   		JmpE     = 0;
   		RegDst   = 0;
   		ALUInA   = 0;
   		ALUInB   = 0;
   		SESel    = 0;
   		WBSel    = 0;
   		RegRW    = 0;
   		MemRW    = 0;
	     end
	     `ADDI: begin
		
		// RD <- [ALUout]
		ALUOp    = 2'b00;
		IRRW     = 0;
   		PCRW     = 0;
   		NPCRW    = 0;
   		ARW      = 0;
   		BRW      = 0;
   		IRW      = 0;
   		ALUoutRW = 0;
   		MDRW     = 0;
   		BCRW     = 0;
   		ZSel     = 0;
   		BraE     = 0;
   		JmpE     = 0;
   		RegDst   = 0;
   		ALUInA   = 0;
   		ALUInB   = 0;
   		SESel    = 0;
   		WBSel    = 1;
   		RegRW    = 1;
   		MemRW    = 0;
	     end
	     `LW: begin
		
		// RD <- [MD]
		ALUOp    = 2'b00;
		IRRW     = 0;
		PCRW     = 0;
   		NPCRW    = 0;
   		ARW      = 0;
   		BRW      = 0;
   		IRW      = 0;
   		ALUoutRW = 0;
   		MDRW     = 0;
   		BCRW     = 0;
   		ZSel     = 0;
   		BraE     = 0;
   		JmpE     = 0;
   		RegDst   = 0;
   		ALUInA   = 0;
   		ALUInB   = 0;
   		SESel    = 0;
   		WBSel    = 0;
   		RegRW    = 1;
   		MemRW    = 0;
	     end
	   endcase
	   NextState = Reset ? `IDLE : `IF;
	end
	default: begin
	   
	end
      endcase
   end
   

endmodule /* Control */
