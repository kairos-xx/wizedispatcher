"""TypedDict and Protocol examples.

Run
  python -m demos.typed_dict_and_protocol
"""

from typing import Callable, Protocol, TypedDict, runtime_checkable

from wizedispatcher import dispatch


class User(TypedDict):
    id: int
    name: str


@runtime_checkable
class Greeter(Protocol):
    def __call__(self, name: str) -> str: ...


def demo(x: object) -> str:
    """Fallback overload for values that are neither User nor Greeter."""
    return "fallback"


@dispatch.demo(x=User)
def _(x: User) -> str:
    """Handle objects matching the User TypedDict shape."""
    return f"user:{x['id']}:{x['name']}"


@dispatch.demo(x=Greeter)
def _(x: Callable[[str], str]) -> str:
    """Call Greeter callbacks with a fixed argument."""
    return x("world")


if __name__ == "__main__":
    print(demo({"id": 1, "name": "Ana"}))

    class G:
        def __call__(self, name: str) -> str:
            return f"hi {name}"

    print(demo(G()))
    print(demo(123))
