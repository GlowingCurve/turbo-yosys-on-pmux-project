# 测试用例目录命名规则

- `testcase` 下的第一层目录表示用例来源：`opencores_case`、`axi_case`、`official_case` 和 `avr_case`。
- 来源目录下的每个用例目录使用 Verilog 顶层模块名称，保留原有大小写。
- 每个用例目录直接存放该用例所需的 Verilog 原文件，包括顶层模块、辅助模块及被引用的定义文件。
- 原有 Verilog 文件保留原有文件名。文件名与用例目录名可以不同
