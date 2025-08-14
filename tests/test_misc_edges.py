from typing import ForwardRef
from typing import Iterable as TIterable

from wizedispatcher import TypeMatch


def test_resolve_hint_string_and_forwardref() -> None:
    """Resolve string and ForwardRef to concrete types."""
    assert TypeMatch._resolve_hint("int") is int
    fr: ForwardRef = ForwardRef("int")
    assert TypeMatch._resolve_hint(fr) is int


def test_iterable_without_args_defaults_true() -> None:
    """Bare Iterable origin should accept list; set origin mismatch fails."""
    assert TypeMatch._is_match([1, 2, 3], TIterable)
    # mismatch branch for origin in (set, frozenset) when wrong outer type
    assert not TypeMatch._is_match([1, 2, 3], set[int])
