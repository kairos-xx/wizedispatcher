from typing import Callable

from wizedispatcher import dispatch


def run(fn) -> str:
    return "fallback"


@dispatch.run(fn=Callable[[int, str], bool])
def _(fn: Callable[[int, str], bool]) -> str:
    _ = fn
    return "typed-callback"


def ok(a: int, b: str) -> bool:
    _ = (a, b)
    return True


def bad(a: str, b: int) -> bool:
    _ = (a, b)
    return True


if __name__ == "__main__":
    print(run(ok))  # typed-callback
    print(run(bad))  # fallback (sig mismatch)
