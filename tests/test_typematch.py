import typing as t
from typing import (
    Annotated,
    Any,
    ClassVar,
    Dict,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
)

from wizedispatcher import WILDCARD, TypeMatch


def test_any_and_wildcard_match() -> None:
    """Top types Any/object and custom WILDCARD should all match."""
    assert TypeMatch._is_match(123, Any)
    assert TypeMatch._is_match("x", object)
    assert TypeMatch._is_match("x", WILDCARD)


def test_union_and_optional() -> None:
    """Union/Optional accept appropriate values; reject mismatches."""
    assert TypeMatch._is_match(1, Union[int, str])
    assert TypeMatch._is_match(None, Optional[int])
    assert not TypeMatch._is_match(1.2, Optional[int])


def test_annotated_and_classvar() -> None:
    """Annotated unwraps to base; ClassVar unwraps to inner type."""
    assert TypeMatch._is_match(3, Annotated[int, "meta"])
    assert TypeMatch._is_match(3, ClassVar[int])


def test_literal_values() -> None:
    """Literal matches enumerated values and rejects others."""
    assert TypeMatch._is_match(2, Literal[1, 2, 3])
    assert not TypeMatch._is_match(4, Literal[1, 2, 3])


def test_iterables_sequences_and_mappings() -> None:
    """Containers: lists, tuples, and mappings with element typing."""
    assert TypeMatch._is_match([1, 2, 3], list[int])
    assert TypeMatch._is_match((1, 2, 3), Tuple[int, int, int])
    assert TypeMatch._is_match((1, 2, 3), Tuple[int, ...])
    assert not TypeMatch._is_match((1, "a"), Tuple[int, ...])
    assert TypeMatch._is_match({"a": 1}, Dict[str, int])
    assert not TypeMatch._is_match({"a": 1}, Dict[str, str])


def test_callable_param_checking():
    """Callable param type checking for signature-compatible callables."""

    def f(a: int, b: str) -> bool: ...

    assert TypeMatch._is_match(f, t.Callable[[int, str], bool])

    # Accept unknown/opaque callables
    class C:

        def __call__(self, *args, **kwargs): ...

    assert TypeMatch._is_match(C(), t.Callable[..., Any])


def test_type_objects_against_Type():
    """Type[T] matching against class objects should respect T."""
    assert TypeMatch._is_match(int, Type[int])
    assert not TypeMatch._is_match(int, Type[str])


def test_specificity_scores_ordering():
    """More specific should outrank Any/object in scoring."""
    # More specific should outrank Any / object
    s_int: int = TypeMatch._type_specificity_score(3, int)
    s_any: int = TypeMatch._type_specificity_score(3, Any)
    s_obj: int = TypeMatch._type_specificity_score(3, object)
    assert s_int > s_any and s_int > s_obj
