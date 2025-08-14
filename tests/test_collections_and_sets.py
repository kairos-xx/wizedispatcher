from typing import Dict, FrozenSet, List, Set

from wizedispatcher import TypeMatch


def test_collections_and_sets_matching() -> None:
    """Match behavior across lists, sets, frozensets, and dicts."""
    assert TypeMatch._is_match([1, 2], List[int])
    assert not TypeMatch._is_match([1, "a"], List[int])
    assert TypeMatch._is_match({1, 2}, Set[int])
    assert TypeMatch._is_match(frozenset({1, 2}), FrozenSet[int])
    assert not TypeMatch._is_match({1, "a"}, Set[int])
    assert TypeMatch._is_match({"a": 1}, Dict[str, int])
