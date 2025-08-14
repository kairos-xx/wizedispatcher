# TypingNormalize

`TypingNormalize` converts type‑like inputs into canonical `typing.*` shapes so
WizeDispatcher can match and score overloads consistently across Python
versions and import styles.

## Why normalization?

Python offers multiple spellings for similar type ideas (`Union` vs `|`,
`collections.abc.Callable` vs `typing.Callable`, builtins like `list[int]`
vs `typing.List[int]`). Normalization eliminates spelling differences,
flattening and mapping to a stable form that the dispatcher understands.

## Behavior guarantees

- Unions
  - Flattens nested unions; deduplicates members
  - Orders `None` first when present (`Optional[T]` ≡ `Union[None, T]`)
  - Any union containing `Any` reduces to `Any`
- Generics and collections
  - PEP 585 builtins and ABCs map to `typing.*`
  - Bare generics gain `Any` defaults (e.g., `List` → `List[Any]`)
  - Container element types are preserved recursively
- Callable
  - Preserves origin: `Callable[[...], R]` vs `Callable[..., R]`
  - `ParamSpec`/`Concatenate` collapse to `Callable[..., R]`
- `Type[...]`
  - `Type["int"]` and `Type[ForwardRef("int")]` resolve to `Type[int]`
  - `Type[CustomClass]` preserves the actual class object
- Special typing forms
  - `Annotated`/`Literal`/`ClassVar` return subscripted forms unchanged
  - `TypeVar` with constraints becomes their union; with bound → bound;
    unconstrained becomes `Any`
- Strings and forward refs
  - Strings and `ForwardRef` are evaluated against a safe module/global map

Idempotency: applying `TypingNormalize` twice yields an equivalent object.

## API

```
TypingNormalize(tp: object) -> object
```

- **tp**: Any annotation or type‑like object (including strings and
  `ForwardRef`).
- **returns**: Canonical `typing.*` object or original class when that is the
  canonical representation.

## Examples

```python
from typing import Callable, Concatenate, Optional, Type, Union
from wizedispatcher.typingnormalize import TypingNormalize

# Unions
assert repr(TypingNormalize(Union[int, str | None])) \
    == "typing.Union[NoneType, int, str]"

# Bare/builtin generics
assert repr(TypingNormalize(list)) == "typing.List[typing.Any]"

# Callable shapes
assert repr(TypingNormalize(Callable[[int, str], bool])) \
    == "typing.Callable[[int, str], bool]"

P = typing.ParamSpec("P")
assert repr(TypingNormalize(Callable[Concatenate[int, P], str])) \
    == "typing.Callable[..., str]"

# Type[...] with strings and classes
class C: ...
assert repr(TypingNormalize(Type["int"])) == "typing.Type[int]"
assert repr(TypingNormalize(Type[C])).startswith("typing.Type[")
```

## How it is used internally

`TypeMatch` and `WizeDispatcher` call `TypingNormalize` after resolving string
and forward references in annotations. This ensures compatibility checks and
specificity scoring operate on canonical shapes.

You generally do not need to call `TypingNormalize` directly unless building
tooling or debugging type behavior.

