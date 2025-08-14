from wizedispatcher import dispatch


def base_fn(a, b, c) -> str:
    """Fallback implementation for `base_fn`.

    Returns:
      The default marker string.
    """
    _ = (a, b, c)
    return "default"


@dispatch.base_fn(a=str, c=float)
def _(a: str, b: int, c: float) -> str:
    """Overload for `(str, int, float)` path."""
    _ = (a, b, c)
    return "str-int-float"


@dispatch.base_fn(a=int)
def _(a, b, c) -> str:
    """Overload when `a` is an int."""
    _ = (a, b, c)
    return "a-int"


@dispatch.base_fn(int, bool)
def _(a, b, c) -> str:
    """Overload for `(int, bool, Any)` route."""
    _ = (a, b, c)
    return "int-bool"


def test_function_overloads() -> None:
    """Validate free-function overload selection across cases."""
    assert base_fn("hi", 1, 2.0) == "str-int-float"
    assert base_fn(5, {}, None) == "a-int"
    assert base_fn(3, True, "x") == "int-bool"
    assert base_fn(set(), object(), object()) == "default"


def test_methods_and_property() -> None:
    """Validate instance/class/static and property setter overloads."""

    class Toy:

        def __init__(self) -> None:
            """Initialize with default value for property storage."""
            self._v: int = 0

        def m(self, x: int) -> str:
            """Base instance method fallback for `m`."""
            return f"base:{x}"

        @dispatch.m(x=str)
        def _(self, x) -> str:
            """Overload for `m` when argument is a string."""
            return f"str:{x}"

        @dispatch.m
        def _(self, x: int | float) -> str:
            """Overload for `m` with numeric argument."""
            return f"num:{x}"

        @classmethod
        def c(cls, x: int) -> str:
            """Base classmethod fallback for `c`."""
            return f"c_base:{x}"

        @dispatch.c
        @classmethod
        def _(cls, x: str) -> str:
            """Overload for classmethod `c` when argument is string."""
            return f"c_str:{x}"

        @staticmethod
        def s(x: int) -> str:
            """Base staticmethod fallback for `s`."""
            return f"s_base:{x}"

        @dispatch.s
        @staticmethod
        def _(x: str) -> str:
            """Overload for staticmethod `s` when argument is string."""
            return f"s_str:{x}"

        @property
        def v(self) -> int:
            """Return the stored property value."""
            return self._v

        @v.setter
        def v(self, value) -> None:
            """Fallback setter used as the default path for `v`."""
            self._v = value

        @dispatch.v(value=str)
        def _(self, value: str) -> None:
            """Overload setter storing the length of the provided string."""
            self._v = len(value)

    t: Toy = Toy()
    assert t.m(3) == "base:3"
    assert t.m(3.14) == "num:3.14"  # type: ignore[reportCallIssue]
    assert Toy.c(7) == "c_base:7"
    assert Toy.c("q") == "c_str:q"  # type: ignore[reportCallIssue]
    assert Toy.s(9) == "s_base:9"
    assert Toy.s("w") == "s_str:w"  # type: ignore[reportCallIssue]
    t.v = "hey"
    assert t.v == 3
    t.v = 10
    assert t.v == 10
