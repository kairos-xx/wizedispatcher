from wizedispatcher import dispatch


def f(a, *args, **kwargs):  # type: ignore[reportRedeclaration]
    """Fallback `f` returning raw call shape for inspection."""
    return (a, args, kwargs)


@dispatch.f
def f(a: int, *args, **kwargs):  # type: ignore[reportRedeclaration]
    """Overload for `a: int` which also accepts variadics."""
    return "int"


def test_cache_key_includes_structure() -> None:
    """Cache keys account for variadic shape; resolution remains stable."""
    assert f(1) == "int"
    assert f(1, 2) == "int"  # type: ignore[reportCallIssue]
    assert f(1, 2, 3) == "int"  # type: ignore[reportCallIssue]
    assert f(1, x=1) == "int"  # type: ignore[reportCallIssue]
    assert f(1, y=1) == "int"  # type: ignore[reportCallIssue]
