import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_yosys(target: str = "optimized") -> None:
    # 在指定的 Yosys 目录中执行增量构建。
    targets = ("original", "optimized") if target == "both" else (target,)
    for version in targets:
        subprocess.run(
            ["cmake", "--build", "build/"],
            cwd=PROJECT_ROOT / f"yosys-{version}",
            stdout=sys.stderr, check=True,
        )


def main():
    # 解析命令行并构建选定版本。
    parser = argparse.ArgumentParser(description="增量构建 Yosys")
    parser.add_argument("--target", choices=("optimized", "original", "both"), default="optimized")
    build_yosys(parser.parse_args().target)


if __name__ == "__main__":
    main()
