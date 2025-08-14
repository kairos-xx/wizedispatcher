from wizedispatcher import dispatch


def test_overload_without_base_method_in_class() -> None:
    """Overload property/method without base still attaches dispatcher."""

    class Q:

        @dispatch.z(value=int)
        def _(self, value) -> str:
            return f"int:{value}"

    q: Q = Q()
    # The dispatcher should still be attached and callable
    assert hasattr(Q, "z")
    assert q.z(5) == "int:5"  # type: ignore[reportCallIssue]
