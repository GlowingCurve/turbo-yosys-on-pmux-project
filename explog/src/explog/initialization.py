from __future__ import annotations

import os
import platform
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

from explog.config import load_config
from explog.directories import resolve_data_root
from explog.errors import ConfigError, DirectoryError, ScriptError
from explog.git import find_git_root
from explog.log import read_log

_EMPTY_CONFIG_TEMPLATE = """\
log = ""
data_root = ""
repository_state_command = []
experiment_scripts = []
data_processing_scripts = []
"""


@dataclass(frozen=True)
class InitializationResult:
    python_version: str
    git_root: Path
    config_path: Path
    repository_state_command: str
    experiment_commands: int
    processing_commands: int
    log_path: Path
    log_created: bool
    existing_records: int
    data_root: Path
    data_root_created: bool


def _create_empty_config(resolved_config: Path) -> None:
    # 创建空配置模板并提示用户填写必需字段。
    with resolved_config.open("x", encoding="utf-8") as config_file:
        config_file.write(_EMPTY_CONFIG_TEMPLATE)
    raise ConfigError(
        f"created empty config template: {resolved_config}; "
        "fill in the values and re-run init"
    )


def _check_executable(executable: str, git_root: Path) -> None:
    # 校验命令的可执行程序可以从仓库目录调用。
    path = Path(executable)
    has_separator = os.sep in executable or (
        os.altsep is not None and os.altsep in executable
    )
    if path.is_absolute() or has_separator:
        candidate = git_root / path
        if not (candidate.is_file() and os.access(candidate, os.X_OK)):
            raise ScriptError(f"script executable is not available: {executable}")
        return

    if shutil.which(executable) is None:
        raise ScriptError(f"script executable is not available on PATH: {executable}")


def initialize_environment(
    *,
    config_path: Path,
    log_path: Path | None = None,
    cwd: Path | None = None,
) -> InitializationResult:
    # 校验环境并创建日志和数据根目录。
    working_directory = (cwd or Path.cwd()).resolve()
    resolved_config = (working_directory / config_path).resolve()
    if not resolved_config.exists():
        _create_empty_config(resolved_config)
    git_root = find_git_root(working_directory)
    config = load_config(resolved_config)
    resolved_log = working_directory / config.log_path(resolved_config, log_path)
    for command in (
        config.repository_state_command,
        *config.experiment_scripts,
        *config.data_processing_scripts,
    ):
        _check_executable(command[0], git_root)
    data_root = resolve_data_root(git_root, config.data_root)
    if data_root.is_relative_to(resolved_log.resolve()):
        raise DirectoryError(
            f"data_root conflicts with log path: {data_root} and {resolved_log}"
        )

    records = read_log(resolved_log)

    data_root_created = not data_root.exists()
    log_created = not resolved_log.exists()
    resolved_log.parent.mkdir(parents=True, exist_ok=True)
    data_root.mkdir(parents=True, exist_ok=True)
    if log_created:
        with resolved_log.open("x", encoding="utf-8"):
            pass

    return InitializationResult(
        python_version=platform.python_version(),
        git_root=git_root,
        config_path=resolved_config,
        repository_state_command=shlex.join(config.repository_state_command),
        experiment_commands=len(config.experiment_scripts),
        processing_commands=len(config.data_processing_scripts),
        log_path=resolved_log,
        log_created=log_created,
        existing_records=len(records),
        data_root=data_root,
        data_root_created=data_root_created,
    )
