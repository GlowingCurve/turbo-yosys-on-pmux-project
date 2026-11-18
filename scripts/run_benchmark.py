import argparse
import fcntl
import json
import os
import re
import resource
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time
import tomllib
import traceback
from contextlib import ExitStack, contextmanager, nullcontext, suppress
from datetime import datetime
from itertools import islice
from pathlib import Path

if __package__:
    from .build_yosys import PROJECT_ROOT, build_yosys
else:
    from build_yosys import PROJECT_ROOT, build_yosys

CGROUP_ROOT = Path("/sys/fs/cgroup")
CGROUP = CGROUP_ROOT / "yosys-finegrain"
CPU_SAMPLE = struct.Struct("=dd")
VERSIONS = ("original", "optimized")
TIMINGS = ("rusage", "yosys_log")
FOOTER = re.compile(
    r"^End of script\..*?time:\s*(\d+(?:\.\d+)?)s,\s*user:\s*(\d+(?:\.\d+)?)s,"
    r"\s*system:\s*(\d+(?:\.\d+)?)s,\s*MEM:\s*(\d+(?:\.\d+)?)\s*MB peak\s*$",
)

def parse_settings(parser):
    # 合并默认配置、TOML 文件和命令行参数。
    parser.add_argument("cases", nargs="*", type=Path)
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--warmup", type=int, dest="warmup_rounds")
    parser.add_argument("--rounds", type=int, dest="formal_rounds")
    parser.add_argument("--timing", choices=TIMINGS)
    parser.add_argument("--env-control", action=argparse.BooleanOptionalAction)
    parser.add_argument("--jobs", type=int)
    parser.add_argument("--settle", type=int, dest="settle_seconds")
    parser.add_argument("--build", action=argparse.BooleanOptionalAction, dest="build_optimized")
    for version in VERSIONS:
        parser.add_argument(f"--yosys-{version}", type=Path, dest=version)
    args = parser.parse_args()
    defaults = {
        "yosys": {"original": "yosys-original/build/yosys",
                  "optimized": "yosys-optimized/build/yosys", "build_optimized": True},
        "benchmark": {"cases": ["testcase"], "warmup_rounds": 0, "formal_rounds": 1,
                      "timing": "rusage", "env_control": False, "jobs": 1},
        "environment": {"host_cpus": "0-7,16-23", "isolated_cpus": "8-15,24-31",
                        "benchmark_cpu": 8, "target_khz": 4000000, "settle_seconds": 60},
    }
    if args.settings:
        try:
            for table, values in tomllib.loads(args.settings.read_text("utf-8")).items():
                if table not in defaults or not isinstance(values, dict):
                    parser.error(f"无效的配置表 {table}")
                for key, value in values.items():
                    if key not in defaults[table] or type(value) is not type(defaults[table][key]):
                        parser.error(f"无效的配置项 {table}.{key}")
                    if key == "cases" and not all(isinstance(path, str) for path in value):
                        parser.error("benchmark.cases 必须为路径字符串列表")
                defaults[table].update(values)
        except (OSError, tomllib.TOMLDecodeError) as error:
            parser.error(str(error))
    yosys, benchmark, environment = (defaults[key] for key in ("yosys", "benchmark", "environment"))
    for table in (yosys, benchmark, environment):
        table.update((key, value) for key, value in vars(args).items()
                     if key in table and value is not None and (key != "cases" or value))
    for version in VERSIONS:
        yosys[version] = (getattr(args, version) or PROJECT_ROOT / yosys[version]).resolve()
    base = Path.cwd() if args.cases else PROJECT_ROOT
    benchmark["cases"] = [(base / path).resolve() for path in benchmark["cases"]]
    if benchmark["warmup_rounds"] < 0 or benchmark["formal_rounds"] < 1:
        parser.error("--warmup 必须大于等于 0，--rounds 必须大于等于 1")
    if not 1 <= benchmark["jobs"] <= 32 or environment["settle_seconds"] < 0:
        parser.error("--jobs 必须介于 1 和 32 之间，--settle 必须大于等于 0")
    if benchmark["env_control"] and benchmark["jobs"] != 1:
        parser.error("开启 env_control 时必须设置 --jobs 1，避免隔离单核争抢")
    if args.timing is None and benchmark["timing"] not in TIMINGS:
        parser.error("benchmark.timing 必须为 rusage 或 yosys_log")
    output = args.output or PROJECT_ROOT / ".work/run_benchmark" / datetime.now().strftime("%Y%m%d_%H%M%S")
    return output.resolve(), yosys, benchmark, environment

