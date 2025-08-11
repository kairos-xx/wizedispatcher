#!/usr/bin/env python3
"""Run all Python demo files in the demo folder sequentially.

This script scans the "demo" directory for files ending with ".py" and
executes each one in a subprocess, printing a header before the run.

The demo scripts are executed in their own processes, so side effects or
module imports in one will not interfere with others.
"""

from pathlib import Path
from subprocess import CalledProcessError, run
from sys import executable, exit, stderr
from typing import List


def run_all_demos() -> None:
    """Find and run all Python demo scripts sequentially."""
    demo_dir: Path = Path(__file__).parent

    if not demo_dir.exists():
        print(f"Demo folder not found: {demo_dir}", file=stderr)
        exit(1)

    demo_files: List[Path] = sorted(
        [
            f
            for f in demo_dir.glob("*.py")
            if f.is_file() and Path(f) != Path(__file__)
        ],
        key=lambda x: x.name.lower(),
    )

    if not demo_files:
        print(f"No Python files found in: {demo_dir}", file=stderr)
        exit(1)

    for file_path in demo_files:
        print("\n" + "=" * 79)
        print(f"Running demo: {file_path.name}")
        print("=" * 79 + "\n")
        try:
            run(
                [executable, str(file_path)],
                check=True,
            )
        except CalledProcessError as e:
            print(
                f"Demo {file_path.name} failed with exit code {e.returncode}"
            )
        except Exception as exc:
            print(f"Error running {file_path.name}: {exc}")


if __name__ == "__main__":
    run_all_demos()
