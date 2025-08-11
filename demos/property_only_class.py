from typing import Any

from wizedispatcher import dispatch


class Q:

    @property
    def v(self) -> Any:
        return getattr(self, "_v", None)

    @v.setter
    def v(self, value) -> None:
        self._v = value

    @dispatch.v(value=int)
    def _(self, value) -> None:
        self._v = value * 2

    @dispatch.v(value=str)
    def _(self, value) -> None:
        self._v = f"({value})"


if __name__ == "__main__":
    q: Q = Q()
    q.v = 3
    print(q.v)  # 6
    q.v = "hey"
    print(q.v)  # (hey)
