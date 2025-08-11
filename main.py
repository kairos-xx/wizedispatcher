#!/usr/bin/env python3
"""WizeDispatchershowcase (entry-level, v4: version-robust).

Highlights (robust across versions):
- Free functions (keyword/positional decorator types)
- Instance/class/static methods
- Property setter dispatch (with a safe base setter)
- Containers, Optional, Callable
- Container-kind dispatch (list[int] vs tuple[int, ...])
- Omitted-param overloads with injected defaults
  (fallback defaults + overload-provided defaults + gated params)

Requires: `pip install wizedispatcher`
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Union

from wizedispatcher import dispatch


# ---------- simple styling ---------- #
class C:
    R: str = "\033[31m"
    G: str = "\033[32m"
    Y: str = "\033[33m"
    B: str = "\033[34m"
    C: str = "\033[36m"
    W: str = "\033[97m"
    DIM: str = "\033[2m"
    BOLD: str = "\033[1m"
    RESET: str = "\033[0m"


def title(text: str) -> None:
    bar: str = "═" * (len(text) + 2)
    print(f"\n{C.C}╔{bar}╗{C.RESET}")
    print(f"{C.C}║ {C.BOLD}{text}{C.RESET}{C.C} ║{C.RESET}")
    print(f"{C.C}╚{bar}╝{C.RESET}")


def show(label: str, got: object, expected: object | None = None) -> None:
    ok: bool = expected is None or got == expected
    mark: str = f"{C.G}✓{C.RESET}" if ok else f"{C.R}✗{C.RESET}"
    exp: str = "" if expected is None else f"{C.DIM} (expected {expected}){C.RESET}"
    print(f" {mark} {C.BOLD}{label}{C.RESET}: {got}{exp}")


# ---------- 1) free functions ---------- #
def concat(a: object, b: object) -> str:
    """Fallback: string concatenation by default."""
    return f"{a}{b}"


@dispatch.concat(a=int, b=int)
def _(a: int, b: int) -> int:
    """Sum numbers when both args are ints."""
    return a + b


@dispatch.concat
def _(a: str, b: str) -> str:
    """Concatenate strings (explicit overload)."""
    return a + b


@dispatch.concat(int, bool)
def _(a, b) -> str:
    """Show positional type registration: (int, bool)."""
    return f"int/bool:{a}-{b}"


# ---------- 2) typing demos ---------- #
def describe(x: object) -> str:
    """Fallback: coarse description."""
    return f"type={type(x).__name__}"


@dispatch.describe
def _(x: Optional[int]) -> str:
    """Optional demo (None or int)."""
    return "none" if x is None else f"int:{x}"


@dispatch.describe
def _(x: list[int]) -> str:
    """Container origin demo (list[int])."""
    return f"list[int]:{len(x)}"


# Broad Callable demo (version-safe): accept any callable
@dispatch.describe(x=Callable)
def _(x) -> str:
    """Callable demo (broad, version-robust)."""
    _ = x
    return "callable"


# Container-kind dispatch (robust and visually clear)
def classify(xs: object) -> str:
    """Fallback for sequences."""
    _ = xs
    return "unknown"


@dispatch.classify
def _(xs: list[int]) -> str:
    _ = xs
    return "list[int]"


@dispatch.classify
def _(xs: tuple[int, ...]) -> str:
    _ = xs
    return "tuple[int,...]"


# ---------- 3) methods, class/static, property ---------- #
class Toy:
    """Examples for method dispatch and property setter dispatch."""

    def m(self, x: object) -> str:
        return f"base:{x}"

    @dispatch.m(x=str)
    def _(self, x) -> str:
        return f"str:{x}"

    @dispatch.m
    def _(self, x: Union[int, float]) -> str:
        return f"num:{x}"

    @classmethod
    def cm(cls, x: object) -> str:
        return f"cm base:{x}"

    @dispatch.cm
    @classmethod
    def _(cls, x: bool) -> str:
        return f"cm bool:{x}"

    @staticmethod
    def sm(x: object) -> str:
        return f"sm base:{x}"

    @dispatch.sm
    @staticmethod
    def _(x: str) -> str:
        return f"sm str:{x}"

    @property
    def v(self) -> int | str:
        return getattr(self, "_v", 0)

    # Base setter keeps (self, value) signature consistent everywhere
    @v.setter
    def v(self, value: object) -> None:
        self._v = value  # fallback

    @dispatch.v(value=int)
    def _(self, value: int) -> None:
        self._v = value * 2

    @dispatch.v(value=str)
    def _(self, value: str) -> None:
        self._v = f"({value})"


def times_two(n: int) -> int:
    return 2 * n


# ---------- 5) NEW FEATURES: omitted params + default injection ---------- #
def concat_adv(a: Any, b: Any, c: Any = "default") -> str:
    """Fallback that carries a default for `c` used by overloads."""
    return f"default - {a}{b}{c}"


# Uses fallback default for `c` (overload omits `c`)
@dispatch.concat_adv
def _adv_a(a: int, b: int) -> str:
    """Overload: treat as (a: int, b: int, c: str='default')."""
    return f"_a - {a + b}{c}"  # type: ignore[name-defined]


# Overload provides its own default for `c`; `b` must be float
@dispatch.concat_adv(b=float)
def _adv_b(c: int = 3) -> str:
    """Overload: treat as (a: object, b: float, c: int=3)."""
    return f"_b - {a}{b + c}"  # type: ignore[name-defined]


# Requires `a: str` and `c: bool` explicitly; no default for `c`
@dispatch.concat_adv(str, c=bool)
def _adv_c(b: bool) -> str:
    """Overload: (a: str, b: bool, c: bool) — only if `c` is bool."""
    return f"_c - {a}{b and c}"  # type: ignore[name-defined]


def main() -> None:
    title("WizeDispatcher— Entry-Level Showcase")

    title("1) Free Functions")
    show("concat(2, 3) → int+int", concat(2, 3), 5)
    show("concat('a','b') → str+str", concat("a", "b"), "ab")
    show("concat(7, True) → positional overload", concat(7, True),
         "int/bool:7-True")

    title("2) Typing: Optional, Container, Callable, Container-Kind")
    show("describe(None) → Optional[int]", describe(None), "none")
    show("describe([1,2,3]) → list[int]", describe([1, 2, 3]), "list[int]:3")
    show("describe(times_two) → Callable (broad)", describe(times_two),
         "callable")
    show("classify([1,2]) → list[int]", classify([1, 2]), "list[int]")
    show("classify((1,2,3)) → tuple[int,...]", classify((1, 2, 3)),
         "tuple[int,...]")
    show("classify({'a': 1}) → fallback", classify({"a": 1}), "unknown")

    title("3) Methods, Class/Static")
    t: Toy = Toy()
    show("Toy().m(3.14) → num", t.m(3.14), "num:3.14")
    show("Toy().m('hi') → str", t.m("hi"), "str:hi")
    show("Toy.cm(True) → classmethod(bool)", Toy.cm(True), "cm bool:True")
    show("Toy.cm(42) → classmethod(base)", Toy.cm(42), "cm base:42")
    show("Toy.sm('yo') → static(str)", Toy.sm("yo"), "sm str:yo")
    show("Toy.sm({'x':1}) → static(base)", Toy.sm({"x": 1}),
         "sm base:{'x': 1}")

    title("4) Property Setter Dispatch")
    t.v = 7
    show("t.v = 7 → doubled", t.v, 14)
    t.v = "hey"
    show("t.v = 'hey' → wrapped", t.v, "(hey)")

    title("5) Omitted Params + Default Injection")
    show("concat_adv(1, 2) → _a + fallback c",
         concat_adv(1, 2), "_a - 3default")
    show("concat_adv(1, 2, 's') → _a with c='s'",
         concat_adv(1, 2, "s"), "_a - 3s")
    show("concat_adv(1, 2.2, 3) → _b (b=float, c=3)",
         concat_adv(1, 2.2, 3), "_b - 15.2")
    show("concat_adv('1', True, False) → _c (a=str, c=bool)",
         concat_adv("1", True, False), "_c - 1False")
    show("concat_adv('1', True) → fallback (no c:bool)",
         concat_adv("1", True), "default - 1Truedefault")

    print(f"\n{C.DIM}Done. All green checks mean the overload matched as "
          f"intended.{C.RESET}\n")


if __name__ == "__main__":
    main()
