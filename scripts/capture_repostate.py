from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path
from typing import BinaryIO

_GIT = ("git", "--no-optional-locks")
_STATUS = (
    "status",
    "--porcelain=v1",
    "--untracked-files=all",
    "--ignore-submodules=none",
)
_DIFF = (
    "diff",
    "--no-color",
    "--no-ext-diff",
    "--no-textconv",
    "--binary",
    "--full-index",
    "--ignore-submodules=none",
    "HEAD",
    "--",
    ".",
)


def write_section(
    stream: BinaryIO, root: Path, title: str, arguments: tuple[str, ...]
) -> None:
    stream.write(f"\n=== {title} ===\n".encode())
    stream.flush()
    subprocess.run([*_GIT, *arguments], cwd=root, stdout=stream, check=True)


def capture(output: Path, root: Path) -> Path:
    state_file = output / "repository-state.txt"
    submodule_command = " && ".join(
        shlex.join([*_GIT, *arguments])
        for arguments in (("rev-parse", "HEAD"), _STATUS, _DIFF)
    )
    with state_file.open("xb") as stream:
        write_section(stream, root, "Superproject HEAD", ("rev-parse", "HEAD"))
        write_section(
            stream, root, "Submodule revisions", ("submodule", "status", "--recursive")
        )
        write_section(stream, root, "Superproject status", _STATUS)
        write_section(stream, root, "Superproject diff against HEAD", _DIFF)
        write_section(
            stream,
            root,
            "Submodule HEAD, status and diff against HEAD",
            ("submodule", "foreach", "--recursive", submodule_command),
        )
    return state_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture Git state of the superproject and recursive submodules."
    )
    parser.add_argument("--output", required=True, type=Path, help="Run data directory")
    arguments = parser.parse_args()
    output = arguments.output.resolve(strict=True)
    if not output.is_dir():
        parser.error(f"output must be a directory: {output}")
    if len(str(output).splitlines()) != 1:
        parser.error("output path must fit on one stdout line")

    result = subprocess.run(
        [*_GIT, "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        check=True,
        text=True,
        encoding="utf-8",
    )
    root = Path(result.stdout.rstrip("\n")).resolve(strict=True)
    output.relative_to(root)
    state_file = capture(output, root)
    print(state_file)


if __name__ == "__main__":
    main()
