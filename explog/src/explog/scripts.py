import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def run_command(
    command: Sequence[str], cwd: Path, *, capture_stdout: bool = False
) -> subprocess.CompletedProcess[str]:
    # 执行外部命令并按脚本协议传递标准输入输出。
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE if capture_stdout else sys.stderr,
        text=True,
        encoding="utf-8",
    )
