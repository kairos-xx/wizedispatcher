"""Demonstrate instance/class/static methods and property setter dispatch.

Run
  python -m demos.methods_and_property
"""

from wizedispatcher import dispatch


class Toy:
    """Toy class used to showcase various dispatch contexts."""

    def __init__(self) -> None:
        self._v = 0

    def m(self, x: int) -> str:
        """Base instance method; acts as fallback for `m`.

        Args:
          x: Integer value.

        Returns:
          Base marker string with the value.
        """
        return f"base:{x}"

    @dispatch.m(x=str)
    def _(self, x: object) -> str:
        """Overload for `m` when x is a string (decorator enforced)."""
        return f"str:{x}"

    @dispatch.m
    def _(self, x: int | float) -> str:
        """Overload for `m` when x is int or float via annotation."""
        return f"num:{x}"

    @classmethod
    def c(cls, x: int) -> str:
        """Base class method; fallback for `c`."""
        return f"c_base:{x}"

    @dispatch.c
    @classmethod
    def _(cls, x: str) -> str:
        """Overload for class method when x is a string."""
        return f"c_str:{x}"

    @staticmethod
    def s(x: int) -> str:
        """Base static method; fallback for `s`."""
        return f"s_base:{x}"

    @dispatch.s
    @staticmethod
    def _(x: str) -> str:
        """Overload for static method when x is a string."""
        return f"s_str:{x}"

    @property
    def v(self) -> int:
        """Return the stored integer value."""
        return self._v

    @v.setter
    def v(self, value: object) -> None:
        """Base setter used as fallback for property `v`.

        For demonstration, strings are coerced with int(), and other values
        are also coerced with int().
        """
        self._v = int(value) if isinstance(value, str) else int(value)  # type: ignore[reportArgumentType]

    @dispatch.v(value=str)
    def _(self, value: str) -> None:
        """Overload for setter; store the length of the string value."""
        self._v = len(value)


if __name__ == "__main__":
    t: Toy = Toy()
    print(t.m(10))
    print(t.m(3.14)) # type: ignore[reportArgumentType]
    print(Toy.c(7))
    print(Toy.c("q")) # type: ignore[reportArgumentType]
    print(Toy.s(5))
    print(Toy.s("w")) # type: ignore[reportArgumentType]
    t.v = "hello"
    print(t.v)
    t.v = 42
    print(t.v)
