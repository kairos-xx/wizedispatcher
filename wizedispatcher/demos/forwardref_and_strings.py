from __future__ import annotations

from wizedispatcher import dispatch


def show(x) -> str:
    _ = x
    return "fallback"


class A:
    pass


@dispatch.show(x="A")
def _(x) -> str:
    _ = x
    return "string-annot:A"


@dispatch.show(x="int | str")
def _(x) -> str:
    _ = x
    return "string-union"


if __name__ == "__main__":
    print(show(A()))  # string-annot:A
    print(show(5))  # string-union
    print(show("x"))  # string-union
    print(show(3.14))  # fallback
