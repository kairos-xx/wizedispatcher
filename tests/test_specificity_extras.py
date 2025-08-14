from typing import Dict, List, Sequence, Tuple, TypedDict

from wizedispatcher import TypeMatch


class TD(TypedDict):
    """Simple TypedDict used for specificity scoring examples."""

    a: int
    b: str


def test_specificity_negative_and_bare_aliases_and_typeddict() -> None:
    """Cover negative penalties, bare aliases, and TypedDict scoring."""
    # Bare aliases
    TypeMatch._type_specificity_score((), Tuple)
    TypeMatch._type_specificity_score([], List)
    TypeMatch._type_specificity_score({}, Dict)
    TypeMatch._type_specificity_score(set(), set)
    TypeMatch._type_specificity_score({}, dict)

    # Negative paths (-50 penalties)
    TypeMatch._type_specificity_score(123, dict[str, int])
    TypeMatch._type_specificity_score(123, Sequence[int])
    TypeMatch._type_specificity_score(123, tuple[int, str])

    # TypedDict scoring
    TypeMatch._type_specificity_score({"a": 1, "b": "x"}, TD)
