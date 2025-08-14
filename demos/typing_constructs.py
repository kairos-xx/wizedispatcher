"""Demonstrate Annotated, Literal, Optional, and Union dispatch.

Run
  python -m demos.typing_constructs
"""

from typing import Annotated, Literal, Optional, Union

from wizedispatcher import dispatch


def h(x: object) -> str:
    """Fallback overload used when no other overload matches.

    Args:
      x: Any runtime value.

    Returns:
      A fallback marker string.
    """
    return "fallback"


@dispatch.h(x=Literal[1, 2, 3])
def _(x: int) -> str:
    """Overload selected when x equals 1, 2, or 3."""
    return f"literal:{x}"


@dispatch.h
def _(x: Annotated[int, "meta"]) -> str:
    """Overload for `Annotated[int, ...]` values."""
    return f"annotated:{x}"


@dispatch.h
def _(x: Optional[int]) -> str:
    """Overload for optional ints including None."""
    return f"optional:{x}"


@dispatch.h
def _(x: Union[int, str]) -> str:
    """Overload for ints or strings via Union."""
    return f"union:{x}"


if __name__ == "__main__":
    print(h(2))
    print(h(10))
    print(h(None))
    print(h("ok"))
    print(h(3.14))
