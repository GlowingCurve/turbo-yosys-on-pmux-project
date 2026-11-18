# AVR 样例

源码来自 [aman-goel/avr](https://github.com/aman-goel/avr/tree/master/tests/opensource) 的 `tests/opensource` 目录，固定 commit 为 `9a76dc632066c4416cebccda3a4974a4f8adede8`。

每个样例目录使用其 Verilog 顶层模块名称，直接存放该功能模块及必要依赖。源文件保留版权、来源说明、参数、接口和可综合逻辑。原始 `.sv` 文件清理为 Verilog 后保存为同名 `.v`，其他 Verilog 原文件保留原文件名。

`fru` 的定义文件 `decode.v` 来自 `vis_QF_BV_fru32_p1/includes/decode.v`，直接存放在 `fru` 样例目录中。`read_packet` 所需的 `time_stamps` 和 `start_code_prefix` 保存在同一份 `mpeg_1.v` 中。

| 样例目录及顶层 | 原文件，相对于 `tests/opensource` | 原顶层 |
|---|---|---|
| `heap` | `Heap/main.v` | `main` |
| `icctl` | `pj_icu/icctl1.v` | `icctl` |
| `b12` | `itc99_b12/b12_1.v` | `main` |
| `sdlx_control` | `sdlx/control1.v` | `main` |
| `huffmanDec` | `Huffman_dec/main.v` | `huffmanDec` |
| `huffmanEnc` | `Huffman_dec/main.v` | `huffmanEnc` |
| `buffer_alloc` | `h_BufAl/main.sv` | `main` |
| `srFIFO` | `h_FIFO/main.v` | `srFIFO` |
| `rbFIFO` | `h_FIFO/main.v` | `rbFIFO` |
| `instruction_buffer` | `h_Ibuf/main.sv` | `main` |
| `spinner` | `h_Spinner/main.sv` | `main` |
| `crc` | `h_CRC/main.sv` | `main` |
| `tic_tac_toe` | `h_TicTacToe/main.sv` | `main` |
| `rrobin` | `h_Rrobin/main.sv` | `main` |
| `vsa16` | `h_Vsa16/main.sv` | `main` |
| `b02` | `h_b02/main.sv` | `main` |
| `b03` | `h_b03/main.sv` | `main` |
| `b05` | `h_b05/main.sv` | `main` |
| `daio` | `v_DAIO/main.v` | `main` |
| `unidec` | `v_Unidec/main.sv` | `main` |
| `fru` | `vis_QF_BV_fru32_p1/fru32_p1.v` | `fru` |
| `bcu` | `vis_QF_BV_bcuvis32/bcuvis32.v` | `bcu` |
| `am2901` | `vis_arrays_am2901/am2901.v` | `main` |
| `am2910` | `vis_arrays_am2910_p1/am2910_p1.v` | `main` |
| `branch_predictor` | `vis_arrays_bpbs_p1/bpbs_p1.v` | `main` |
| `miim` | `miim/vMiim.v` | `main` |
| `parse_pack_header` | `mpeg/mpeg_1.v` | `parse_pack_header` |
| `parse_system_header` | `mpeg/mpeg_1.v` | `parse_system_header` |
| `read_packet` | `mpeg/mpeg_1.v` | `read_packet` |
| `pi_state_machine` | `pi_bus/main_1_2.v` | `pi_state_machine` |
| `controller` | `h_Arbiter/main.v` | `controller` |
| `cell` | `h_TreeArb/main.sv` | `cell` |
| `pcache` | `cache_coherence_two/two_processor_bin_2.v` | `pcache` |
| `character_transform` | `h_Vlunc/main.sv` | `main` |
