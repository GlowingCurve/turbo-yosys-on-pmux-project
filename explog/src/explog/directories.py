from pathlib import Path

from explog.errors import DirectoryError


def validate_id(experiment_id: str) -> None:
    # 校验实验 ID 可以安全用作单层目录名称。
    if (
        not experiment_id
        or experiment_id in {".", ".."}
        or "/" in experiment_id
        or "\\" in experiment_id
        or any(
            ord(character) < 32 or ord(character) == 127 for character in experiment_id
        )
    ):
        raise DirectoryError(
            "id must be a non-empty, safe, single-directory name without separators"
        )


def resolve_data_root(git_root: Path, configured_data_root: Path) -> Path:
    # 解析数据根目录并校验其位于 Git 仓库内部。
    data_root = (git_root / configured_data_root).resolve()
    if not data_root.is_relative_to(git_root):
        raise DirectoryError(f"data_root must be inside Git root: {data_root}")
    if data_root.exists() and not data_root.is_dir():
        raise DirectoryError(f"data_root is not a directory: {data_root}")
    return data_root


def create_run_directory(
    git_root: Path, configured_data_root: Path, experiment_id: str
) -> Path:
    # 创建本次实验及其原始数据和处理结果目录。
    data_root = resolve_data_root(git_root, configured_data_root)
    data = data_root / experiment_id
    if data.exists() or data.is_symlink():
        raise DirectoryError(f"data directory already exists: {data}")
    data.mkdir(parents=True)
    (data / "raw").mkdir()
    (data / "processed").mkdir()
    return data
