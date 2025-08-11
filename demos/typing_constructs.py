from typing import Annotated, Literal, Optional, Union

from wizedispatcher import dispatch


def h(x) -> str:
    return "fallback"


@dispatch.h(x=Literal[1, 2, 3])
def _(x) -> str:
    return f"literal:{x}"


@dispatch.h
def _(x: Annotated[int, "meta"]) -> str:
    return f"annotated:{x}"


@dispatch.h
def _(x: Optional[int]) -> str:
    return f"optional:{x}"


@dispatch.h
def _(x: Union[int, str]) -> str:
    return f"union:{x}"


if __name__ == "__main__":
    print(h(2))  # literal:2
    print(
        h(10)
    )  # annotated:10 (also matches union/optional; specificity picks one)
    print(h(None))  # optional:None
    print(h("ok"))  # union:ok
    print(h(3.14))  # fallback
