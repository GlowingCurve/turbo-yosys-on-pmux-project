# explog

## 调用

需要 Python 3.11+。在本仓库根目录安装：

```bash
python3 -m pip install -e ./explog
explog init --config explog.toml
explog run --config explog.toml --name "基准实验"
explog run --config explog.toml --name "参数实验" --parent-id 1 --message "调整参数"
explog list --log experiments.jsonl
```

`python3 -m explog` 与 `explog` 等价。各子命令的完整参数通过 `--help` 查看。

- `init` 检查配置、Git 仓库和命令的可执行程序，创建日志与数据根目录；可以重复调用，调用期间不执行脚本。配置缺失时生成空模板并以非零状态退出，填写后重新调用。
- `run` 依次捕获状态、执行实验脚本、执行处理脚本，全部成功后追加日志，标准输出仅包含实验 ID。`--name` 必填，名称必须包含非空白字符；`--message` 可省略，默认为空字符串。ID 自动使用十进制实验序号，从 `1` 开始，按照日志和数据根目录中的最大序号递增；已有记录和目录的数量也作为序号下限。失败实验保留的目录占用对应序号。`--parent-id` 由用户指定，父节点必须已存在于同一日志中，省略时创建根节点。
- `list` 按时间升序显示时间、ID、父节点、名称和说明文字；指定 `--log` 后可独立读取日志。
- `init`、`list` 的 `--config` 默认为 `explog.toml`；三个命令均可用 `--log` 覆盖配置中的日志路径。CLI 路径相对于当前目录。

## 配置

TOML 恰好包含以下五个键。脚本由项目提供，实验和处理命令列表可以为空：

```toml
log = "experiments.jsonl"
data_root = "experiment-data"
repository_state_command = ["python3", "scripts/capture_repostate.py"]
experiment_scripts = [["python3", "scripts/run.py"]]
data_processing_scripts = [["python3", "scripts/process.py"]]
```

`log` 相对于配置文件所在目录；`data_root` 相对于 Git 仓库根目录，也可使用绝对路径，但必须位于仓库内部。将数据目录加入 `.gitignore`。直接调用 `run` 时，日志的父目录需要已经存在。

## 脚本协议

每条命令使用非空 argv 数组，元素必须为字符串，首个元素是非空的可执行程序名称。命令直接执行，需要 shell 时在数组中显式指定 `bash` 等程序。所有命令的工作目录均为 Git 仓库根目录，继承环境变量和标准输入。以下参数由 explog 追加，目录参数均为绝对路径；调用前已创建 `data_root/ID/`、`raw/` 和 `processed/`。

| 命令 | 追加参数 | 输出约定 |
| --- | --- | --- |
| `repository_state_command` | `--output <data_root/ID>` | 写入状态文件，stdout 仅输出该文件的一行路径 |
| `experiment_scripts` | `--output <data_root/ID/raw>` | 实验结果写入输出目录 |
| `data_processing_scripts` | `--input <data_root/ID/raw> --output <data_root/ID/processed>` | 读取实验结果，将处理结果写入输出目录 |

捕获命令的 stdout 必须使用 UTF-8，恰好包含一行非空路径，允许前后空白和省略末尾换行；额外空行也会报错。相对路径以仓库根目录为基准。解析符号链接后，路径必须指向本次运行目录内已存在的普通文件。状态文件的内容、格式和扩展名由脚本决定。

脚本的诊断信息写入 stderr；实验与处理脚本的 stdout 也转发到 explog 的 stderr。因此可以直接取得运行 ID：

```bash
id=$(explog run --config explog.toml --name "参数实验" --message "调整参数")
```

捕获命令执行一次，随后按配置顺序执行全部实验命令，再按顺序执行全部处理命令。同组命令共享目录，脚本负责避免文件名冲突。所有命令必须以状态码 `0` 退出；任一步骤失败立即终止，返回非零状态，保留已有数据，日志仅记录全部脚本成功的实验。同一日志的运行应串行调用。

## 工具组合与错误处理

explog 负责调用外部工具和追加实验记录。状态捕获工具负责保存仓库状态，实验工具负责生成原始数据，处理工具负责读取原始数据并生成处理结果。各个工具通过 argv、文件路径和标准输入输出组合，每个工具也可以独立调用。

`run` 的 stdout 只输出生成的实验 ID，便于命令替换；脚本诊断信息和实验、处理工具的输出通过 stderr 传递。工具继承标准输入和环境变量，命令参数以 argv 数组直接传递。JSONL 日志可通过 `jq`、`sort` 等 UNIX 工具读取和处理：

```bash
jq -r '[.id, .parent_id, .name, .message] | @tsv' experiments.jsonl
```

代码遵循 fast-fail：字段和路径校验在使用位置完成，校验失败立即终止；文件操作、Git 命令和实验脚本的错误直接向调用方传播。JSON/TOML 解析异常会补充文件路径，JSON 错误还包含日志行号。CLI 直接调用对应功能，失败时通过 Python 的 stderr 错误信息和非零退出状态报告问题。

源代码按照配置、目录、命令执行、状态捕获、日志读写和列表显示划分职责，每个函数包含一行简短中文注释。

## 日志协议

日志为 UTF-8 JSONL，每个实验追加一个 JSON 对象，包含以下字段；可直接交给 `jq` 等工具处理。

| 字段 | 内容 |
| --- | --- |
| `id` | 自动生成的十进制实验序号，保存为字符串 |
| `name` | 用户通过 `--name` 指定的必填名称 |
| `parent_id` | 父节点 ID，根节点为 `null` |
| `timestamp` | 脚本完成后创建记录的 UTC 时间，精确到秒，格式为 `YYYY-MM-DDTHH:MM:SSZ` |
| `message` | `--message` 的原始文字，可为空字符串 |
| `repository_state_path` | 状态文件相对于仓库根目录的 POSIX 路径 |
| `data_dir` | 本次运行目录相对于仓库根目录的 POSIX 路径 |

## 查看实验结果

本仓库的 `viz/` 页面固定读取仓库根目录的 `experiments.jsonl`，根据记录中的 `data_dir` 与 `repository_state_path` 定位结果和状态文本。使用页面时，名称严格等于 `baseline` 的实验必须正好一个；每条记录都必须拥有完整的 `processed/results.json`。分析文件 `testcase/analysis.json` 提供各用例的 `pmux` 数量。

页面可以选择比较实验、切换基准、筛选来源，并通过总体结果卡片上的“详情”查看记录字段与仓库状态。安装和启动见 [网页使用说明](../viz/README.md)，字段与校验规则见 [数据与 HTTP 接口](../viz/docs/data-and-api.md)。
