from typing import (
    Annotated,
    Any,
    Callable,
    ClassVar,
    List,
    Literal,
    Tuple,
    Type,
    Union,
)

from wizedispatcher import TypeMatch


def test_specificity_covers_many_branches() -> None:
    """Exercise many scoring branches with diverse typing hints."""
    v: int = 3
    # Top types
    assert TypeMatch._type_specificity_score(v, Any) == 0
    # NewType path is hard to construct here; cover others:
    TypeMatch._type_specificity_score({"a": 1}, dict[str, int])  # Mapping
    TypeMatch._type_specificity_score((1, 2, 3), Tuple[int, ...])
    TypeMatch._type_specificity_score([1, 2, 3], List[int])
    TypeMatch._type_specificity_score(3, Literal[3])
    TypeMatch._type_specificity_score(3, Annotated[int, "m"])
    TypeMatch._type_specificity_score(3, ClassVar[int])
    TypeMatch._type_specificity_score(3, Union[int, str])
    TypeMatch._type_specificity_score(int, Type[int])

    def f(a: int, b: str) -> bool:  # type: ignore[reportUnusedParameter]
        ...

    TypeMatch._type_specificity_score(f, Callable[[int, str], bool])
    # Fallback plain class
    TypeMatch._type_specificity_score(3, int)
