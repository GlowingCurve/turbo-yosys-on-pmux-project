from __future__ import annotations

import subprocess
from pathlib import Path

from explog.errors import GitError


def find_git_root(cwd: Path) -> Path:
    # 调用 Git 查找当前目录所属的仓库根目录。
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    root = result.stdout.rstrip("\n")
    if not root:
        raise GitError("git rev-parse returned an empty repository root")
    return Path(root).resolve()
