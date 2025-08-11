from __future__ import annotations

from wizedispatcher import dispatch


def test(a, b, c) -> str:
    _ = (a, b, c)
    return "default"


@dispatch.test(a=str, c=float)
def _(a: str, b: int, c: float) -> str:
    _ = (a, b, c)
    return "str-int-float"


@dispatch.test(a=int)
def _(a, b, c) -> str:
    _ = (a, b, c)
    return "a-int"


@dispatch.test(int, bool)
def _(a, b, c) -> str:
    _ = (a, b, c)
    return "int-bool"


if __name__ == "__main__":
    print(test("hi", 1, 2.0))
    print(test(5, {}, None))
    print(test(3, True, "x"))
    print(test(set(), object(), object()))
