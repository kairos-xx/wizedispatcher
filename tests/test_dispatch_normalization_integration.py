from typing import Annotated, ClassVar, Literal, Optional, Type

from wizedispatcher import dispatch


def target(a, b):  # type: ignore[reportRedeclaration]
    """Fallback target; simply returns input tuple."""
    return (a, b)


@dispatch.target
def target(a: Annotated[int, "m"], b: str):  # type: ignore[reportRedeclaration]
    """Overload requiring Annotated[int, ...] for parameter `a`."""
    return "annotated"


@dispatch.target
def target(a: ClassVar[int], b: str):  # type: ignore[type-arg,reportRedeclaration]
    """Overload demonstrating ClassVar normalization."""
    return "classvar"


@dispatch.target
def target(a: Optional[int], b: str):  # type: ignore[reportRedeclaration]
    """Overload using Optional for parameter `a`."""
    return "optional"


@dispatch.target
def target(a: Type["int"], b: str):  # type: ignore[valid-type,reportRedeclaration]
    """Overload resolving string-based Type["int"]."""
    return "type_str"


# Separate function to avoid cache interactions between literal and annotated
def target_lit(a, b):  # type: ignore[reportRedeclaration]
    """Separate fallback to isolate Literal from cache effects."""
    return (a, b)


@dispatch.target_lit
def target_lit(a: Annotated[int, "m"], b: str):  # type: ignore[reportRedeclaration]
    """Overload for Annotated under `target_lit`."""
    return "annotated"


@dispatch.target_lit
def target_lit(a: Literal[1, 2], b: str):  # type: ignore[reportRedeclaration]
    """Overload for Literal values, outscoring Annotated."""
    return "literal"


def test_integration_paths() -> None:
    """Integration tests across Annotated, Optional, Type, and Literal."""
    # Matches Annotated[int, ...]
    assert target(3, "x") == "annotated"  # type: ignore[reportCallIssue]

    # Optional[int] should match None
    assert target(None, "x") == "optional"  # type: ignore[reportCallIssue]

    # Type["int"] should match int class
    assert target(int, "x") == "type_str"  # type: ignore[reportCallIssue]

    # Literal more specific than Annotated[int] when isolated from cache
    assert target_lit(1, "x") == "literal"  # type: ignore[reportCallIssue]
