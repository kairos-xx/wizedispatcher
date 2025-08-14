"""TypingNormalize basics demo.

This script shows how TypingNormalize converts various runtime and typing
constructs into canonical typing.* forms. The goal is to make downstream
matching and scoring consistent across Python versions and import styles.

Run
  python -m demos.typingnormalize_basics

Expected output shows normalized reprs for several cases.
"""

from __future__ import annotations

from typing import Any, Callable, Concatenate, Optional, Type, Union

from wizedispatcher.typingnormalize import TypingNormalize


def show(title: str, obj: object) -> None:
    """Print title and normalized repr of obj.

    Args:
      title: Short label for the case being demonstrated.
      obj: Any object that might represent a typing construct.
    """
    print(f"{title:36s} -> {repr(TypingNormalize(obj))}")


def main() -> None:
    """Demonstrate core normalization categories."""
    # Unions and PEP 604 unions
    show("Union flattening", Union[Union[int, str], Optional[bytes]])
    show("PEP 604 with None first", int | str | None)
    show("Any collapses union", Union[int, Any])

    # Bare generics and builtins
    show("Bare list -> List[Any]", list)
    show("Bare dict -> Dict[Any,Any]", dict)
    show("Bare tuple -> Tuple[Any,...]", tuple)
    show("Bare callable -> Callable[...,Any]", callable)

    # Callable shapes
    show("Callable[[int,str],R]", Callable[[int, str], bool])
    P = typing.ParamSpec("P")  # type: ignore[name-defined]
    show("Callable[Concatenate,...]", Callable[Concatenate[int, P], str]) # type: ignore[reportInvalidTypeForm]

    # Type[...] cases
    show("Type['int'] -> Type[int]", Type["int"])  # type: ignore[valid-type]

    class C:
        pass

    show("Type[C] preserves class", Type[C])


if __name__ == "__main__":
    main()