def raise_walk_error(error):
    # 报告目录遍历错误。
    raise error

def discover_cases(roots):
    # 收集用例目录和源文件，并生成稳定的用例编号。
    cases = {}
    for root in roots:
        for directory, children, files in os.walk(root, onerror=raise_walk_error, followlinks=False):
            sources = sorted(name for name in files if name.endswith(".v"))
            if sources:
                cases[Path(directory).resolve()] = sources
                children.clear()
    if not cases:
        raise ValueError("未找到包含 .v 源文件的用例目录")
    testcase = (PROJECT_ROOT / "testcase").resolve()
    common_parent = Path(os.path.commonpath([case.parent for case in cases]))
    found = {}
    for case in sorted(cases):
        base = testcase if case.is_relative_to(testcase) else common_parent
        case_id = case.relative_to(base).as_posix()
        if case_id in found:
            raise ValueError(f"用例编号重复 {case_id}")
        found[case_id] = case, cases[case]
    return found

def parse_cpu_set(spec: str) -> set[int]:
    # 将 CPU 编号和范围转换为编号集合。
    cpus = set()
    for item in spec.split(","):
        first, separator, last = item.partition("-")
        cpus.update(range(int(first), int(last if separator else first) + 1))
    return cpus

def admin(*cmd, stdin=None):
    # 以管理员权限执行环境设置命令。
    prefix = () if os.geteuid() == 0 else ("sudo", "-n", "--")
    subprocess.run((*prefix, *cmd), input=stdin, text=True, stdout=subprocess.DEVNULL, check=True)

def write_setting(path, value):
    # 向内核设置文件写入一行值。
    admin("tee", path, stdin=f"{value}\n")

def remove_partition():
    # 终止隔离分区内的进程，等待分区清空并移除分区。
    if CGROUP.is_dir():
        try:
            write_setting(CGROUP / "cgroup.kill", 1)
            while "populated 0" not in (CGROUP / "cgroup.events").read_text().splitlines():
                time.sleep(0.01)
        finally:
            admin("rmdir", "--", CGROUP)

def move_irqs(cleanup, host_cpus):
    # 将可修改的中断移出隔离核心并记录原亲和性。
    command = ("systemctl", "show", "--property=ActiveState", "--value", "irqbalance.service")
    state = subprocess.check_output(command, text=True).strip()
    if state in {"active", "activating", "reloading"}:
        cleanup.callback(admin, "systemctl", "start", "irqbalance.service")
        admin("systemctl", "stop", "irqbalance.service")
    for affinity in sorted(Path("/proc/irq").glob("[0-9]*/smp_affinity_list")):
        if affinity.stat().st_mode & stat.S_IWUSR:
            previous = affinity.read_text().strip()
            if previous != host_cpus:
                cleanup.callback(write_setting, affinity, previous)
                write_setting(affinity, host_cpus)

def set_frequency(policy, minimum, maximum):
    # 按内核允许的顺序调整频率上下限。
    low, high = policy / "scaling_min_freq", policy / "scaling_max_freq"
    updates = [(high, maximum), (low, minimum)]
    if maximum < int(low.read_text()):
        updates.reverse()
    for path, value in updates:
        write_setting(path, value)

