from wizedispatcher import dispatch


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


if __name__ == "__main__":
    t: Toy = Toy()
    print(t.m(10))  # base:10
    print(t.m(3.14))  # num:3.14 # type: ignore
    print(Toy.c(7))  # c_base:7
    print(Toy.c("q"))  # c_str:q # type: ignore
    print(Toy.s(5))  # s_base:5
    print(Toy.s("w"))  # s_str:w # type: ignore
    t.v = "hello"
    print(t.v)  # 5
    t.v = 42
    print(t.v)  # 42
