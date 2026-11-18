/*
*
*	Taken from VIS Benchmarks <ftp://vlsi.colorado.edu/pub/vis/vis-verilog-models-1.3.tar.gz>
*	Modified for YOSYS BTOR Backend <http://www.clifford.at/yosys/>
*	Modified by Ahmed Irfan <irfan@fbk.eu>
*
*/
//----------------------------------------------------------------------
// module fru: Forwarding Register Unit
//
// Retrieves register values as required for IDU, keeps track of data 
// values and there associated register addresses in flight to REG_file 
// and forwards to EXU A.R. to avoid idle pipe. Good data to EXU Opd's 
// typically 2 tics after commited to EXU/MAU-to-FRU data inputs (if 
// forwarding allowed). 
//
// In the event of data dependency, a stall of EXU stage by PCU is requested
// via Wait_for _data (= FRU_DataDependency).  The Steps & Works from PCU
// are expected to be combinational ckt based => several tics into Clk cycle
// FRU will recognize data dependency in progress & issue a DataDependency to
// PCU.  Several tics after this PCU expected to de-assert Step & Work to EXU
// to prepare to insert bubble in EXU on pending posedge Clk.  FRU will 
// keep DataDependency asserted up to this posedge & PCU is expected to latch
// it.  After posedge FRU de-asserts DataDependency and PCU is expected to 
// retain history of DataDependency, monitor MAU progress, and stall A.R.
// until MAU has data - even if FRU_DataDependency long since de-asserted.
// 
// Opd1 and Opd2 values, when sourced from REG_file, are valid midway 
// thru first 1/2 of Clk cycle and, internal to FRU, write of WB values
// occur on last 1/2 of CP cycle. This avoids possible stall in the 
// event of Read/Write contention.  
//
// If Reset duration > 32 Clk's all of REG_file is ZERO'd.  Reset's <
// 32 Clk's => partial zeroing occurs, starting from Reg0.
//
// IDU/FRU Interface: Per intermodule agreement, logic is asserted positive.
//     If ever get discreted decode of MAU_data_source,  1=> data from MAU
//                                                       0=> data from EXU.
//     Currently, MSB of RegA/B/Dest is the valid bit,   1=>valid address.
//
//
// PCU/FRU Interface: Per intermodule agreement, logic is asserted positive. 
//     All Steps and Works are assumed asserted positive and are expected to
//       valid prior to & during the posedge Clk. They are then stored 
//       inside FRU per Clk and may change externally prior to next posedge.
//
//     Wait_for _data => request to PCU to stall Step_EXU till data available
//       from MAU.  1=> asserted, need stall, 0=> deasserted, normal ops.
//
// CHIP/FRU Resetn assumed asserted neg. 
//        
//----------------------------------------------------------------------

`include "decode.v"


 
///////////////////////////////////////////////////////////////
// General Definitions  
///////////////////////////////////////////////////////////////    
`define asserted     1'b1 
`define R31          5'b11111
`define R31_contents 32'h0000_0000 

// Definitions for MUX signals SEL_A and SEL_B                                  
`define TAKE_EXUp_d  2'b11                                                      
`define TAKE_MAUp_d  2'b10                                                      
`define TAKE_WBp_d   2'b01                                                      
`define TAKE_REG_d   2'b00

////////////////////////////////////////////////////////////////
  // Behavioral module fru
				//////////////// //////////////////////////////////////////////////
  module fru(Wait_for_data, Opd1, Opd2, sys_clk, iStep_EXU, iStep_MAU, iStep_WB, iWork_EXU, iWork_MAU, iWork_WB,iRegA, iRegB, iEXU_Dest, iMAU_Dest, iEXU_ResData, iMAU_Data,iDecode, iEXU_Cond, iMAU_Cond, iResetn);
