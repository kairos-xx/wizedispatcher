from time import perf_counter

from wizedispatcher import dispatch


def f(x) -> str:
    _ = x
    return "base"


@dispatch.f(x=int)
def _(x) -> str:
    _ = x
    return "int"


N: int = 100_000

if __name__ == "__main__":
    # warm up cache
    f(1)
    t0: float = perf_counter()
    for _ in range(N):
        f(1)
    t1: float = perf_counter()
    for _ in range(N):
        f("x")
    t2: float = perf_counter()
    print("int calls (cached):", t1 - t0)
    print("fallback calls     :", t2 - t1)
