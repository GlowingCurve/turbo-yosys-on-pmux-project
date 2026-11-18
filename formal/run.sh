#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
work="$root/.work/eqy"
mkdir -p "$work/scratch"
export TMPDIR="$work/scratch"
logs=()

for source in testcase/official_case/test*/test*.v; do
    case_name="$(basename -- "$source" .v)"
    output="$work/$case_name"
    mkdir -p "$output"
    ./yosys/build/yosys -Q -T -p "read_verilog $source; synth_intel -family cycloneiv -top $case_name; write_verilog -noattr $output/netlist.v" > "$output/synth.log" 2>&1
    EQY_CASE="$case_name" eqy -f -j 4 -d "$output/proof" formal/verify.eqy 2>&1 | tee "$output/eqy.log"
    test -f "$output/proof/PASS"
    logs+=("$output/eqy.log")
done

printf '\n'
grep -hF 'DONE (PASS, rc=0)' "${logs[@]}"
