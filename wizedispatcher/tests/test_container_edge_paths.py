from typing import Set, Tuple

from wizedispatcher import TypeMatch


def test_tuple_length_mismatch_branch() -> None:
    assert TypeMatch._is_match((1, 2), Tuple[int]) is False


def test_dict_origin_false_branch_when_not_dict() -> None:
    assert TypeMatch._is_match(123, dict[str, int]) is False


def test_set_branch_no_args_and_non_set_value() -> None:
    assert (
        TypeMatch._is_match(123, Set[int]) is False
    )  # not a set -> early False at 266
    assert TypeMatch._is_match({1, 2}, Set) is True  # no args -> True at 268
