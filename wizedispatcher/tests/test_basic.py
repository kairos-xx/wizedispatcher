from wizedispatcher import dispatch


def base_fn(a, b, c) -> str:
    _ = (a, b, c)
    return "default"


@dispatch.base_fn(a=str, c=float)
def _(a: str, b: int, c: float) -> str:
    _ = (a, b, c)
    return "str-int-float"


@dispatch.base_fn(a=int)
def _(a, b, c) -> str:
    _ = (a, b, c)
    return "a-int"


@dispatch.base_fn(int, bool)
def _(a, b, c) -> str:
    _ = (a, b, c)
    return "int-bool"


# --- inside the pytest test function ---
def test_function_overloads() -> None:
    assert base_fn("hi", 1, 2.0) == "str-int-float"
    assert base_fn(5, {}, None) == "a-int"
    assert base_fn(3, True, "x") == "int-bool"
    assert base_fn(set(), object(), object()) == "default"


def test_methods_and_property() -> None:

    class Toy:

        def __init__(self) -> None:
            self._v = 0

        def m(self, x: int) -> str:
            return f"base:{x}"

        @dispatch.m(x=str)
        def _(self, x) -> str:
            return f"str:{x}"

        @dispatch.m
        def _(self, x: int | float) -> str:
            return f"num:{x}"

        @classmethod
        def c(cls, x: int) -> str:
            return f"c_base:{x}"

        @dispatch.c
        @classmethod
        def _(cls, x: str) -> str:
            return f"c_str:{x}"

        @staticmethod
        def s(x: int) -> str:
            return f"s_base:{x}"

        @dispatch.s
        @staticmethod
        def _(x: str) -> str:
            return f"s_str:{x}"

        @property
        def v(self) -> int:
            return self._v

        @v.setter
        def v(self, value) -> None:
            self._v = value

        @dispatch.v(value=str)
        def _(self, value: str) -> None:
            self._v = len(value)

    t: Toy = Toy()
    assert t.m(3) == "base:3"
    assert t.m(3.14) == "num:3.14" # type: ignore
    assert Toy.c(7) == "c_base:7"
    assert Toy.c("q") == "c_str:q" # type: ignore
    assert Toy.s(9) == "s_base:9"
    assert Toy.s("w") == "s_str:w" # type: ignore
    t.v = "hey"
    assert t.v == 3
    t.v = 10
    assert t.v == 10
