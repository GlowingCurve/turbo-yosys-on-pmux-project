import argparse
import json
import sys
import tomllib
from itertools import product
from pathlib import Path
from statistics import mean

VERSIONS = ("original", "optimized")
METRICS = ("lut4", "runtime_s", "peak_memory_mb")
LABELS = ("LUT4 (cells, sum)", "Time (s, sum)", "Peak Mem (MB, avg)")
SORT_KEYS = dict(zip(("lut4", "time", "mem"), METRICS))
RULE = "-" * 92

def change_pct(original, optimized):
    # 计算两个数值之间的变化率。
    return (optimized - original) / original * 100.0 if original else None

def measures(original, optimized, metric, *, aggregate=False):
    # 生成单用例或汇总指标。
    suffix = "_mean" if aggregate and metric == "peak_memory_mb" else ""
    values = {f"original{suffix}": original, f"optimized{suffix}": optimized,
              f"delta{suffix}": optimized - original}
    if metric != "dff":
        values["total_change_pct" if aggregate else "change_pct"] = change_pct(original, optimized)
    return values

def summarize(cases):
    # 计算全局和各分组的总量变化率与用例平均变化率。
    groups = {}
    for row in cases.values():
        groups.setdefault(row["group"], []).append(row)
    summaries = []
    for rows in (cases.values(), *(groups[name] for name in sorted(groups))):
        summary = {"case_count": len(rows)}
        for metric in METRICS:
            combine = mean if metric == "peak_memory_mb" else sum
            original, optimized = (combine(row[metric][v] for row in rows) for v in VERSIONS)
            changes = [row[metric]["change_pct"] for row in rows if row[metric]["change_pct"] is not None]
            summary[metric] = measures(original, optimized, metric, aggregate=True)
            summary[metric]["mean_change_pct"] = mean(changes) if changes else None
        summaries.append(summary)
    return summaries[0], dict(zip(sorted(groups), summaries[1:]))

