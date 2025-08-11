from collections import deque
from typing import Deque, NewType

from wizedispatcher import TypeMatch


def test_newtype_specificity_and_match_paths() -> None:
    MyInt = NewType("MyInt", int)
    # _is_match should treat NewType as its supertype
    assert TypeMatch._is_match(3, MyInt)
    # Specificity should follow supertype path + 1
    s: int = TypeMatch._type_specificity_score(3, MyInt)
    assert isinstance(s, int)


def test_generic_origin_fallback_instance_check() -> None:
    d: Deque = deque([1, 2, 3])
    assert TypeMatch._is_match(d, Deque[int])