// Inputs
   input 	 iStep_EXU,		// Latch data @ EXU input on nxt sys_clk (from PCU)
	 iStep_MAU,		// Latch data @ MAU input on nxt sys_clk (from PCU)
	 iStep_WB,		// Latch data @ WB input on nxt sys_clk  (from PCU)
	 iWork_EXU,		// Valid work in EXU nxt sys_clk period  (from PCU)
	 iWork_MAU,		// Valid work in MAU nxt sys_clk period  (from PCU)
	 iWork_WB,		// Valid work in WB nxt sys_clk period   (from PCU)
	 iEXU_Cond,		// Norm = 1 & = 0 iff cmov false     (from EXU)
	 iMAU_Cond,		// Norm = 1 & = 0 iff cmov false     (from MAU)
	 iResetn;		// processor reset, assert neg      (from CHIP)
    
   
reg 	 EXU_Cond,		// Norm = 1 & = 0 iff cmov false     (from EXU)
	 MAU_Cond;		// Norm = 1 & = 0 iff cmov false     (from MAU)
      
 
   input [5:0] iRegA,		// register address of operand A   (from IDU)
	
       iRegB,		// register address of operand B   (from IDU)
	       iEXU_Dest,	// EXU's Dest add, w/MSB =1 =>valid(from EXU)
	       iMAU_Dest;	// MAU's Dest add, w/MSB =1 =>valid(from MAU)
  
   input [31:0] iEXU_ResData,	// EXU's out d_bus for fwding  (from EXU)
		iMAU_Data;	// MAU out d_bus, fwding & WB  (from MAU)

   input `DEC 	iDecode;      // from IDU, decode of inst    (from IDU)            

   reg [5:0] RegA,         // register address of operand A   (from IDU)
             RegB,         // register address of operand B   (from IDU)
             EXU_Dest,     // EXU's Dest add, w/MSB =1 =>valid(from EXU)
             MAU_Dest;     // MAU's Dest add, w/MSB =1 =>valid(from MAU)

   reg [31:0] EXU_ResData, // EXU's out d_bus for fwding  (from EXU)
	     MAU_Data;    // MAU out d_bus, fwding & WB  (from MAU)

   reg `DEC  Decode;      // from IDU, decode of inst    (from IDU)            


   // Outputs

   output [31:0] Opd1,		// Operand normally corresponding to
				// contents of RegA  
				// unless forwarding occurrs      (to EXU)

		 Opd2;		// Operand norm corresponding to 
				// contents of RegB 
				// unless forwarding occurrs      (to EXU)
  
   output 	 Wait_for_data; // FRU detects data dependency &
				// requests a stall of EXU till data
				// can be forwarded               (to PCU)

                             
   // Declarations 

   reg [31:0] 	 REG_file[7:0]; // REGister file

   reg [31:0] 	 Read_RegA,	// stores output <RegA> on fall edge cp     
		 Read_RegB,	// stores output <RegB> on fall edge cp   
		 dOpd1,		// data bus normally driven by <RegA>           
		 dOpd2,		// data bus normally driven by <RegB>
		 WBp_Data;	// to latch output of MAU_Data for WBp 
                


   reg [5:0] 	 WBp_add;	// latch output of MAU_Dest, w/ valid
  
 
   
   reg [1:0] 	 SEL_A, SEL_B;   // for selecting source of dOpd's 

   reg 		 WBp_Cond,       // value of MAU_Cond passed on to WB
		 
		 EXUp_data_source, // tells comparitors the data src 
				// that EXUp_add is associated with 
                                  // (ie EXUout or MAUout) => qualifies
                                  // forwarding EXU data & is .....


                                // Step & Work inputs to FRU change
		 LStep_EXU,      // after posedge of sys_clk.  To guarantee 
		 LStep_MAU,	// that they do not effect outputs of 
		 LStep_WB,       // the FRU during sys_clk these
		 LWork_EXU,      // Step & Work signals are assigned to
		 LWork_MAU,
		 LWork_WB,	// internal versions as per below.
		 Resetn;	//Reset
   
   

   reg 		 dWait_for_data;	// used to gen Wait_for_data sig. 

   input 	 sys_clk;
   
