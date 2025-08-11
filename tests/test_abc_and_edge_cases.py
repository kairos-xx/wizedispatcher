from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Callable, TypeVar

from wizedispatcher import TypeMatch

T = TypeVar("T")


def test_iterable_and_sequence_and_mapping_abcs() -> None:
    assert TypeMatch._is_match([1, 2, 3], Iterable[int])
    assert not TypeMatch._is_match([1, "x"], Iterable[int])
    assert TypeMatch._is_match((1, 2, 3), Sequence[int])
    assert TypeMatch._is_match({"a": 1}, Mapping[str, int])


def test_list_t_matches_scalar_inner_type() -> None:
    # Special case: list[T] matches scalar T when value isn't list
    assert TypeMatch._is_match(5, list[int])
    assert not TypeMatch._is_match("5", list[int])


def test_callable_ellipsis_always_ok_when_callable() -> None:

    def f(x: T) -> T:
        return x

    assert TypeMatch._is_match(f, Callable[..., Any])


def test_type_origin_with_instance_returns_false() -> None:
    # If origin is Type[type] and value is an instance (not a class), return False
    assert not TypeMatch._is_match(3, type[int])
