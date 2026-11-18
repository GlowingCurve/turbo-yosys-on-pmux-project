import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = PROJECT_ROOT / ".work/test_scripts"
CASE_IDS = ("official_case/test1", "official_case/test2")


class BenchmarkScriptsTest(unittest.TestCase):
    def setUp(self):
        # 为每个测试创建独立的实验目录。
        WORK_ROOT.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=WORK_ROOT)
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)

    def command(self, script, *arguments, check=True):
        # 在仓库根目录运行脚本并捕获输出。
        return subprocess.run(
            [sys.executable, PROJECT_ROOT / "scripts" / script, *arguments],
            cwd=PROJECT_ROOT, text=True, capture_output=True, check=check,
        )

    def run_benchmark(self, raw, *arguments):
        # 使用两个小用例和已构建的 Yosys 运行实验。
        result = self.command(
            "run_benchmark.py", *(f"testcase/{name}" for name in CASE_IDS),
            "--no-build", "--no-env-control", "--output", raw, *arguments,
        )
        self.assertEqual(result.stdout, "")
        return [json.loads(line) for line in (raw / "measurements.jsonl").read_text().splitlines()]

    def test_rusage_alternating_and_analyze(self):
        # 检查用例编号、轮次顺序、原始产物和变化率。
        raw, processed = self.work / "raw1", self.work / "proc1"
        records = self.run_benchmark(raw, "--warmup", "1", "--rounds", "2", "--timing", "rusage", "--jobs", "1")
        metadata = json.loads((raw / "metadata.json").read_text())
        self.assertEqual(metadata["config"]["case_ids"], list(CASE_IDS))
        self.assertIsNone(metadata["config"]["environment"])
        batches = [("warmup", 1), ("formal", 1), ("formal", 2)]
        expected = [(phase, number, version, case) for phase, number in batches
                    for version in (("original", "optimized") if number == 1 else ("optimized", "original"))
                    for case in CASE_IDS]
        self.assertEqual(len(records), 12)
        self.assertEqual([(r["phase"], r["round"], r["version"], r["case"]) for r in records], expected)
        self.assertFalse((raw / "warmup").exists())
        for phase, number, version, case in expected:
            if phase == "formal":
                directory = raw / phase / str(number) / version / case
                self.assertEqual({p.name for p in directory.iterdir()}, {"stat.json", "yosys.log"})
        for row in records:
            self.assertEqual(row["runtime_s"], round(row["rusage_user_s"] + row["rusage_system_s"], 6))
        analysis = self.command("analyze_benchmark.py", "--input", raw, "--output", processed)
        self.assertEqual(analysis.stdout, "")
        self.assertIn("Benchmark Summary", analysis.stderr)
        results = json.loads((processed / "results.json").read_text())
        self.assertIn("## Per-Case Results", (processed / "report.md").read_text())
        lut4 = results["cases"][CASE_IDS[0]]["lut4"]
        self.assertEqual(lut4["change_pct"], (lut4["optimized"] - lut4["original"]) / lut4["original"] * 100.0)
        self.assertLess(lut4["change_pct"], 0)

    def test_yosys_log_parallel_and_cli_views(self):
        # 检查双进程日志计时以及历史实验的查看和比较。
        raw, processed = self.work / "raw2", self.work / "proc2"
        records = self.run_benchmark(raw, "--warmup", "0", "--rounds", "1", "--timing", "yosys_log", "--jobs", "2")
        self.assertEqual(len(records), 4)
        for row in records:
            self.assertEqual(row["runtime_s"], row["log_time_s"])
        self.command("analyze_benchmark.py", raw, "--output", processed)
        config = self.work / "explog.toml"
        config.write_text('log = "experiments.jsonl"\ndata_root = "experiment-data"\n', encoding="utf-8")
        entries = []
        for i in ("1", "2"):
            target = self.work / "experiment-data" / i / "processed"
            shutil.copytree(processed, target)
            entries.append(dict(id=i, name=f"test-{i}", parent_id=None,
                                timestamp="2026-11-18T00:00:00Z", message=""))
        (self.work / "experiments.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in entries), encoding="utf-8",
        )
        inspected = self.command("analyze_benchmark.py", "--exp", "1", "--detail", "--config", config)
        self.assertIn("Experiment #1: test-1", inspected.stdout)
        self.assertIn("LUT4 (Orig -> Opt)", inspected.stdout)
        self.assertIn(CASE_IDS[0], inspected.stdout)
        compared = self.command("analyze_benchmark.py", "--compare", "1", "2", "--config", config)
        self.assertIn("Comparison: #1 (test-1) -> #2 (test-2)", compared.stdout)
        self.assertIn("#2 vs #1", compared.stdout)
        self.assertIn("official_case", compared.stdout)

    def test_env_control_jobs_conflict(self):
        # 确认单核隔离与多进程的冲突在执行前报错。
        output = self.work / "conflict"
        result = self.command("run_benchmark.py", "--env-control", "--jobs", "2", "--output", output, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("开启 env_control 时必须设置 --jobs 1，避免隔离单核争抢", result.stderr)
        self.assertFalse(output.exists())