@contextmanager
def measurement_environment(env_cfg: dict):
    # 配置隔离环境并按依赖顺序恢复系统设置。
    with ExitStack() as controllers, ExitStack() as cleanup:
        controllers.callback(os.sched_setaffinity, 0, os.sched_getaffinity(0))
        os.sched_setaffinity(0, parse_cpu_set(env_cfg["host_cpus"]))
        lock = os.open(CGROUP_ROOT, os.O_RDONLY | os.O_DIRECTORY)
        controllers.callback(os.close, lock)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        remove_partition()
        cleanup.callback(remove_partition)
        admin("mkdir", "--", CGROUP)
        subtree = CGROUP_ROOT / "cgroup.subtree_control"
        if "cpuset" not in subtree.read_text().split():
            controllers.callback(write_setting, subtree, "-cpuset")
            write_setting(subtree, "+cpuset")
        write_setting(CGROUP / "cpuset.mems", 0)
        write_setting(CGROUP / "cpuset.cpus", env_cfg["isolated_cpus"])
        write_setting(CGROUP / "cpuset.cpus.partition", "isolated")
        move_irqs(cleanup, env_cfg["host_cpus"])
        for policy in sorted(Path("/sys/devices/system/cpu/cpufreq").glob("policy*")):
            previous = [int((policy / f"scaling_{bound}_freq").read_text()) for bound in ("min", "max")]
            cleanup.callback(set_frequency, policy, *previous)
            set_frequency(policy, env_cfg["target_khz"], env_cfg["target_khz"])
        if settle := env_cfg["settle_seconds"]:
            print(f"Environment locked, settling for {settle}s...", file=sys.stderr)
            time.sleep(settle)
        yield

def spawn_yosys(case, argv, directory, record, active, env_cfg):
    # 启动综合进程并读取执行前的 CPU 时间。
    env = os.environ | {"YOSYS_MAX_THREADS": "1", "TMPDIR": str(directory / "tmp")}
    with (directory / "yosys.log").open("wb", buffering=0) as log, ExitStack() as pipes:
        read_fd, write_fd = os.pipe()
        timings_in = pipes.enter_context(os.fdopen(read_fd, "rb"))
        timings_out = pipes.enter_context(os.fdopen(write_fd, "wb", buffering=0))
        if env_cfg:
            read_fd, write_fd = os.pipe()
            startup_in = pipes.enter_context(os.fdopen(read_fd, "rb", buffering=0))
            startup_out = pipes.enter_context(os.fdopen(write_fd, "wb", buffering=0))
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        try:
            pid = os.fork()
        except OSError:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            raise
        if pid == 0:
            try:
                os.dup2(log.fileno(), 1)
                os.dup2(log.fileno(), 2)
                os.setsid()
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
                timings_in.close()
                if env_cfg:
                    startup_out.close()
                    if not startup_in.read(1):
                        os._exit(127)
                    startup_in.close()
                    os.sched_setaffinity(0, {env_cfg["benchmark_cpu"]})
                os.chdir(case)
                usage = resource.getrusage(resource.RUSAGE_SELF)
                timings_out.write(CPU_SAMPLE.pack(usage.ru_utime, usage.ru_stime))
                timings_out.close()
                os.execve(argv[0], argv, env)
            except BaseException:
                traceback.print_exc()
            finally:
                os._exit(127)
        active[pid] = (directory, record, b"")
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        timings_out.close()
        if env_cfg:
            startup_in.close()
            write_setting(CGROUP / "cgroup.procs", pid)
            startup_out.write(b"1")
            startup_out.close()
        active[pid] = (directory, record, timings_in.read(CPU_SAMPLE.size))

def collect_result(yosys, directory, record, sample, status, usage, timing):
    # 从退出状态、资源用量和 Yosys 产物提取单次测量结果。
    log = directory / "yosys.log"
    if code := os.waitstatus_to_exitcode(status):
        print(f"综合失败 {record['case']}，日志 {log}", file=sys.stderr)
        raise subprocess.CalledProcessError(code, [str(yosys), "-Q", "-s", str(directory / "synth.ys")])
    user_before, system_before = CPU_SAMPLE.unpack(sample)
    user = (round(usage.ru_utime * 1_000_000) - round(user_before * 1_000_000)) / 1_000_000
    system = (round(usage.ru_stime * 1_000_000) - round(system_before * 1_000_000)) / 1_000_000
    with log.open(encoding="utf-8", errors="replace") as stream:
        match = next((match for line in stream if (match := FOOTER.match(line))), None)
    if not match:
        raise ValueError(f"Yosys 日志缺少时间或内存摘要 {log}")
    elapsed, _, _, memory = map(float, match.groups())
    cells = json.loads((directory / "stat.json").read_text("utf-8"))["design"]["num_cells_by_type"]
    return dict(record, lut4=int(cells.get("cycloneiv_lcell_comb", 0) + cells.get("$not", 0)),
                dff=int(cells.get("dffeas", 0)), cells_total=int(sum(cells.values())),
                runtime_s=round(user + system, 6) if timing == "rusage" else elapsed,
                rusage_user_s=user, rusage_system_s=system, log_time_s=elapsed, peak_memory_mb=memory)

