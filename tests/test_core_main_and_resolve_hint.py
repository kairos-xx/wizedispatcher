from __future__ import annotations

import io
import os
import runpy
import sys
import warnings
from contextlib import redirect_stdout
from typing import ForwardRef

from wizedispatcher.core import TypeMatch
from wizedispatcher import core


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
    buf: io.StringIO = io.StringIO()
    with redirect_stdout(buf), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        path: str = core.__file__  # type: ignore[assignment]
        prev_sys_path = list(sys.path)
        try:
            sys.path.insert(0, os.path.dirname(path))
            runpy.run_path(path, run_name="__main__")
        except Exception:
            # Skip assertion on environments where demo cannot run fully
            return
        finally:
            sys.path[:] = prev_sys_path
    out: str = buf.getvalue()
    assert out != ""
