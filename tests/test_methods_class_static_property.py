from wizedispatcher import dispatch


def test_methods_class_static_and_property_setter() -> None:
    """End-to-end test for methods, class/static, and property setter."""

    class T:

        def __init__(self) -> None:
            """Initialize storage for property value."""
            self._v = 0

        def m(self, x: int) -> str:
            """Base method fallback for `m`."""
            return f"base:{x}"

        @dispatch.m(x=str)
        def _(self, x) -> str:
            """Overload for `m` when string is provided."""
            return f"str:{x}"

        @dispatch.m
        def _(self, x: int | float) -> str:
            """Overload for `m` when a number is provided."""
            return f"num:{x}"

        @classmethod
        def c(cls, x: int) -> str:
            """Base classmethod fallback for `c`."""
            return f"c_base:{x}"

        @dispatch.c
        @classmethod
        def _(cls, x: str) -> str:
            """Overload for classmethod `c` when string provided."""
            return f"c_str:{x}"

        @staticmethod
        def s(x: int) -> str:
            """Base staticmethod fallback for `s`."""
            return f"s_base:{x}"

        @dispatch.s
        @staticmethod
        def _(x: str) -> str:
            """Overload for staticmethod `s` when string provided."""
            return f"s_str:{x}"

        @property
        def v(self) -> int:
            """Return stored property value."""
            return self._v

        @v.setter
        def v(self, value) -> None:
            """Fallback setter for property `v`."""
            self._v = value

        @dispatch.v(value=str)
        def _(self, value: str) -> None:
            """Overload setter storing the length of the string."""
            self._v = len(value)

    t: T = T()
    assert t.m(10) == "base:10"
    assert t.m(2.5) == "num:2.5"  # type: ignore[reportCallIssue]
    assert T.c(7) == "c_base:7"
    assert T.c("q") == "c_str:q"  # type: ignore[reportCallIssue]
    assert T.s(3) == "s_base:3"
    assert T.s("w") == "s_str:w"  # type: ignore[reportCallIssue]
    t.v = "hey"
    assert t.v == 3
    t.v = 42
    assert t.v == 42
