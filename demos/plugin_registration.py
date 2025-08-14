"""Illustrate plugin-style overload registration.

Plugins can import a consumer's `dispatch.handle` and register overloads
without modifying the consumer module, as long as import ordering brings
the plugins into scope before calls.
"""

from wizedispatcher import dispatch


def handle(event: object) -> str:
    """Fallback consumer function when no plugin overload applies."""
    return "default"


@dispatch.handle(event=dict)
def _(event: dict) -> str:  # type: ignore[type-arg]
    """Plugin A overload for mapping events."""
    return f"dict:{sorted(event)}"


@dispatch.handle(event=list)
def _(event: list) -> str:  # type: ignore[type-arg]
    """Plugin B overload for sequence events."""
    return f"list:{len(event)}"


if __name__ == "__main__":
    print(handle({"a": 1, "b": 2}))
    print(handle([1, 2, 3]))
    print(handle(object()))
