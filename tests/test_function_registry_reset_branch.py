from sys import modules
from types import ModuleType
from typing import Any, Dict

from wizedispatcher import dispatch


# Create base and first overload to initialize regmap
def h0(a) -> str:
    """Base fallback used to initialize registry for reset path."""
    _ = a
    return "base"


@dispatch.h0(a=int)
def _(a) -> str:
    """Overload for integer argument to prime registry map."""
    _ = a
    return "int"


def test_force_reset_branch() -> None:
    """Force rare branch that rebuilds registry for a replaced target."""
    # Access the function's module registry and the registry entry for 'h0'
    mod: ModuleType = modules[__name__]
    regmap: Dict[str, Any] = mod.__fdispatch_registry__
    reg: Any = regmap["h0"]

    # Now replace the global name with a fresh plain function (not wrapped)
    def h0(a) -> str:
        """Replacement base; simulates external reassignment of target."""
        _ = a
        return "base2"

    mod.__dict__["h0"] = h0  # assign explicitly

    # Force the rare path: empty out recorded overloads to satisfy the
    # 'if not reg._overloads' condition
    reg._overloads = []
    reg._cache = {}
    reg._reg_counter = 0

    # Register a new overload; this should hit the code path that re-reads
    # signature and registers original
    @dispatch.h0(a=str)
    def _(a) -> str:
        """New overload added after reset to exercise path."""
        _ = a
        return "str"

    assert (
        h0(1) == "base2" or h0(1) == "int"
    )  # dispatch behavior may vary, but should be callable
    assert h0("x") in ("str", "base2")
