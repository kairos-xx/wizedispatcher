from typing import (
    Callable,
    ClassVar,
    Protocol,
    Type,
    TypedDict,
    runtime_checkable,
)

from wizedispatcher import TypeMatch


# TypedDict tests
class UserTD(TypedDict):
    id: int
    name: str


class UserPartial(TypedDict, total=False):
    id: int
    name: str


def test_typed_dict_matching() -> None:
    assert TypeMatch._is_match({"id": 1, "name": "a"}, UserTD)
    assert not TypeMatch._is_match({"id": "1", "name": "a"}, UserTD)
    # Partial with optional keys: allow missing
    assert TypeMatch._is_match({}, UserPartial)


# Protocol tests
class P(Protocol):

    def foo(self) -> int: ...


@runtime_checkable
class PR(Protocol):

    def foo(self) -> int: ...


class COK:

    def foo(self) -> int:
        return 1


def test_protocol_runtime_checkable() -> None:
    # Non-runtime protocol should return False
    assert TypeMatch._is_match(COK(), P) is False
    # Runtime checkable works with isinstance
    assert TypeMatch._is_match(COK(), PR) is True


# Callable signature mismatches
def ok(a: int, b: str) -> bool: ...


def bad(a: str, b: int) -> bool: ...


def test_callable_param_compatibility() -> None:
    assert TypeMatch._is_match(ok, Callable[[int, str], bool])
    assert not TypeMatch._is_match(bad, Callable[[int, str], bool])


# ClassVar unwrap and Type[T] scoring paths
class D:
    pass


class E(D):
    pass


def test_classvar_and_type_objects() -> None:
    assert TypeMatch._is_match(3, ClassVar[int])
    assert TypeMatch._is_match(E, Type[D])
    assert not TypeMatch._is_match(D, Type[E])
