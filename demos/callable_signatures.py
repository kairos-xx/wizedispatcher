"""Demonstrate dispatch on callable parameter shapes.

Run
  python -m demos.callable_signatures
"""

from typing import Callable

from wizedispatcher import dispatch


def run(fn: object) -> str:
    """Fallback overload for non-matching callables.

    Args:
      fn: Any callable value.
    """
    return "fallback"


@dispatch.run(fn=Callable[[int, str], bool])
def _(fn: Callable[[int, str], bool]) -> str:
    """Selected when fn accepts (int, str) and returns bool."""
    return "typed-callback"


def ok(a: int, b: str) -> bool:
    """Valid callback used to satisfy the overload."""
    return True


def bad(a: str, b: int) -> bool:
    """Invalid callback; parameter order/types do not match."""
    return True


if __name__ == "__main__":
    print(run(ok))
    print(run(bad))
