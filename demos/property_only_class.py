"""Property-only class demo with typed setter overloads."""

from typing import Any

from wizedispatcher import dispatch


class Q:
    @property
    def v(self) -> Any:
        """Return stored value or None if not set."""
        return getattr(self, "_v", None)

    @v.setter
    def v(self, value: Any) -> None:
        self._v = value

    @dispatch.v(value=int)
    def _(self, value: int) -> None:
        """Setter overload for int values; doubles the input."""
        self._v = value * 2

    @dispatch.v(value=str)
    def _(self, value: str) -> None:
        """Setter overload for str values; wraps the text."""
        self._v = f"({value})"


if __name__ == "__main__":
    q: Q = Q()
    q.v = 3
    print(q.v)
    q.v = "hey"
    print(q.v)
