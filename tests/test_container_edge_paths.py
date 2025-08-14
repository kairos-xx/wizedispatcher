from typing import Set, Tuple

from wizedispatcher import TypeMatch


def test_tuple_length_mismatch_branch() -> None:
    """Tuple arity mismatch should fail for fixed-length annotation."""
    assert TypeMatch._is_match((1, 2), Tuple[int]) is False


def test_dict_origin_false_branch_when_not_dict() -> None:
    """Non-dict value should not match a dict[K, V] annotation."""
    assert TypeMatch._is_match(123, dict[str, int]) is False


def test_set_branch_no_args_and_non_set_value() -> None:
    """Set origin checks: wrong type fails; bare Set matches any elems."""
    assert TypeMatch._is_match(123, Set[int]) is False
    assert TypeMatch._is_match({1, 2}, Set) is True
