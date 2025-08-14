# Behavior-oriented tests for internal core behaviors without referencing line numbers
from typing import Any, Callable, Dict, List

from wizedispatcher import WizeDispatcher
from wizedispatcher.core import TypeMatch


def test_type_match_rejects_non_mapping_for_dict_annotations() -> None:
    """Non-mapping value should not match Dict[str, int]."""
    assert TypeMatch._is_match("not_a_dict", Dict[str, int]) is False


def test_scoring_handles_unannotated_parameters_gracefully() -> None:
    """Scoring must handle unannotated parameters without errors."""

    # Create a function with one annotated and one unannotated parameter
    def func(annotated: int, unannotated):
        return annotated

    # Competing overload specifying both annotations
    def func_overload(annotated: int, unannotated: str):
        return annotated

    # Use TypeMatch to exercise scoring and hint resolution without wiring
    winners: List[Callable] = TypeMatch(
        {"annotated": 10, "unannotated": "x"}, [func, func_overload]
    )
    assert winners


def test_adapter_global_backup_and_restore() -> None:
    """Adapter should backup and restore globals around invocation."""

    # Function where a name in globals is overwritten and restored
    def func_with_global(a: int, gname: str) -> tuple[int, str]:
        return (a, gname)

    # Pre-create global to force backup/restore behavior
    func_with_global.__globals__["gname"] = "preexisting"

    try:
        adapter, _ = WizeDispatcher._BaseRegistry._make_adapter(
            func_with_global
        )
        result: Any = adapter(a=1, gname="injected")
        assert result == (1, "injected")
        # Ensure restored
        assert func_with_global.__globals__["gname"] == "preexisting"
    finally:
        func_with_global.__globals__.pop("gname", None)


def test_invoke_selected_calls_wrapped_when_no_wrapper_present() -> None:
    """_invoke_selected fast path when chosen has no __wrapped__."""

    # Build a minimal registry and call _invoke_selected with a plain function
    def base(a: int) -> int:
        return a + 1

    # Create a minimal _BaseRegistry via _FunctionRegistry
    reg: WizeDispatcher._FunctionRegistry = WizeDispatcher._FunctionRegistry(
        target_name="tmp", original=base
    )
    # Bind once to produce BoundArguments
    bound, _ = reg._bind(instance=None, args=(1,), kwargs={})
    # Since 'chosen' is a plain function (no __wrapped__), the fast path should be used
    assert reg._invoke_selected(chosen=base, bound=bound) == 2


def test_function_registry_initialization_on_first_register() -> None:
    """First register initializes function registry without errors."""
    dispatcher: WizeDispatcher = WizeDispatcher()

    def new_fn(x: int) -> str:
        return str(x)

    dispatcher.register(
        func=new_fn,
        type_map={"x": int},
        dec_keys=frozenset(),
        is_original=True,
    )
    # If it didn't raise, initialization path worked
    assert callable(new_fn)
