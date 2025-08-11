from wizedispatcher import dispatch


def gname(x) -> str:  # type: ignore
    _ = x
    return "fallback"


@dispatch.gname(x=str)
def _(x) -> str:
    _ = x
    return "str"


def gname(x) -> str:  # type: ignore
    _ = x
    return "fallback2"


@dispatch.gname(x=int)
def _(x) -> str:
    _ = x
    return "int"


def test_register_after_existing_wrapper_replacement() -> None:
    assert gname("a") == "str"
    assert gname(1) == "int"
    assert gname(object()) == "fallback2"