/////////////////////////////////////////////////////////////                   
// General assignments. All Outputs are delayed by `delay.
// Step and Work Inputs to FRU are latched on posedge and are
// guaranteed internally stable for this sys_clk.
//////////////////////////////////////////////////////////////

  initial 
    begin
     SEL_A = 0;
     SEL_B = 0;
     dOpd1 = 32'h0000_0000;
     dOpd2 = 32'h0000_0000;
      REG_file[0] = 32'h0000_0000;
      REG_file[1] = 32'h0000_0000;
      REG_file[2] = 32'h0000_0000;
      REG_file[3] = 32'h0000_0000;
      REG_file[4] = 32'h0000_0000;
      REG_file[5] = 32'h0000_0000;
      REG_file[6] = 32'h0000_0000;
      REG_file[7] = 32'h0000_0000;
      REG_file[8] = 32'h0000_0000; 
      REG_file[9] = 32'h0000_0000;
      REG_file[10] = 32'h0000_0000;
      REG_file[11] = 32'h0000_0000; 
      REG_file[12] = 32'h0000_0000; 
      REG_file[13] = 32'h0000_0000; 
      REG_file[14] = 32'h0000_0000;// 
      REG_file[15] = 32'h0000_0000;// 
      REG_file[16] = 32'h0000_0000;// 
      REG_file[17] = 32'h0000_0000;// 
      REG_file[18] = 32'h0000_0000;// 
      REG_file[19] = 32'h0000_0000;// 
      REG_file[20] = 32'h0000_0000;// 
      REG_file[21] = 32'h0000_0000;// 
      REG_file[22] = 32'h0000_0000;// 
      REG_file[23] = 32'h0000_0000;// 
      REG_file[24] = 32'h0000_0000;// 
      REG_file[25] = 32'h0000_0000;// 
      REG_file[26] = 32'h0000_0000;// 
      REG_file[27] = 32'h0000_0000;// 
      REG_file[28] = 32'h0000_0000;// 
      REG_file[29] = 32'h0000_0000;// 
      REG_file[30] = 32'h0000_0000;// 
      REG_file[31] = 32'h0000_0000;// 
     Read_RegA = 32'h0000_0000;	// 
     Read_RegB = 32'h0000_0000;	// 
     WBp_add = 6'b0000_00;	// 
     LStep_EXU =1'b0;		// 
     LStep_MAU =1'b0;		// 
     LStep_WB  =1'b0;		// 
     LWork_EXU =1'b0;
     LWork_MAU =1'b0;		// 
     LWork_WB  =1'b0;
     WBp_Data = 1'b0;		// 
     WBp_Cond = 1'b0;
     EXUp_data_source = 1'b0;
     Resetn = 1'b0;
     EXU_Cond= 1'b0;
     MAU_Cond= 1'b0;
     RegA=6'b0000_00;
     RegB=6'b0000_00;
     EXU_Dest=6'b0000_00;
     MAU_Dest=6'b0000_00;
     EXU_ResData=32'h0000_000;
     MAU_Data=32'h0000_000;
     Decode=6'b0000_00;
     dWait_for_data = 0;
              
    end				// initial begin

   always @(posedge sys_clk) 
     begin
	Resetn <= iResetn;
	LStep_EXU <=  iStep_EXU;
	LStep_MAU <=  iStep_MAU;	// 
	LStep_WB  <=  iStep_WB;	// 
	LWork_EXU <=  iWork_EXU;	// 
	LWork_MAU <=  iWork_MAU;	// 
	LWork_WB  <=  iWork_WB;	// 
	EXU_Cond <= iEXU_Cond;	// 
	MAU_Cond <= iMAU_Cond;	// 
	RegA <= iRegA;		// register address of operand A   (from IDU)
	RegB <= iRegB;		// register address of operand B   (from IDU)
	EXU_Dest <= iEXU_Dest;	// EXU's Dest add, w/MSB =1 =>valid(from EXU)
	MAU_Dest <=iMAU_Dest;	// MAU's Dest add, w/MSB =1 =>valid(from MAU)
	EXU_ResData <=iEXU_ResData;// EXU's out d_bus for fwding  (from EXU)
	MAU_Data <= iMAU_Data;	// MAU out d_bus, fwding & WB  (from MAU)
	Decode <= iDecode;	// 
     end			// always @ (posedge sys_clk)

  assign Wait_for_data =  dWait_for_data;
   assign Opd1          =  dOpd1;
   assign Opd2          =  dOpd2;// 
   

