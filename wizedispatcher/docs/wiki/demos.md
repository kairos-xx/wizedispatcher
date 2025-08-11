# Demos

The `demo` directory contains small programs that exercise the
features of WizeDispatcher. Each script can be run directly. To
run all demos sequentially, use the following helper script:

```python
#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys


def run_all_demos() -> None:
    """Find and run all Python demo scripts sequentially."""
    demo_dir: Path = Path(__file__).parent / "demo"
    for file in sorted(demo_dir.glob("*.py")):
        print(f"== Running {file.name} ==")
        subprocess.run([sys.executable, str(file)], check=True)


if __name__ == "__main__":
    run_all_demos()
```

Save this script in the root of your project (for example as
`run_demos.py`), ensure it is executable, and run it with Python.
The script locates every `.py` file in the `demo` directory, sorts
them alphabetically, and executes them one after another. Errors
in one demo do not prevent later demos from running.

The typical contents of the `demo` directory include:

| Demo file | Description |
|---|---|
| `function_overloads.py` | Shows how to register and use multiple function overloads with positional and keyword type constraints. |
| `method_overloads.py` | Illustrates dispatch on instance methods, class methods, and static methods. |
| `property_only_class.py` | Demonstrates how to dispatch property setters based on the type of the assigned value. |
| `union_and_optional.py` | Uses `Union`, `Literal`, and `Optional` annotations in overloads. |
| `generic_containers.py` | Shows dispatch on list, tuple, dict, and set container types with type parameters. |

Refer to the source of each demo for details; the docstrings at
the top of each script describe what it tests and what output you
should expect.