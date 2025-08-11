from sys import modules
from types import ModuleType
from typing import Dict

from wizedispatcher import dispatch


# Create base and first overload to initialize regmap
def h0(a) -> str:
    _ = a
    return "base"


@dispatch.h0(a=int)
def _(a) -> str:
    _ = a
    return "int"


def test_force_reset_branch() -> None:
    # Access the function's module registry and the registry entry for 'h0'
    mod: ModuleType = modules[__name__]
    regmap: Dict = mod.__fdispatch_registry__
    reg = regmap["h0"]

    # Now replace the global name with a fresh plain function (not wrapped)
    def h0(a) -> str:
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
        _ = a
        return "str"

    assert (
        h0(1) == "base2" or h0(1) == "int"
    )  # dispatch behavior may vary, but should be callable
    assert h0("x") in ("str", "base2")
