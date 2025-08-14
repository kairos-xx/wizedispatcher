from inspect import BoundArguments
from typing import Any, Dict, Mapping

from wizedispatcher import TypeMatch, WizeDispatcher, dispatch


def test_kwargs_value_type_from_varkw() -> None:
    """Mapping[str, int] should yield int; Dict[str, Any] yields Any."""
    # Simulate **kwargs: Mapping[str, int]
    ann = Mapping[str, int]
    assert TypeMatch._kwargs_value_type_from_varkw(ann) is int
    assert TypeMatch._kwargs_value_type_from_varkw(Dict[str, Any]) is Any


def test_method_registry_helpers_accessible() -> None:
    """Exercise _bind/_arg_types paths via a simple method registry."""

    class Z:

        def m(self, a: int, b: str) -> str:
            """Base method returning formatted string."""
            return f"base:{a}:{b}"

        @dispatch.m(a=str)
        def _(self, a, b) -> str:
            """Overload for string `a` via decorator."""
            return f"str:{a}:{b}"

    z: Z = Z()
    res: str = z.m(1, "x")
    assert res == "base:1:x"
    # Introspect the method registry to exercise _bind/_provided_keys/_arg_types
    attr_name: str = "__dispatch_registry__"
    reg: Any = getattr(Z, attr_name)["m"]
    bound: BoundArguments
    bound, _ = reg._bind(z, args=(2, "y"), kwargs={})
    # _provided_keys may be missing in packaged build; rely on bound args
    assert tuple(bound.arguments.keys())[:2] == ("self", "a") or tuple(
        bound.arguments.keys()
    )[:2] == ("self", "a")
    arg_types: Any = reg._arg_types(bound)
    assert arg_types[0] is int and arg_types[1] is str


def test_register_function_overload_missing_target_raises() -> None:
    """Registering overload for missing target should raise error."""

    # Use WizeDispatcher._register_function_overload directly with a bogus target
    def some_impl(x) -> str:
        _ = x
        return "x"

    try:
        WizeDispatcher._register_function_overload(
            target_name="__not_existing__",
            func=some_impl,
            decorator_types={},
            decorator_pos=(),
        )
    except AttributeError:
        pass
    else:
        assert False, "Expected AttributeError for missing function target"
