from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from explog.errors import ConfigError


@dataclass(frozen=True)
class Config:
    log: Path
    data_root: Path
    repository_state_command: tuple[str, ...]
    experiment_scripts: tuple[tuple[str, ...], ...]
    data_processing_scripts: tuple[tuple[str, ...], ...]

    def log_path(self, config_path: Path, override: Path | None = None) -> Path:
        # 根据配置文件位置和显式参数确定日志路径。
        return override if override is not None else config_path.parent / self.log


_CONFIG_KEYS = {
    "log",
    "data_root",
    "repository_state_command",
    "experiment_scripts",
    "data_processing_scripts",
}


def _parse_command(value: object, key: str) -> tuple[str, ...]:
    # 校验单条命令的 argv 参数。
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{key} must be a non-empty argv array")
    if not all(isinstance(argument, str) for argument in value):
        raise ConfigError(f"{key} arguments must all be strings")
    if not value[0]:
        raise ConfigError(f"{key} executable must not be empty")
    return tuple(value)


def _parse_commands(value: object, key: str) -> tuple[tuple[str, ...], ...]:
    # 校验命令列表并保留执行顺序。
    if not isinstance(value, list):
        raise ConfigError(f"{key} must be an array of argv arrays")

    return tuple(
        _parse_command(command, f"{key}[{index}]")
        for index, command in enumerate(value)
    )


def _parse_path(value: object, key: str) -> Path:
    # 校验路径字段并创建 Path 对象。
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{key} must be a non-empty string")
    if "\x00" in value:
        raise ConfigError(f"{key} must not contain a NUL character")
    return Path(value)


def load_config(path: Path) -> Config:
    # 读取 TOML 配置并校验全部字段。
    with path.open("rb") as config_file:
        try:
            raw = tomllib.load(config_file)
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"invalid TOML in {path}: {error}") from error

    unknown = set(raw) - _CONFIG_KEYS
    missing = _CONFIG_KEYS - set(raw)
    if missing:
        raise ConfigError(f"missing config key(s): {', '.join(sorted(missing))}")
    if unknown:
        raise ConfigError(f"unknown config key(s): {', '.join(sorted(unknown))}")

    repository_state_command = _parse_command(
        raw["repository_state_command"], "repository_state_command"
    )
    return Config(
        log=_parse_path(raw["log"], "log"),
        data_root=_parse_path(raw["data_root"], "data_root"),
        repository_state_command=repository_state_command,
        experiment_scripts=_parse_commands(
            raw["experiment_scripts"], "experiment_scripts"
        ),
        data_processing_scripts=_parse_commands(
            raw["data_processing_scripts"], "data_processing_scripts"
        ),
    )
