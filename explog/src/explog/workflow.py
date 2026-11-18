from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from explog.config import load_config
from explog.directories import create_run_directory, resolve_data_root
from explog.errors import LogError
from explog.git import find_git_root
from explog.log import append_record, read_log
from explog.model import ExperimentNode, validate_name
from explog.scripts import run_command
from explog.state import capture_repository_state


def generate_id(existing_ids: Iterable[str]) -> str:
    # 根据已有记录和数据目录生成下一个实验序号。
    ids = set(existing_ids)
    sequence = max(
        (int(value) for value in ids if value.isascii() and value.isdecimal()),
        default=0,
    )
    return str(max(sequence, len(ids)) + 1)


def run_experiment(
    *,
    config_path: Path,
    name: str,
    log_path: Path | None = None,
    message: str = "",
    parent_id: str | None = None,
    cwd: Path | None = None,
) -> ExperimentNode:
    # 依次调用捕获、实验和处理工具并记录成功结果。
    validate_name(name)
    if not isinstance(message, str):
        raise LogError("message must be a string")
    working_directory = (cwd or Path.cwd()).resolve()
    config_path = (working_directory / config_path).resolve()
    config = load_config(config_path)
    log_path = working_directory / config.log_path(config_path, log_path)
    git_root = find_git_root(working_directory)
    existing_ids = {record["id"] for record in read_log(log_path)}
    if parent_id is not None and parent_id not in existing_ids:
        raise LogError(f"parent id does not exist in log: {parent_id}")
    if not log_path.parent.is_dir():
        raise LogError(f"log parent directory does not exist: {log_path.parent}")

    data_root = resolve_data_root(git_root, config.data_root)
    directory_ids = (
        {path.name for path in data_root.iterdir()} if data_root.exists() else set()
    )
    chosen_id = generate_id(existing_ids | directory_ids)
    data = create_run_directory(git_root, config.data_root, chosen_id)
    raw, processed = str(data / "raw"), str(data / "processed")
    relative_state = capture_repository_state(
        config.repository_state_command, data, git_root
    )
    for command in config.experiment_scripts:
        run_command([*command, "--output", raw], git_root)
    for command in config.data_processing_scripts:
        run_command([*command, "--input", raw, "--output", processed], git_root)

    node = ExperimentNode(
        id=chosen_id,
        name=name,
        parent_id=parent_id,
        timestamp=datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        message=message,
        repository_state_path=relative_state,
        data_dir=data.relative_to(git_root).as_posix(),
    )
    append_record(log_path, asdict(node))
    return node
