from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from explog.errors import ScriptError
from explog.scripts import run_command


def _parse_state_path(raw_output: str) -> Path:
    # 从捕获命令的单行标准输出读取状态文件路径。
    lines = raw_output.splitlines()
    if len(lines) > 1:
        raise ScriptError(
            f"repository state command printed {len(lines)} lines on stdout, "
            f"exactly one path is required: {raw_output!r}"
        )
    if not lines or not lines[0].strip():
        raise ScriptError(
            f"repository state command printed no path on stdout: {raw_output!r}"
        )
    return Path(lines[0].strip())


def capture_repository_state(
    command: Sequence[str], data_dir: Path, git_root: Path
) -> str:
    # 调用状态捕获工具并校验输出文件的位置。
    resolved_data = data_dir.resolve()
    output = run_command(
        [*command, "--output", str(resolved_data)], git_root, capture_stdout=True
    )
    reported = _parse_state_path(output.stdout)
    candidate = git_root / reported
    resolved = candidate.resolve()

    if not resolved.is_file():
        raise ScriptError(
            f"repository state file is missing or not a regular file: {resolved}"
        )
    if not resolved.is_relative_to(resolved_data):
        raise ScriptError(
            f"repository state file must be inside the run data directory: {resolved}"
        )
    return resolved.relative_to(git_root).as_posix()