///////////////////////////////////////////////////////////
// Reset function (takes *all* FRU outputs to 0 during Reset)
// & zero's all of the REG_file IFF Reset > 32 sys_clk's.
// If Reset < 32 sys_clk's then lowest REG's zero'd until
// Reset de-asserted.
///////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////
// Reset function (takes *all* FRU outputs to 0 during Reset)
// & zero's all of the REG_file IFF Reset > 32 sys_clk's.
// If Reset < 32 sys_clk's then lowest REG's zero'd until
// Reset de-asserted.
///////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////
// Simple mirror of pipe created to pass values A.R.
////////////////////////////////////////////////////////////
// Create EXUp status (valid for EXUperiod) 
 
    always @(posedge sys_clk) if (LStep_EXU) begin 
 EXUp_data_source <= (Decode[`DEC_MEM] & Decode[`DEC_MEM_ACC] &// 
 ~Decode[`DEC_MEM_ST]); 
  
  end
 


// Create WBp status (valid for WBperiod)
always @(posedge sys_clk) if (LStep_WB) 
     begin
       WBp_Cond         <= MAU_Cond;
       WBp_add [5:0]    <= MAU_Dest [5:0];
       WBp_Data [31:0]  <= MAU_Data [31:0];
     end

////////////////////////////////////////////////////////////
// Compare pipe Dest addresses to RegA and RegB values and 
// and determine MUX control values.  For whatever reason, if
// Reg32 is a Dest it is NOT forwarded. 
// Also determines value of "Wait_for _data" for requesting 
// (from the PCU) a stall (no step) of EXU till data from MAU
// can be forwarded, minimum 1-cycle delay.
////////////////////////////////////////////////////////////
 always @(RegA  or RegB  or EXU_Dest  or MAU_Dest or 
           EXUp_data_source or EXU_Cond or MAU_Cond or
           WBp_add  or LWork_EXU or LWork_MAU or LWork_WB) 
   begin
   
     // Determine MUX_A control 
     if ((RegA[5]==`asserted) && (RegA==EXU_Dest) && 
         (EXUp_data_source!=`asserted) && (EXU_Cond==`asserted) &&
         (LWork_EXU==`asserted) && (RegA[4:0]!=`R31)) begin 
              SEL_A <= `TAKE_EXUp_d;
                                   
     end else if ((RegA[5]==`asserted) && (RegA==MAU_Dest) &&
                  (MAU_Cond==`asserted) && (LWork_MAU==`asserted) &&
                  (RegA[4:0]!=`R31)) begin 
              SEL_A <= `TAKE_MAUp_d;
                                           
     end else if ((RegA[5]==`asserted) && (RegA==WBp_add) &&  
                  (LWork_WB==`asserted) && (WBp_Cond==`asserted) &&  
                  (RegA[4:0]!=`R31)) begin
 SEL_A <= `TAKE_WBp_d;// 
 
     end else SEL_A <= `TAKE_REG_d;


     // Determine MUX_B control
     if ((RegB[5]==`asserted) && (RegB==EXU_Dest) &&  
         (EXUp_data_source!=`asserted) && (EXU_Cond==`asserted) &&
         (LWork_EXU==`asserted) && (RegB[4:0]!=`R31)) begin 
              SEL_B <= `TAKE_EXUp_d; 
                                   
     end else if ((RegB[5]==`asserted) && (RegB==MAU_Dest) && 
                  (MAU_Cond==`asserted) && (LWork_MAU==`asserted) && 
                  (RegB[4:0]!=`R31)) begin
              SEL_B <= `TAKE_MAUp_d; 
                                          
     end else if ((RegB[5]==`asserted) && (RegB==WBp_add) && 
                  (LWork_WB==`asserted) && (WBp_Cond==`asserted) &&
                  (RegB[4:0]!=`R31)) begin  
	SEL_B <= `TAKE_WBp_d;
                       
     end else SEL_B <= `TAKE_REG_d;


   // Determine if "Wait_for_data" request of PCU is required
     if( ((RegA[5]==`asserted) && (RegA==EXU_Dest) &&  
         (EXUp_data_source==`asserted) && 
         (LWork_EXU==`asserted) && (RegA[4:0]!=`R31))  
                               ||

         ((RegB[5]==`asserted) && (RegB==EXU_Dest) &&  
         (EXUp_data_source==`asserted) && 
         (LWork_EXU==`asserted) && (RegB[4:0]!=`R31)) ) begin 
              dWait_for_data <= `asserted;
     end else dWait_for_data <= ~`asserted;
   end
 
///////////////////////////////////////////////////////////////////////////
// Forward the correct data bus to the dOpd1 and dOpd2 outputs of the MUX's
// per the MUX SEL values determined above. If RegA[4:0] or RegB[4:0] = R31
// then associated Opd will be set to 0.  Currently this is done regardless
// of Reg's valid bit. 
///////////////////////////////////////////////////////////////////////////

  always @(RegA  or RegB  or EXU_Dest  or MAU_Dest or Read_RegA or
        Read_RegB or WBp_add  or LWork_EXU or LWork_MAU or LWork_WB or 
        SEL_A or SEL_B or
        EXU_ResData or MAU_Data or WBp_Data or Read_RegA or Read_RegB)
   begin

     // Determine MUX_A source 
     case (RegA[4:0])
       `R31:            dOpd1 <= `R31_contents;  
        default: case (SEL_A)
                 `TAKE_EXUp_d:  dOpd1 <= EXU_ResData;
                 `TAKE_MAUp_d:  dOpd1 <= MAU_Data;
                 `TAKE_WBp_d:   dOpd1 <= WBp_Data;
                 `TAKE_REG_d:   dOpd1 <= Read_RegA;
                 endcase
     endcase

     // Determine MUX_B source
     case (RegB[4:0])
       `R31:            dOpd2 <= `R31_contents;
        default: case (SEL_B)
                 `TAKE_EXUp_d:  dOpd2 <= EXU_ResData;  
                 `TAKE_MAUp_d:  dOpd2 <= MAU_Data;  
                 `TAKE_WBp_d:   dOpd2 <= WBp_Data;  
                 `TAKE_REG_d:   dOpd2 <= Read_RegB;
                 endcase
     endcase
   end
//////////////////////////////////////////////////////////////////////////////
// REG_file is an array of 32 register configured by the access logic as a 
// special dual-port RAM.  Reads are on the first 1/2 of sys_clk and writes are 
// on the second half of sys_clk which avoids contention for the same register. 
// This is opposite Toobsie and results in an extra WB forwarding bus but 
// increases speed by allowing the MUX propogation delay and
// tsu of EXU input register (if synthesized) to occur in the second 1/2 of
// sys_clk as opposed to compressing everything into the second 1/2 of sys_clk. 
// If the valid bit is not asserted then no read takes place of REG_file
// and old READ_Reg data will come thru on the Opd's to the EXU per Compare 
// and Forwarding sections. 
// If R31 is the Dest address during WB, which should *NEVER* happen because 
// of the valid bit, it will be written into REG_file BUT the MUX section is 
// designed to substitute 0 when R31 is read. 
//////////////////////////////////////////////////////////////////////////////

endmodule //fru   
