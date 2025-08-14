from __future__ import annotations

from typing import Any

from pytest import mark
from wizedispatcher import dispatch


def concat(a: Any, b: Any, c: Any = 4) -> str:
    """Fallback for concat used by all overload-specific tests.

    Args:
      a: First argument.
      b: Second argument.
      c: Optional tail argument with a default.

    Returns:
      A formatted string encoding the result shape.
    """
    return f"default - {a}{b}{c}"


@dispatch.concat
def _a(a: int, b: int) -> str:
    """Overload `_a` using fallback default for `c` when omitted."""
    return f"_a - {a + b}{c}"  # type: ignore[name-defined]


@dispatch.concat(b=float)
def _b(c: int = 3) -> str:
    """Overload `_b` with own default `c=3`; `b` must be float."""
    return f"_b - {a}{b + c}"  # type: ignore[name-defined]


@dispatch.concat(str, c=bool)
def _c(b: bool) -> str:
    """Overload `_c` requires `a: str` and `c: bool` explicitly."""
    return f"_c - {a}{b and c}"  # type: ignore[name-defined]


class TestConcatDispatch:
    """Behavior tests for overloads and injected defaults."""

    @mark.parametrize(
        ("args", "expected"),
        [
            ((1, 2), "_a - 34"),
            ((1, 2, "s"), "_a - 3s"),
            ((1, 2.2, 3), "_b - 15.2"),
            (("1", True, False), "_c - 1False"),
        ],
    )
    def test_basic_cases(self, args: tuple[Any, ...], expected: str) -> None:
        """Core matching across all three overload styles.

        Args:
          args: Positional inputs to call `concat` with.
          expected: Expected formatted string result.
        """
        assert concat(*args) == expected

    def test_fallback_when_bool_not_provided(self) -> None:
        """`_c` should not match unless `c` is explicitly a bool."""
        # Here: a=str, b=bool, c omitted -> falls back to original.
        assert concat("1", True) == "default - 1True4"

    def test_injection_of_missing_names(self) -> None:
        """Undeclared names in body (e.g., `c` in `_a`) are injected."""
        out: str = concat(5, 7)  # `_a` + fallback default c="4"
        assert out.endswith("4")
        assert out == "_a - 124"

    def test_overload_default_used_when_c_missing(self) -> None:
        """`_b` uses its own default `c=3` when `c` is omitted."""
        # Note: b must be float to select _b.
        assert concat(9, 1.0) == "_b - 95.0"
        # Let's assert the exact intended output:
        assert concat(1, 2.2) == "_b - 16.2"
