# Yosys 综合实验

在仓库根目录执行以下命令。脚本使用 Python 3.11 或更新版本。原版与优化版 Yosys 分别位于 `yosys-original/build/yosys` 和 `yosys-optimized/build/yosys`。对已配置的 CMake 构建目录执行增量构建：

```bash
python3 scripts/build_yosys.py --target both
```

## 记录实验

```bash
explog init --config explog.toml
explog run --config explog.toml --name "综合基准"
explog list --config explog.toml
```

默认配置预热 2 轮、正式测量 6 轮。严格环境控制需要 Linux cgroup v2 和管理员权限，普通用户通过 `sudo -n` 执行环境设置命令。原始数据和处理结果分别保存到 `experiment-data/<ID>/raw/` 和 `experiment-data/<ID>/processed/`。

## 实验配置

| 参数 | 含义 |
| --- | --- |
| `yosys.original`、`yosys.optimized` | 原版和优化版可执行文件 |
| `yosys.build_optimized` | 测量前增量构建优化版 |
| `benchmark.cases` | 用例目录或包含用例的父目录列表 |
| `benchmark.warmup_rounds`、`benchmark.formal_rounds` | 预热轮数和正式测量轮数 |
| `benchmark.timing` | `rusage` 使用进程 CPU 时间，`yosys_log` 使用 Yosys 日志时间 |
| `benchmark.env_control` | 启用 CPU、IRQ 和频率控制 |
| `benchmark.jobs` | 并发进程数，启用环境控制时设为 1 |
| `environment.host_cpus`、`environment.isolated_cpus` | 调度进程和中断使用的核心、隔离分区使用的核心 |
| `environment.benchmark_cpu` | 综合进程使用的隔离核心 |
| `environment.target_khz`、`environment.settle_seconds` | 锁定频率（kHz）和测量前等待时间（秒） |

通过 `--settings experiments.toml` 读取配置。显式命令行参数覆盖配置值。TOML 中的相对路径以仓库根目录为基准，命令行中的相对路径以当前工作目录为基准。

## 快速验证

独立运行默认预热 0 轮、正式测量 1 轮，并关闭环境控制。

```bash
python3 scripts/run_benchmark.py testcase/official_case --no-build --jobs 2
python3 scripts/run_benchmark.py testcase/official_case/test1 --no-build --output .work/quick/raw
python3 scripts/analyze_benchmark.py --input .work/quick/raw --output .work/quick/processed
```

省略 `--output` 时，实验保存到 `.work/run_benchmark/YYYYMMDD_HHMMSS/`。分析结果包含 `results.json` 和 `report.md`。

## 查看和比较实验

```bash
python3 scripts/analyze_benchmark.py --exp 1
python3 scripts/analyze_benchmark.py --exp 1 --group official_case --sort lut4
python3 scripts/analyze_benchmark.py --compare 1 2 --detail
```

变化率为负时表示指标减少。`--compare` 比较两次实验共同用例的优化版结果。
