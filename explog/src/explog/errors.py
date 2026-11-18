class ExplogError(Exception):
    """Base class for expected explog failures."""


class ConfigError(ExplogError):
    """Raised when the configuration cannot be loaded or validated."""


class LogError(ExplogError):
    """Raised when the JSONL log is invalid or cannot be used."""


class GitError(ExplogError):
    """定位 Git 仓库根目录失败时抛出。"""


class DirectoryError(ExplogError):
    """Raised when the run directories are invalid or cannot be created."""


class ScriptError(ExplogError):
    """捕获命令、实验脚本或处理脚本失败时抛出。"""
