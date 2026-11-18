from __future__ import annotations

from dataclasses import dataclass

from explog.errors import LogError


def validate_name(name: str, record_id: str | None = None) -> None:
    # 校验用户指定的名称包含非空白字符。
    if not isinstance(name, str) or not name.strip():
        context = "" if record_id is None else f"log record {record_id}: "
        raise LogError(f"{context}name must be a non-empty string")


@dataclass(frozen=True)
class ExperimentNode:
    id: str
    name: str
    parent_id: str | None
    timestamp: str
    repository_state_path: str
    data_dir: str
    message: str = ""

    def __post_init__(self) -> None:
        # 在创建节点时校验必填名称。
        validate_name(self.name, self.id)
