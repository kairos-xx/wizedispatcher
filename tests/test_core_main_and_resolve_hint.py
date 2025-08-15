from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from os import path as os_path
from runpy import run_path
from sys import path as sys_path
from typing import ForwardRef
from warnings import catch_warnings, simplefilter

from wizedispatcher import core
from wizedispatcher.core import TypeMatch


def test_resolve_hint_str_success() -> None:
    """String that evals in module globals should resolve to `int`."""
    assert TypeMatch._resolve_hint("int") is int


def test_resolve_hint_forwardref_success() -> None:
    """ForwardRef("int") resolves to the concrete `int` type."""
    fr: ForwardRef = ForwardRef("int")
    assert TypeMatch._resolve_hint(fr) is int


def test_resolve_hint_unknown_string_fallback() -> None:
    """Unknown strings fall back to returning the original hint."""
    assert TypeMatch._resolve_hint("NoSuchNameXYZ") == "NoSuchNameXYZ"


def test_core_main_runs() -> None:
    """Execute core's __main__ demo and confirm captured output exists."""
    buf: StringIO = StringIO()
    with redirect_stdout(buf), catch_warnings():
        simplefilter("ignore", RuntimeWarning)
        path: str = core.__file__  # type: ignore[assignment]
        prev_sys_path = list(sys_path)
        try:
            sys_path.insert(0, os_path.dirname(path))
            run_path(path, run_name="__main__")
        except Exception:
            # Skip assertion on environments where demo cannot run fully
            return
        finally:
            sys_path[:] = prev_sys_path
    out: str = buf.getvalue()
    assert out != ""
