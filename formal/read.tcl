if {$argc != 1 || [lindex $argv 0] ni {gold gate}} {
    error "read.tcl requires gold or gate"
}
set top $::env(EQY_CASE)
if {[lindex $argv 0] eq "gold"} {
    yosys "read_verilog -formal testcase/official_case/$top/$top.v"
} else {
    yosys "read_verilog -formal .work/eqy/$top/netlist.v"
}
yosys "prep -top $top -flatten"
