from collections.abc import Callable
from typing import List, Mapping, TypeVar

from wizedispatcher import TypeMatch


def test_typevar_constraints_and_bounds_specificity() -> None:
    """TypeVar with constraints and bound should be scorable."""
    T = TypeVar("T", int, str)
    U = TypeVar("U", bound=int)
    # Just ensure these execute; relative ordering not crucial here
    TypeMatch._type_specificity_score(3, T)
    TypeMatch._type_specificity_score(3, U)


def test_typematch_empty_and_kwargs_value_inference() -> None:
    """Empty options return []; **kwargs Mapping guides unknown keys."""
    # Case 1: empty options -> returns []
    assert TypeMatch({"x": 1}, []) == []

    # Case 2: candidate has **kwargs Mapping[str, int] and match has an
    # unknown key
    def f(a, **kwargs: Mapping[str, int]) -> str:
        """Accept extras via Mapping[str, int] in **kwargs."""
        _ = (a, kwargs)
        return "ok"

    # Unknown key 'k' should look at **kwargs value type (int) and match True
    winners: List[Callable] = TypeMatch({"k": 1}, [f])
    assert winners and winners[0] is f
