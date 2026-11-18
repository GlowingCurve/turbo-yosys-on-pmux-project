# Yosys `$pmux` 综合优化复现仓库

本仓库提供优化版 Yosys 与上游原版 Yosys 的对比实验环境，用于在 Intel Cyclone IV（`synth_intel -family cycloneiv`）综合流程下复现 **LUT4 面积、综合时间与峰值内存** 对比结果。优化原理与实验结论详见 [docs/技术报告.pdf](docs/技术报告.pdf)。

## 1. 环境准备与编译

需使用 **Linux** 系统、**Python 3.11+**，以及构建 Yosys 所需的常规依赖（Clang/GCC、CMake、Ninja、Bison、Flex、Readline、Tcl、Zlib、libffi）。

克隆仓库并初始化全部递归子模块（含 `abc`），配置并编译原版与优化版 Yosys，然后安装实验记录工具 `explog`：

```bash
git submodule update --init --recursive

cmake -S yosys-original -B yosys-original/build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake -S yosys-optimized -B yosys-optimized/build -G Ninja -DCMAKE_BUILD_TYPE=Release
python3 scripts/build_yosys.py --target both

python3 -m pip install -e ./explog
```

## 2. 运行实验

### 方式一：快速复现（无需管理员权限，适用于任意 Linux 机器）

如果不开启底层硬件隔离，可直接通过命令行并发运行全部测试用例并输出对比报告：

```bash
python3 scripts/run_benchmark.py testcase --no-build --no-env-control --warmup 1 --rounds 3 --jobs 8 --output .work/repro/raw
python3 scripts/analyze_benchmark.py .work/repro/raw --output .work/repro/processed
```

也可以只指定某个用例组快速验证（如 `testcase/official_case` 或 `testcase/axi_case`）。

### 方式二：使用 `explog` 进行标准实验记录（支持严格环境隔离）

通过 `explog` 运行实验会自动记录仓库 Git 状态、执行基准测试、汇总分析并在终端输出对比表：

```bash
explog init --config explog.toml
explog run --config explog.toml --name "baseline" --message "复现基准对比"
explog list --config explog.toml
```

> **严格环境控制注意事项**：
> `experiments.toml` 默认开启 `env_control = true`（启用 cgroup v2 核心隔离、中断迁移与 CPU 锁频，配合微秒级 CPU 时间测量）：
> 1. 执行前需具备免密 `sudo` 权限（`sudo -n`）。若无 root 权限，请先在 `experiments.toml` 中将 `env_control` 改为 `false`。
> 2. `[environment]` 默认按 16 核 32 线程处理器配置。**在不同硬件上开启 `env_control = true` 前，请根据本机 `lscpu` 拓扑修改 `experiments.toml` 中的核心范围（`host_cpus`、`isolated_cpus`、`benchmark_cpu`）及锁频值（`target_khz`）**。

## 3. 参数配置（`experiments.toml`）

`explog run` 默认读取根目录的 `experiments.toml`，常用配置项如下（单跑 `scripts/run_benchmark.py` 时也可通过同名命令行参数临时覆盖，详见 `--help`）：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `yosys.build_optimized` | `true` | 实验开始前是否自动增量编译 `yosys-optimized` |
| `benchmark.cases` | `["testcase"]` | 待测目录列表，可改为子集如 `["testcase/axi_case"]` |
| `benchmark.warmup_rounds` | `2` | 预热轮数（`>= 0`） |
| `benchmark.formal_rounds` | `6` | 正式测量轮数（`>= 1`，原版与优化版正反交替执行） |
| `benchmark.timing` | `"rusage"` | `"rusage"`（微秒级纯 CPU 时间）或 `"yosys_log"`（Yosys 日志计时） |
| `benchmark.env_control` | `true` | 是否锁定频率、隔离核心并迁走系统中断 |
| `benchmark.jobs` | `1` | 并发进程数（`env_control = true` 时必须为 `1`） |

## 4. 查看结果与等价性验证

每次 `explog run` 完成后，完整 Markdown 报表与 JSON 数据保存在 `experiment-data/<ID>/processed/`（`report.md` 与 `results.json`）。也可随时在终端查询或对比不同实验（变化率为负值代表减少/加速）：

```bash
# 查看第 1 号实验汇总表
python3 scripts/analyze_benchmark.py --exp 1

# 查看逐用例明细，并按 LUT4 缩减幅度排序
python3 scripts/analyze_benchmark.py --exp 1 --detail --sort lut4

# 横向对比第 1 号与第 2 号两次实验的优化版差异
python3 scripts/analyze_benchmark.py --compare 1 2
```

如需运行综合前后的形式化时序等价性验证（基于 EQY / SBY），请参考 [formal/README.md](formal/README.md)。
