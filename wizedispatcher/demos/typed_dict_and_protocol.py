from typing import Callable, Protocol, TypedDict, runtime_checkable

from wizedispatcher import dispatch


class User(TypedDict):
    id: int
    name: str


@runtime_checkable
class Greeter(Protocol):

    def __call__(self, name: str) -> str: ...


def demo(x) -> str:
    _ = x
    return "fallback"


@dispatch.demo(x=User)
def _(x) -> str:
    return f"user:{x['id']}:{x['name']}"


@dispatch.demo(x=Greeter)
def _(x: Callable[[str], str]) -> str:
    return x("world")


if __name__ == "__main__":
    print(demo({"id": 1, "name": "Ana"}))  # user:1:Ana

    class G:

        def __call__(self, name: str) -> str:
            return f"hi {name}"

    print(demo(G()))  # hi world
    print(demo(123))  # fallback