def analyze(raw):
    # 校验正式测量的完整性和单元统计一致性并计算结果。
    metadata = json.loads((raw / "metadata.json").read_text("utf-8"))
    config = metadata["config"]
    rounds = range(1, config["formal_rounds"] + 1)
    case_ids = sorted(config["case_ids"])
    if not rounds or not case_ids or len(set(case_ids)) != len(case_ids):
        raise ValueError("元数据中的正式轮次或用例编号无效")
    missing = set(product(rounds, VERSIONS, case_ids))
    records = {}
    with (raw / "measurements.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["phase"] == "formal":
                key = row["round"], row["version"], row["case"]
                if key not in missing:
                    raise ValueError(f"出现重复或未预期的正式测量 {key}")
                missing.remove(key)
                records[key] = row
    if missing:
        raise ValueError(f"缺少正式测量 {min(missing)}（共 {len(missing)} 条）")
    cases = {}
    for case in case_ids:
        versions = {}
        for version in VERSIONS:
            rows = []
            for number in rounds:
                path = raw / "formal" / str(number) / version / case / "stat.json"
                cells = json.loads(path.read_text("utf-8"))["design"]["num_cells_by_type"]
                if number == 1:
                    first_cells = cells
                elif cells != first_cells:
                    raise ValueError(f"综合单元统计在第 {number} 轮发生变化 {case} ({version})")
                rows.append(records[number, version, case])
            versions[version] = {metric: rows[0][metric] if metric in ("lut4", "dff")
                                 else mean(row[metric] for row in rows) for metric in (*METRICS, "dff")}
        case_result = {"group": case.split("/", 1)[0] if "/" in case else "default"}
        for metric in ("lut4", "dff", "runtime_s", "peak_memory_mb"):
            case_result[metric] = measures(*(versions[v][metric] for v in VERSIONS), metric)
        cases[case] = case_result
    overall, groups = summarize(cases)
    return dict(metadata=metadata, overall=overall, groups=groups, cases=cases)

def number(value, metric, *, signed=False, detail=False):
    # 格式化表格中的单元数、时间和内存。
    spec = {"lut4": ",", "runtime_s": ".4f" if detail else ".3f", "peak_memory_mb": ".2f"}[metric]
    return format(value, ("+" if signed else "") + spec)

def pct(value):
    # 格式化变化率或缺省标记。
    return "N/A" if value is None else f"{value:+.2f}%"

def summary_rows(summary):
    # 生成汇总表的数值行。
    for metric, label in zip(METRICS, LABELS):
        values = summary[metric]
        suffix = "_mean" if metric == "peak_memory_mb" else ""
        yield (label, *(number(values[key + suffix], metric, signed=key == "delta")
                        for key in ("original", "optimized", "delta")),
               pct(values["total_change_pct"]), pct(values["mean_change_pct"]))

def group_rows(groups):
    # 生成分组表的总量变化率和用例平均变化率。
    for name, summary in groups.items():
        yield (name, str(summary["case_count"]),
               *(f"{pct(summary[m]['total_change_pct']):>7} / {pct(summary[m]['mean_change_pct']):>7}"
                 for m in METRICS))

def detail_rows(cases):
    # 生成用例明细表的数值行。
    for name, case in cases:
        row = [name]
        for metric in METRICS:
            values = case[metric]
            original, optimized = (number(values[v], metric, detail=True) for v in VERSIONS)
            row.extend((f"{original} -> {optimized}", pct(values["change_pct"])))
        yield row

def ascii_table(header, rows, widths):
    # 用固定列宽打印纯 ASCII 表格。
    def line(values):
        # 保留列间距并转义非 ASCII 字符。
        fields = [value.encode("ascii", "backslashreplace").decode("ascii") for value in values]
        columns = [f"{value:>{width}}" for value, width in zip(fields[1:], widths[1:])]
        return f"{fields[0]:<{widths[0] - 1}} " + "".join(columns)
    yield line(header)
    yield "-" * sum(widths)
    yield from map(line, rows)

SUMMARY_COLUMNS = ("Original", "Optimized", "Delta", "Total %", "Mean %")
GROUP_COLUMNS = ("Group", "Cases", "LUT4 (Tot / Mean)", "Time (Tot / Mean)", "Mem (Tot / Mean)")
DETAIL_COLUMNS = ("Case", "LUT4 (Orig -> Opt)", "LUT4 %", "Time s (Orig -> Opt)", "Time %",
                  "Mem MB (Orig -> Opt)", "Mem %")

def configuration(result):
    # 读取报表需要显示的实验参数。
    cfg = result["metadata"]["config"]
    return (f"timing={cfg['timing']}", f"env_control={'on' if cfg['env_control'] else 'off'}",
            f"warmup={cfg['warmup_rounds']}, formal={cfg['formal_rounds']}",
            f"jobs={cfg['jobs']}", f"cases={result['overall']['case_count']}")

def show_summary(result, *, stream=sys.stdout):
    # 打印全局汇总和分组表。
    overall = result["overall"]
    print(f"Benchmark Summary  [{' | '.join(configuration(result))}]", RULE, sep="\n", file=stream)
    header = (f"Overall (N={overall['case_count']})", *SUMMARY_COLUMNS)
    print(*ascii_table(header, summary_rows(overall), (21, 10, 16, 16, 15, 14)), RULE, sep="\n", file=stream)
    print(*ascii_table(GROUP_COLUMNS, group_rows(result["groups"]), (18, 7, 23, 22, 22)), RULE, sep="\n", file=stream)

def show_detail(cases, *, compare=None):
    # 打印逐用例明细，并为较长的用例编号保留空间。
    headers = DETAIL_COLUMNS
    if compare:
        a, b = compare
        headers = tuple(value.replace("Orig -> Opt", f"#{a} Opt -> #{b} Opt") for value in headers)
    names_width = max((len(name.encode("ascii", "backslashreplace")) + 2 for name, _ in cases), default=0)
    minimums = (max(32, names_width), 23, 10, 22, 10, 22, 10)
    widths = tuple(max(width, len(header) + 2) for width, header in zip(minimums, headers))
    print(*ascii_table(headers, detail_rows(cases), widths), sep="\n")

def markdown_table(header, rows):
    # 生成 GitHub Flavored Markdown 表格。
    return "\n".join("| " + " | ".join(value.strip().replace("\\", "\\\\").replace("|", "\\|") for value in row) + " |"
                     for row in (header, ["---"] + ["---:"] * (len(header) - 1), *rows))

def write_report(output, result):
    # 写入分析结果和包含全部用例的 Markdown 报表。
    report = "\n\n".join(("# Benchmark Report\n\n" + "\n".join(f"- {item}" for item in configuration(result)),
                          "## Overall", markdown_table(("Metric", *SUMMARY_COLUMNS), summary_rows(result["overall"])),
                          "## By Group", markdown_table(GROUP_COLUMNS, group_rows(result["groups"])),
                          "## Per-Case Results", markdown_table(DETAIL_COLUMNS, detail_rows(result["cases"].items()))))
    with (output / "results.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
    with (output / "report.md").open("x", encoding="utf-8") as stream:
        stream.write(report + "\n")

def show_comparison(ids, records, results, *, detail):
    # 用共同用例比较两次实验的优化版。
    left, right = (result["cases"] for result in results)
    common = sorted(left.keys() & right.keys())
    if not common:
        raise ValueError("两次实验没有共同用例")
    cases = {}
    for name in common:
        cases[name] = {"group": left[name]["group"]}
        for metric in METRICS:
            cases[name][metric] = measures(left[name][metric]["optimized"], right[name][metric]["optimized"], metric)
    overall, groups = summarize(cases)
    a, b = ids
    name_a, name_b = (records.get(i, {}).get("name", "") for i in ids)
    print(f"Comparison: #{a} ({name_a}) -> #{b} ({name_b})   [Cases: {len(common)}]", RULE, sep="\n")
    header = ("Metric", f"#{a} Opt", f"#{b} Opt", "Delta", f"#{b} vs #{a}", f"(#{a}% -> #{b}% vs Orig)")
    original_a, original_b = (summarize({name: rows[name] for name in common})[0] for rows in (left, right))
    rows = []
    for metric, row in zip(METRICS, summary_rows(overall)):
        a_pct, b_pct = (pct(data[metric]["total_change_pct"]) for data in (original_a, original_b))
        rows.append((*row[:-1], f"({a_pct:>7} -> {b_pct:>7})"))
    print(*ascii_table(header, rows, (21, 10, 14, 13, 12, 22)), RULE, sep="\n")
    print(*ascii_table(GROUP_COLUMNS, group_rows(groups), (18, 7, 23, 22, 22)), RULE, sep="\n")
    if detail:
        show_detail(list(cases.items()), compare=ids)

def main():
    # 根据命令行参数处理、查看或比较实验数据。
    parser = argparse.ArgumentParser(description="分析 Yosys 综合实验")
    parser.add_argument("raw", type=Path, nargs="?")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--input", type=Path)
    mode.add_argument("--exp", metavar="ID")
    mode.add_argument("--compare", nargs=2, metavar=("ID_A", "ID_B"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--detail", action="store_true")
    parser.add_argument("--group")
    parser.add_argument("--sort", choices=("case", *SORT_KEYS))
    args = parser.parse_args()
    if not (args.exp or args.compare):
        if not args.output or bool(args.raw) == bool(args.input) or any((args.config, args.detail, args.group, args.sort)):
            parser.error("处理模式需要一个输入目录和 --output")
        args.output.mkdir(parents=True, exist_ok=True)
        for filename in ("results.json", "report.md"):
            if (path := args.output / filename).exists():
                raise FileExistsError(path)
        result = analyze(args.input or args.raw)
        write_report(args.output, result)
        show_summary(result, stream=sys.stderr)
        return
    if args.raw or args.output or (args.compare and (args.group or args.sort)):
        parser.error("当前模式不支持指定的参数")
    path = args.config or Path("explog.toml")
    config = tomllib.loads(path.read_text("utf-8"))
    log = path.parent / config["log"]
    records = {row["id"]: row for row in map(json.loads, log.read_text("utf-8").splitlines())} if log.is_file() else {}
    ids = args.compare or [args.exp]
    root = path.parent / config["data_root"]
    results = [json.loads((root / i / "processed/results.json").read_text("utf-8")) for i in ids]
    if args.compare:
        show_comparison(ids, records, results, detail=args.detail)
        return
    if row := records.get(args.exp):
        print(f"Experiment #{args.exp}: {row['name']}  "
              f"(parent={row.get('parent_id')}, time={row['timestamp']})  {row.get('message', '')}")
    result = results[0]
    show_summary(result)
    if args.detail or args.group or args.sort:
        cases = sorted((name, row) for name, row in result["cases"].items() if not args.group or row["group"] == args.group)
        if args.sort in SORT_KEYS:
            metric = SORT_KEYS[args.sort]
            cases.sort(key=lambda item: (item[1][metric]["change_pct"] is None, item[1][metric]["change_pct"]))
        show_detail(cases)


if __name__ == "__main__":
    main()
