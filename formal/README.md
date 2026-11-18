在项目根目录运行：

```bash
bash formal/run.sh
```

`verify.eqy` 直接比较 `testcase/official_case` 中的原始 RTL 与项目中 `yosys/build/yosys` 执行完整 `synth_intel -family cycloneiv` 后的 Verilog 网表。EQY 使用 SBY 的 ABC PDR 引擎进行时序等价证明，覆盖复位、使能、初始化及跨周期行为。

终端实时显示每项 EQY 验证的完整输出，结束后集中显示本次运行的原始 `DONE (PASS, rc=0)` 行，方便截图。输出同时保存在各 testcase 的 `eqy.log` 中。

`cells.v` 提供 LUT 与 DFF 的功能定义。DFF 模型对应本项目 `ff_map.v` 生成的 `prn=1`、`aload=0` 端口配置，覆盖上升沿采样、低有效异步清零、使能和 `power_up`；同步清零、同步装载按 `clrn`、`ena`、`sclr`、`sload` 的优先级实现。

控制信号优先级依据 [Altera 寄存器控制信号说明](https://docs.altera.com/r/docs/683082/25.1/quartus-prime-pro-edition-user-guide/secondary-register-control-signals-such-as-clear-and-clock-enable)，上电参数依据项目的 `yosys/techlibs/intel/common/ff_map.v`。

结果保存于 `.work/eqy/`，包含每个 testcase 的 `netlist.v`、`synth.log`、`eqy.log` 和完整 `proof/` 目录。证明成功标记为 `proof/PASS`。运行需要项目中的 Yosys 和 EQY/SBY。
