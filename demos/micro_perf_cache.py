"""Micro benchmark to illustrate cache hits vs fallback calls.

The hot path repeatedly calls the same overload and should be faster than
calling the fallback function because it avoids selection work.
"""

from time import perf_counter

from wizedispatcher import dispatch


def f(x: object) -> str:
    """Fallback implementation for `f` when no overload matches.

    This simulates the slower path that performs selection work as the
    dispatcher resolves the best overload.

    Args:
      x: Any runtime value.

    Returns:
      The base marker string "base".
    """
    return "base"


@dispatch.f(x=int)
def _(x: int) -> str:
    """Overload for `f` when ``x`` is an ``int``.

    Repeated calls with the same shape exercise the hot path because the
    dispatcher fetches the cached selection.

    Args:
      x: Integer argument that triggers this overload.

    Returns:
      The marker string "int".
    """
    return "int"


N: int = 100_000  # Number of iterations for the micro benchmark

if __name__ == "__main__":
    # Warm up the cache by selecting and caching the `int` overload.
    f(1)
    t0: float = perf_counter()
    for _ in range(N):
        # Hot path: cached selection for the `int` overload.
        f(1)
    t1: float = perf_counter()
    for _ in range(N):
        # Fallback path: selection resolves to base due to mismatched type.
        f("x")
    t2: float = perf_counter()
    print("int calls (cached):", t1 - t0)
    print("fallback calls     :", t2 - t1)
