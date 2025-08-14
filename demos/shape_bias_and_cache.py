"""Demonstrate shape bias and structure-aware cache behavior.

Repeated calls with the same call shape (types and *args/**kwargs keys)
hit the cache even if the values differ. Variadic overloads still add
small penalties but can match broader shapes.
"""

from typing import Dict

from wizedispatcher import dispatch

calls: Dict[str, int] = {"base": 0, "varpos": 0, "varkw": 0}


def f(a: object, b: object) -> str:
    """Base function used to count fallback calls."""
    calls["base"] += 1
    return f"base:{a}:{b}"


@dispatch.f(a=int, b=str)
def _(a: int, b: str, *args: object) -> str:
    """Overload that accepts extra positional arguments."""
    calls["varpos"] += 1
    return f"varpos:{a}:{b}:{len(args)}"


@dispatch.f(a=int)
def _(a: int, b: object, **kwargs: object) -> str:
    """Overload that accepts arbitrary keyword arguments."""
    calls["varkw"] += 1
    return f"varkw:{a}:{b}:{list(kwargs)}"


if __name__ == "__main__":
    print(f(1, "x"))
    print(f(2, "y"))
    print(f(3, 4))
    print(f("a", "b"))
    print("calls:", calls)
