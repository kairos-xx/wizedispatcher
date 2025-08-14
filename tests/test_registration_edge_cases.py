from wizedispatcher import dispatch


def gname(x: object) -> str:  # type: ignore[reportRedeclaration]
    """Initial fallback used before wrapper replacement edge case."""
    _ = x
    return "fallback"


@dispatch.gname(x=str)
def _(x: str) -> str:
    """Overload when x is a string."""
    _ = x
    return "str"


def gname(x: object) -> str:  # type: ignore[reportRedeclaration]
    """Replacement fallback to simulate wrapper replacement."""
    _ = x
    return "fallback2"


@dispatch.gname(x=int)
def _(x: int) -> str:
    """Overload when x is an integer."""
    _ = x
    return "int"


def test_register_after_existing_wrapper_replacement() -> None:
    """Ensure dispatch remains callable after wrapper replacement."""
    assert gname("a") == "str"
    assert gname(1) == "int"
    assert gname(object()) == "fallback2"
