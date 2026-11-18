from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from explog.errors import LogError
from explog.model import ExperimentNode


def read_log(path: Path, missing_ok: bool = True) -> list[dict[str, Any]]:
    # 逐行读取 JSONL 日志并校验记录 ID。
    if not path.exists():
        if path.is_symlink():
            raise LogError(f"log path is a broken symbolic link: {path}")
        if missing_ok:
            return []
        raise LogError(f"log file does not exist: {path}")
    if not path.is_file():
        raise LogError(f"log path is not a regular file: {path}")

    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with path.open(encoding="utf-8") as log_file:
        for line_number, line in enumerate(log_file, start=1):
            if not line.strip():
                raise LogError(f"blank line in {path} at line {line_number}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise LogError(
                    f"invalid JSON in {path} at line {line_number}: {error.msg}"
                ) from error
            if not isinstance(record, dict):
                raise LogError(
                    f"log record in {path} at line {line_number} is not an object"
                )
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id:
                raise LogError(
                    f"log record in {path} at line {line_number} has no valid id"
                )
            if record_id in seen_ids:
                raise LogError(f"duplicate id in existing log: {record_id}")
            seen_ids.add(record_id)
            records.append(record)
    return records


def _required_string(record: dict[str, Any], record_id: str, field: str) -> str:
    # 读取必填字符串字段并报告对应节点。
    if field not in record:
        raise LogError(f"log record {record_id} is missing required field: {field}")
    value = record[field]
    if not isinstance(value, str):
        raise LogError(f"log record {record_id} has non-string field: {field}")
    return value


def read_nodes(path: Path, missing_ok: bool = True) -> list[ExperimentNode]:
    # 校验日志字段并创建实验节点。
    nodes: list[ExperimentNode] = []
    for record in read_log(path, missing_ok=missing_ok):
        record_id = record["id"]
        if "parent_id" not in record:
            raise LogError(
                f"log record {record_id} is missing required field: parent_id"
            )
        parent_id = record["parent_id"]
        if parent_id is not None and not isinstance(parent_id, str):
            raise LogError(f"log record {record_id} has invalid field type: parent_id")
        nodes.append(
            ExperimentNode(
                id=record_id,
                name=_required_string(record, record_id, "name"),
                parent_id=parent_id,
                timestamp=_required_string(record, record_id, "timestamp"),
                message=_required_string(record, record_id, "message"),
                repository_state_path=_required_string(
                    record, record_id, "repository_state_path"
                ),
                data_dir=_required_string(record, record_id, "data_dir"),
            )
        )
    return nodes


def append_record(path: Path, record: Mapping[str, Any]) -> None:
    # 将一条记录追加为 UTF-8 JSONL 文本。
    serialized = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8", newline="") as log_file:
        log_file.write(f"{serialized}\n")
