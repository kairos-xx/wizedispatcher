"""Demonstrate dispatch on lists and tuples with element typing.

Run
  python -m demos.containers_and_tuples
"""

from typing import Tuple

from wizedispatcher import dispatch


def pack(x: object) -> str:
    """Fallback for non-list/tuple shapes."""
    return "base"


@dispatch.pack(x=list[int])
def _(x: list[int]) -> str:
    """Sum a list of ints."""
    return f"list:{sum(x)}"


@dispatch.pack(x=Tuple[int, ...])
def _(x: Tuple[int, ...]) -> str:
    """Sum a variadic tuple of ints."""
    return f"tuple*:{sum(x)}"


@dispatch.pack(x=Tuple[int, int])
def _(x: Tuple[int, int]) -> str:
    """Sum a 2-item tuple of ints and show components."""
    return f"tuple2:{x[0]}+{x[1]}={sum(x)}"


if __name__ == "__main__":
    print(pack([1, 2, 3]))
    print(pack((1, 2, 3, 4)))
    print(pack((5, 7)))
    print(pack({1, 2, 3}))
