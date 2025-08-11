from wizedispatcher import dispatch


def test_methods_class_static_and_property_setter() -> None:

    class T:

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

    t: T = T()
    assert t.m(10) == "base:10"
    assert t.m(2.5) == "num:2.5"  # type: ignore
    assert T.c(7) == "c_base:7"
    assert T.c("q") == "c_str:q"  # type: ignore
    assert T.s(3) == "s_base:3"
    assert T.s("w") == "s_str:w"  # type: ignore
    t.v = "hey"
    assert t.v == 3
    t.v = 42
    assert t.v == 42
