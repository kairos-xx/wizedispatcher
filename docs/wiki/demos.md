# Demos

The [`demos`](../../demos/) directory contains small programs that exercise the
features of WizeDispatcher. Each script can be run directly. To
run all demos sequentially, use the following helper script:

```python
#!/usr/bin/env python3
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
            run([executable, str(file_path)], check=True)
        except CalledProcessError as e:
            print(f"Demo {file_path.name} failed with exit code {e.returncode}")
        except Exception as exc:
            print(f"Error running {file_path.name}: {exc}")


if __name__ == "__main__":
    run_all_demos()
```

Save this script in the root of your project (for example as
`run_demos.py`), ensure it is executable, and run it with Python.
The script locates every `.py` file in the `demos` directory, sorts
them alphabetically, and executes them one after another. Errors
in one demo do not prevent later demos from running.

The typical contents of the `demos` directory include:

| Demo file | Description |
|---|---|
| [`basic_demo.py`](../../demos/basic_demo.py) | End-to-end showcase with formatted output. |
| [`basic_overloads.py`](../../demos/basic_overloads.py) | Minimal examples of free function overloads. |
| [`callable_signatures.py`](../../demos/callable_signatures.py) | Callable shape matching and ParamSpec/Concatenate. |
| [`concat.py`](../../demos/concat.py) | Partial hints and injected defaults in practice. |
| [`containers_and_tuples.py`](../../demos/containers_and_tuples.py) | Dispatch on lists/tuples/mappings with element type checking. |
| [`forwardref_and_strings.py`](../../demos/forwardref_and_strings.py) | Normalization of `Type["int"]` and forward references. |
| [`methods_and_property.py`](../../demos/methods_and_property.py) | Instance/class/static methods and property setter overloads. |
| [`micro_perf_cache.py`](../../demos/micro_perf_cache.py) | Quick look at cold vs hot dispatch paths. |
| [`plugin_registration.py`](../../demos/plugin_registration.py) | Simple plugin-style registration via dispatch. |
| [`property_only_class.py`](../../demos/property_only_class.py) | Dispatch property setters by assigned value type. |
| [`run_all.py`](../../demos/run_all.py) | Helper to execute all demos. |
| [`shape_bias_and_cache.py`](../../demos/shape_bias_and_cache.py) | Structure-aware cache and call-shape effects. |
| [`typed_dict_and_protocol.py`](../../demos/typed_dict_and_protocol.py) | TypedDict and runtime Protocol dispatching. |
| [`typing_constructs.py`](../../demos/typing_constructs.py) | `Annotated`, `Literal`, unions, callable shapes. |
| [`typingnormalize_basics.py`](../../demos/typingnormalize_basics.py) | TypingNormalize basics and normalization guarantees. |
| [`typingnormalize_forwardrefs.py`](../../demos/typingnormalize_forwardrefs.py) | TypingNormalize with ForwardRef and string types. |

Refer to the source of each demo for details; the docstrings at
the top of each script describe what it tests and what output you
should expect.

## Partial Hints and Missing Params Demo

```python
from wizedispatcher.demos.concat import concat

print(concat(1, 2))            # _a - 3default
print(concat(1, 2, "s"))       # _a - 3s
print(concat(1, 2.2, 3))       # _b - 15.2
print(concat("1", True, False))# _c - 1False
```
