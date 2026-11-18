from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from explog.errors import LogError
from explog.log import read_nodes
from explog.model import ExperimentNode


def _utc_timestamp(node: ExperimentNode) -> datetime:
    # 将节点时间转换为带时区的 UTC 时间。
    timestamp = datetime.fromisoformat(node.timestamp)
    if timestamp.utcoffset() is None:
        raise LogError(f"log record {node.id} has timestamp without timezone")
    return timestamp.astimezone(UTC)


def list_nodes(path: Path) -> list[ExperimentNode]:
    # 读取节点并按照 UTC 时间稳定排序。
    nodes = read_nodes(path, missing_ok=False)
    return sorted(nodes, key=_utc_timestamp)


def _escape_message(message: str) -> str:
    # 转义文本中的换行和制表符以保持单行显示。
    return message.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")


def format_nodes(nodes: list[ExperimentNode]) -> str:
    # 将节点格式化为包含名称的实验列表。
    if not nodes:
        return ""

    rows = [
        (
            node.timestamp,
            node.id,
            "-" if node.parent_id is None else node.parent_id,
            _escape_message(node.name),
            _escape_message(node.message),
        )
        for node in nodes
    ]
    headers = ("TIMESTAMP", "ID", "PARENT", "NAME", "MESSAGE")
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(4)
    ]

    def format_row(row: tuple[str, str, str, str, str]) -> str:
        # 按照各列宽度格式化一条记录。
        return "  ".join(
            [row[index].ljust(widths[index]) for index in range(4)] + [row[4]]
        )

    return "\n".join((format_row(headers), *(format_row(row) for row in rows)))
