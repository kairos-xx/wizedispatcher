"""Demonstrate string-based type hints and PEP 604 unions.

This demo shows that strings like "A" or "int | str" provided in the
decorator are normalized before matching.
"""

from __future__ import annotations

from wizedispatcher import dispatch


def show(x: object) -> str:
    """Fallback overload."""
    return "fallback"


class A:
    """Simple class A used for string-based type annotation demo."""

    pass


@dispatch.show(x="A")
def _(x: A) -> str:  # type: ignore[valid-type]
    """Selected when x is instance of class A."""
    return "string-annot:A"


@dispatch.show(x="int | str")
def _(x: object) -> str:
    """Selected when x is int or str via a string union expression."""
    return "string-union"


if __name__ == "__main__":
    print(show(A()))
    print(show(5))
    print(show("x"))
    print(show(3.14))
