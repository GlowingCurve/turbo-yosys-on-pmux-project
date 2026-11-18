from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from explog.config import load_config
from explog.initialization import InitializationResult, initialize_environment
from explog.listing import format_nodes, list_nodes
from explog.workflow import run_experiment


def build_parser() -> argparse.ArgumentParser:
    # 定义子命令及其输入参数。
    parser = argparse.ArgumentParser(
        prog="explog",
        description="Run and inspect experiments recorded in JSONL.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text, handler in (
        ("run", "run scripts and record an experiment", _run_experiment),
        ("init", "check and initialize an explog environment", _run_init),
        ("list", "list experiments in chronological order", _run_list),
    ):
        command = subparsers.add_parser(name, help=help_text, description=help_text)
        command.add_argument(
            "--config",
            type=Path,
            default=Path("explog.toml"),
            required=name == "run",
            help="TOML config path"
            if name == "run"
            else "TOML config (default: explog.toml)",
        )
        command.add_argument(
            "--log", type=Path, help="JSONL log path (default: config log field)"
        )
        if name == "run":
            command.add_argument("--name", required=True, help="experiment name")
            command.add_argument("--message", default="", help="experiment message")
            command.add_argument("--parent-id", metavar="ID", help="existing parent ID")
        command.set_defaults(handler=handler)
    return parser


def _print_initialization(result: InitializationResult) -> None:
    # 输出初始化检查结果。
    print(f"Python: {result.python_version} [OK]")
    print(f"Git repository: {result.git_root} [OK]")
    print(f"Config: {result.config_path} [OK]")
    print(f"Repository state command: {result.repository_state_command} [OK]")
    print(f"Experiment commands: {result.experiment_commands} [OK]")
    print(f"Processing commands: {result.processing_commands} [OK]")
    log_status = "created" if result.log_created else "already exists, valid"
    print(f"Log: {result.log_path} [{log_status}; {result.existing_records} records]")
    data_status = "created" if result.data_root_created else "already exists"
    print(f"Data root: {result.data_root} [{data_status}]")
    print("explog environment is ready")


def _run_init(arguments: argparse.Namespace) -> int:
    # 根据命令参数初始化实验环境。
    result = initialize_environment(
        config_path=arguments.config,
        log_path=arguments.log,
    )
    _print_initialization(result)
    return 0


def _run_experiment(arguments: argparse.Namespace) -> int:
    # 执行实验并将生成的 ID 输出到 stdout。
    node = run_experiment(
        config_path=arguments.config,
        log_path=arguments.log,
        name=arguments.name,
        message=arguments.message,
        parent_id=arguments.parent_id,
    )
    print(node.id)
    return 0


def _run_list(arguments: argparse.Namespace) -> int:
    # 读取指定日志并输出实验列表。
    log_path = arguments.log
    if log_path is None:
        config_path = arguments.config.resolve()
        config = load_config(config_path)
        log_path = config.log_path(config_path)
    output = format_nodes(list_nodes(log_path))
    if output:
        print(output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    # 解析参数并调用对应子命令。
    arguments = build_parser().parse_args(argv)
    return arguments.handler(arguments)
