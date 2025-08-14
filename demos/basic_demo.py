"""Minimal demonstration of function overload registration.

Run
  python -m demos.basic_demo
"""

from __future__ import annotations

from wizedispatcher import dispatch


def test(a: object, b: object, c: object) -> str:
    """Fallback function used when no overload applies.

    Args:
      a: First argument.
      b: Second argument.
      c: Third argument.

    Returns:
      Default marker string when no overload matches.
    """
    return "default"


@dispatch.test(a=str, c=float)
def _(a: str, b: int, c: float) -> str:
    """Selected when (a is str) and (c is float).

    Args:
      a: String value.
      b: Integer value.
      c: Float value.
    """
    return "str-int-float"


@dispatch.test(a=int)
def _(a: object, b: object, c: object) -> str:
    """Selected when a is an int; others are unconstrained.

    Args:
      a: Any value; must be int at runtime.
      b: Any value.
      c: Any value.
    """
    return "a-int"


@dispatch.test(int, bool)
def _(a: object, b: object, c: object) -> str:
    """Selected when (a is int) and (b is bool) via positional mapping.

    Args:
      a: Any value; must be int at runtime.
      b: Any value; must be bool at runtime.
      c: Any value.
    """
    return "int-bool"


if __name__ == "__main__":
    print(test("hi", 1, 2.0))
    print(test(5, {}, None))
    print(test(3, True, "x"))
    print(test(set(), object(), object()))
