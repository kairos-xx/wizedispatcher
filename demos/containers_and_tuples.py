from typing import Tuple

from wizedispatcher import dispatch


def pack(x) -> str:
    return "base"


@dispatch.pack(x=list[int])
def _(x) -> str:
    return f"list:{sum(x)}"


@dispatch.pack(x=Tuple[int, ...])
def _(x) -> str:
    return f"tuple*:{sum(x)}"


@dispatch.pack(x=Tuple[int, int])
def _(x) -> str:
    return f"tuple2:{x[0]}+{x[1]}={sum(x)}"


if __name__ == "__main__":
    print(pack([1, 2, 3]))  # list:6
    print(pack((1, 2, 3, 4)))  # tuple*:10
    print(pack((5, 7)))  # tuple2:5+7=12
    print(pack({1, 2, 3}))  # base
