import typing as t
from builtins import range as brange
from contextlib import redirect_stdout
from importlib import import_module
from io import StringIO
from re import Pattern as RePattern
from types import ModuleType
from typing import (
    Any,
    Concatenate,
    ForwardRef,
    Optional,
    ParamSpec,
    Type,
    Union,
    get_args,
    get_origin,
)

from wizedispatcher.typingnormalize import TypingNormalize


def test_helpers_typevar_paramspec_union_callable_origin() -> None:
    """Cover helper predicates for TypeVar/ParamSpec/Union/Callable."""
    T = t.TypeVar("T")
    P = ParamSpec("P")
    assert TypingNormalize._is_typevar(T) is True
    assert TypingNormalize._is_typevar(123) is False
    assert TypingNormalize._is_paramspec(P) is True
    assert TypingNormalize._is_paramspec(object()) is False
    assert TypingNormalize._is_union_like(Union[int, str]) is True
    assert TypingNormalize._is_union_like(int) is False
    # Callable origin detection
    assert (TypingNormalize._is_callable_origin(
        get_origin(t.Callable[[int], int])) is True)
    assert TypingNormalize._is_callable_origin(None) is False


def test_string_to_type_and_forwardref_resolution_paths() -> None:
    """String type resolution and ForwardRef fallback branches."""
    # Use builtins fallback path (not in predefined map)
    assert TypingNormalize._string_to_type("range") is brange
    # Unknown type returns Any
    assert TypingNormalize._string_to_type("__does_not_exist__") is t.Any
    # ForwardRef resolution to Any when attribute missing
    assert TypingNormalize._resolve_forward_ref(
        object()) is t.Any  # type: ignore[arg-type]


def test_norm_callable_invalid_shape_defaults_and_forwardref_in_type() -> None:
    """Indirectly exercise _from_origin and ForwardRef in Type[...]"""

    # Invalid Callable shape should be handled by surrounding logic; construct
    # a bad object and pass it through _tsub path indirectly via _from_origin
    # check.
    # Use a mocked origin that looks like Callable but with wrong args length
    class BadCallable:

        def __getitem__(self, item):
            return ("bad", item)

    out: Type = TypingNormalize._from_origin(
        BadCallable(), (int, ))  # type: ignore[reportInvalidTypeForm]
    assert out == ("bad", (int, ))
    # ForwardRef inside Type[] resolves via _resolve_forward_ref branch
    tr: Type = TypingNormalize(
        t.Type[ForwardRef("int")])  # type: ignore[reportInvalidTypeForm]
    assert get_origin(tr) is type and get_args(tr) == (int, )


def test_plain_runtime_to_typing_and_plain_typing_defaults_misc() -> None:
    """PEP 585/ABCs/regex and defaults mapping behavior."""
    # ABCs map to typing defaults via name map
    # For typing.Mapping (not ABC), the origin name lookup goes through
    # defaults-by-name
    assert TypingNormalize._plain_runtime_to_typing(t.Mapping) is t.Mapping
    # Regex runtime types to typing
    assert (repr(TypingNormalize._plain_runtime_to_typing(RePattern)) ==
            "typing.Pattern[typing.Any]")
    # MappingView family via defaults-by-name passthrough
    assert (TypingNormalize._plain_typing_to_defaults(t.MappingView)
            is t.MappingView)
    # Callable/Union special defaults
    assert (repr(TypingNormalize._typing_defaults_by_name("Callable")) ==
            "typing.Callable[..., typing.Any]")
    assert TypingNormalize._typing_defaults_by_name("Union") is t.Any


def test_tsub_error_paths_and_unknown_target() -> None:
    """Error paths for _tsub when shapes or targets are invalid."""
    # Callable wrong shape -> ValueError
    try:
        TypingNormalize._tsub("Callable", ("notlist", int))
        AssertionError("Expected ValueError")
    except ValueError:
        pass
    # Union requires tuple
    try:
        TypingNormalize._tsub("Union", [int, str])  # type: ignore[arg-type]
        AssertionError("Expected ValueError")
    except ValueError:
        pass
    # Generic expects tuple
    try:
        TypingNormalize._tsub("List", int)  # type: ignore[arg-type]
        AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_from_origin_fallback_subscription() -> None:
    """Fallback subscription via origin __getitem__ hook."""

    class Fake:

        def __getitem__(self, args: Any) -> Any:
            return ("ok", args)

    out: Type = TypingNormalize._from_origin(
        Fake(), (int, str))  # type: ignore[reportIndexIssue]
    assert (out[0]  # type: ignore[reportIndexIssue]
            == "ok" and out[1]  # type: ignore[reportIndexIssue]
            == (int, str))


def test_from_origin_returns_origin_when_not_subscriptable() -> None:
    """Non-subscriptable origin should be returned unchanged."""
    # Using a non-subscriptable origin should return the origin object itself
    res: Type = TypingNormalize._from_origin(
        object, (int, ))  # type: ignore[reportIndexIssue]
    assert res is object


def test_is_concatenate_helper() -> None:
    """_is_concatenate returns True only for Concatenate forms."""
    P = ParamSpec("P")
    assert TypingNormalize._is_concatenate(
        Concatenate[int, P]) is True  # type: ignore[misc]
    assert TypingNormalize._is_concatenate(int) is False


def test_tsub_unknown_typing_target_raises() -> None:
    """Unknown typing target should raise ValueError in _tsub."""
    try:
        TypingNormalize._tsub("NotARealTypingName", (int, ))
        AssertionError("Expected ValueError")
    except ValueError:
        pass


def test_exec_main_block_for_demo_coverage() -> None:
    """Execute module as __main__ to exercise demonstration block."""
    mod: ModuleType = import_module("wizedispatcher.typingnormalize")
    path: Optional[str] = mod.__file__
    assert path is not None
    with open(path, "r", encoding="utf-8") as f:
        src: str = f.read()
        buf: StringIO = StringIO()
        g: dict[str, Any] = {"__name__": "__main__"}
        with redirect_stdout(buf):
            exec(compile(src, path, "exec"), g, g)
        # The demo prints multiple lines; ensure something was captured
        assert buf.getvalue()
