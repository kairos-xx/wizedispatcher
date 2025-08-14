from collections.abc import Callable as AbcCallable
from typing import (
    Annotated,
    Any,
    Callable,
    ClassVar,
    Concatenate,
    Literal,
    Optional,
    ParamSpec,
    Type,
    Union,
    get_args,
    get_origin,
)

from wizedispatcher import TypingNormalize


def test_special_forms_preserved_with_args() -> None:
    """Annotated, Literal, and ClassVar should keep origins and args."""
    tn_annotated: Type = TypingNormalize(Annotated[int, "m"])  # type: ignore[reportInvalidTypeForm]
    assert get_origin(tn_annotated) is Annotated
    assert get_args(tn_annotated) == (int, "m")

    tn_literal: Type = TypingNormalize(Literal[1, 2, 3])  # type: ignore[reportInvalidTypeForm]
    assert get_origin(tn_literal) is Literal
    assert get_args(tn_literal) == (1, 2, 3)

    tn_classvar: Type = TypingNormalize(ClassVar[int])  # type: ignore[reportInvalidTypeForm]
    assert get_origin(tn_classvar) is ClassVar
    assert get_args(tn_classvar) == (int,)


def test_union_flattening_and_any_collapse() -> None:
    """Unions flatten; Any collapses union to Any; None ordered first."""
    # None first and flatten nested
    tn: Type = TypingNormalize(Union[Union[int, str], Optional[bytes]])  # type: ignore[reportInvalidTypeForm]
    assert get_origin(tn) is Union
    assert get_args(tn) == (type(None), int, str, bytes)

    # Any collapses union to Any
    tn_any: Type = TypingNormalize(Union[int, Any])  # type: ignore[reportInvalidTypeForm]
    assert tn_any is Any


def test_builtins_to_typing_defaults() -> None:
    """Bare builtins gain Any defaults in their typing equivalents."""
    # Bare builtins gain Any defaults
    assert repr(TypingNormalize(list)) == "typing.List[typing.Any]"
    assert repr(TypingNormalize(dict)) == "typing.Dict[typing.Any, typing.Any]"
    assert repr(TypingNormalize(tuple)) == "typing.Tuple[typing.Any, ...]"
    assert repr(TypingNormalize(type)) == "typing.Type[typing.Any]"


def test_callable_param_forms() -> None:
    """Callable params preserved; ParamSpec/Concatenate collapse."""
    P = ParamSpec("P")

    # Concrete params are preserved
    c: Type = TypingNormalize(Callable[[int, str], bool])  # type: ignore[valid-type]
    # get_origin returns collections.abc.Callable for typing.Callable entries
    assert get_origin(c) is AbcCallable
    assert get_args(c) == ([int, str], bool)
    # ParamSpec/Concatenate collapse to Callable[..., R]
    c_any = TypingNormalize(Callable[Concatenate[int, P], str])  # type: ignore[misc]
    assert get_origin(c_any) is AbcCallable
    params, ret = get_args(c_any)
    assert params is Ellipsis and ret is str


def test_string_and_forwardref_in_Type() -> None:
    """String Type arguments should resolve to actual types."""
    t_int: Type = TypingNormalize(Type["int"])  # type: ignore[valid-type]
    assert get_origin(t_int) is type and get_args(t_int) == (int,)

    t_bytes: Type = TypingNormalize(Type["bytes"])  # type: ignore[valid-type]
    assert get_origin(t_bytes) is type and get_args(t_bytes) == (bytes,)


def test_preserve_runtime_class_objects() -> None:
    """Type[Custom] preserves actual runtime class objects."""

    class Custom:
        pass

    tn: Type = TypingNormalize(Type[Custom])  # type: ignore[reportInvalidTypeForm]
    assert get_origin(tn) is type and get_args(tn) == (Custom,)
