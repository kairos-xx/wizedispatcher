from typing import Dict

from wizedispatcher import dispatch

calls: Dict[str, int] = {"fallback": 0, "str": 0, "intbool": 0}


def base_f(a, b) -> str:
    """Fallback path; increments fallback call counter."""
    _ = (a, b)
    calls["fallback"] += 1
    return "fallback"


@dispatch.base_f(a=str)
def _(a, b) -> str:
    """Overload when first argument is a string; count calls."""
    _ = (a, b)
    calls["str"] += 1
    return "str"


@dispatch.base_f(int, bool)
def _(a, b) -> str:
    """Overload when (int, bool); increments respective counter."""
    _ = (a, b)
    calls["intbool"] += 1
    return "intbool"


def test_free_function_overloads_and_cache() -> None:
    """Verify overload resolution and basic hot-path cache behavior."""
    assert base_f("x", 1) == "str"
    assert base_f("y", 2) == "str"
    assert base_f(3, True) == "intbool"
    assert base_f(4, False) == "intbool"
    assert base_f(3.3, object()) == "fallback"
    assert calls["fallback"] >= 1
    assert calls["str"] >= 1
    assert calls["intbool"] >= 1
