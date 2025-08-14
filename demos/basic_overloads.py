"""Small greeting example using multiple overloads.

Run
  python -m demos.basic_overloads
"""

from wizedispatcher import dispatch


def greet(x: object) -> str:
    """Fallback overload."""
    return "fallback"


@dispatch.greet(x=str)
def _(x: str) -> str:
    """Greet string inputs by name.

    Args:
      x: Person name as a string.

    Returns:
      Friendly greeting for the provided name.
    """
    return f"hello {x}"


@dispatch.greet(int)
def _(x: int) -> str:
    """Greet integer inputs as numeric identifiers."""
    return f"num {x}"


@dispatch.greet(x=bytes)
def _(x: bytes) -> str:
    """Greet byte inputs, showing their repr for clarity."""
    return f"bytes {x!r}"


if __name__ == "__main__":
    print(greet("Ana"))
    print(greet(7))
    print(greet(b"abc"))
    print(greet(object()))
