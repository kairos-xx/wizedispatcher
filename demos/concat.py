from __future__ import annotations

from typing import Any

from wizedispatcher import dispatch


def concat(a: Any, b: Any, c: Any = "default") -> str:
    """Fallback function."""
    return f"default - {a}{b}{c}"


@dispatch.concat
def _a(a: int, b: int) -> str:
    """Overload `_a`: uses fallback default for `c` if not provided."""
    return f"_a - {a + b}{c}"  # type: ignore[name-defined]


@dispatch.concat(b=float)
def _b(c: int = 3) -> str:
    """Overload `_b`: provides own default `c=3`; `b` must be float."""
    return f"_b - {a}{b + c}"  # type: ignore[name-defined]


@dispatch.concat(str, c=bool)
def _c(b: bool) -> str:
    """Overload `_c`: requires `a: str` and `c: bool` explicitly."""
    return f"_c - {a}{b and c}"  # type: ignore[name-defined]


if __name__ == "__main__":
    print(concat(1, 2))  # _a - 3default
    print(concat(1, 2, "s"))  # _a - 3s
    print(concat(1, 2.2, 3))  # _b - 15.2
    print(concat("1", True, False))  # _c - 1False

    # Bonus: show fallback when bool `c` not provided for _c
    print(concat("1", True))  # default - 1Truedefault