def run_batch(cases, output, yosys, batch, config, stream):
    # 按并发上限调度当前批次并逐行保存测量数据。
    phase, number, version = batch
    pending, active = iter(cases.items()), {}
    with tempfile.TemporaryDirectory() if phase == "warmup" else nullcontext() as temporary:
        root = Path(temporary) if temporary else output / "formal" / str(number) / version
        try:
            while True:
                for case_id, (case, sources) in islice(pending, config["jobs"] - len(active)):
                    directory = root / case_id
                    script = directory / "synth.ys"
                    (directory / "tmp").mkdir(parents=True)
                    source_args = " ".join(f'"{case / name}"' for name in sources)
                    script.write_text(f"read_verilog -I. {source_args}\n"
                                      f"synth_intel -family cycloneiv -top {case.name}\n"
                                      f'tee -q -o "{directory / "stat.json"}" stat -json\n', "utf-8")
                    record = dict(phase=phase, round=number, version=version, case=case_id)
                    spawn_yosys(case, [str(yosys), "-Q", "-s", str(script)],
                                directory, record, active, config["environment"])
                if not active:
                    break
                pid, status, usage = os.wait4(-1, 0)
                directory, record, sample = active.pop(pid)
                try:
                    result = collect_result(yosys, directory, record, sample, status, usage, config["timing"])
                    print(json.dumps(result, ensure_ascii=False), file=stream)
                finally:
                    if temporary:
                        shutil.rmtree(directory)
                    else:
                        (directory / "synth.ys").unlink()
                        shutil.rmtree(directory / "tmp")
        finally:
            for pid in active:
                with suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
                with suppress(ProcessLookupError):
                    os.killpg(pid, signal.SIGKILL)
                with suppress(ChildProcessError):
                    os.wait4(pid, 0)

def terminate(_signum, _frame):
    # 将终止信号转换为退出并执行清理。
    raise SystemExit(143)

def project_path(path):
    # 优先在元数据中记录相对于仓库的路径。
    return path.relative_to(PROJECT_ROOT).as_posix() if path.is_relative_to(PROJECT_ROOT) else str(path)

def main():
    # 验证实验配置并依次执行预热和正式测量。
    output, yosys, config, environment = parse_settings(argparse.ArgumentParser(description="运行 Yosys 综合实验"))
    output.mkdir(parents=True, exist_ok=True)
    for name in ("metadata.json", "measurements.jsonl"):
        if (path := output / name).exists():
            raise FileExistsError(path)
    if yosys["build_optimized"]:
        build_yosys("optimized")
    versions = {}
    for version in VERSIONS:
        path = yosys[version]
        if not path.is_file() or not os.access(path, os.X_OK):
            raise PermissionError(f"Yosys 路径需要指向可执行文件 {path}")
        versions[f"{version}_path"] = project_path(path)
        versions[f"{version}_version"] = subprocess.check_output([path, "-V"], text=True).strip()
    cases = discover_cases(config["cases"])
    config.update(cases=[project_path(p) for p in config["cases"]], case_ids=list(cases),
                  environment=environment if config["env_control"] else None)
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    with (output / "metadata.json").open("x", encoding="utf-8") as stream:
        json.dump(dict(created_at=created_at, yosys=versions, config=config), stream, ensure_ascii=False, indent=2)
    signal.signal(signal.SIGTERM, terminate)
    context = measurement_environment(environment) if config["env_control"] else nullcontext()
    with (output / "measurements.jsonl").open("x", encoding="utf-8", buffering=1) as stream, context:
        for phase in ("warmup", "formal"):
            rounds = config[f"{phase}_rounds"]
            for number in range(1, rounds + 1):
                for version in VERSIONS if number % 2 else reversed(VERSIONS):
                    start = time.monotonic()
                    run_batch(cases, output, yosys[version], (phase, number, version), config, stream)
                    print(f"[{phase} {number}/{rounds}] {version:<9} ({len(cases)} cases) "
                          f"... done in {time.monotonic() - start:.1f}s", file=sys.stderr)

if __name__ == "__main__":
    main()
