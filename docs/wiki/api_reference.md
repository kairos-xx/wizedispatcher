# API Reference

This section documents the public API of WizeDispatcher. For more
details, refer to the docstrings in the source code.

## `wizedispatcher.TypeMatch`

`TypeMatch` provides helper methods for resolving annotations,
checking whether a runtime value matches a type hint, computing
specificity scores, and selecting the best overload among
candidates. It is also callable and returns a list of winning
callables given a mapping of parameter names to runtime values and a
list of candidates.

### Methods

| Method | Description |
|---|---|
| `_resolve_hints(func, g=None, localns=None)` | Resolve a callable’s annotations to runtime types using safe global and local mappings. |
| `_resolve_hint(hint)` | Resolve a string or `ForwardRef` into a runtime type (after normalization). |
| `is_match(value, hint)` | Check if a runtime value conforms to a type hint. Supports `Any`, `object`, `Union`, `Literal`, container types, callables, protocols, `TypeVar`, and more. Returns a boolean. |
| `type_specificity_score(value, hint)` | Compute a heuristic specificity score for a value vs. a hint; higher means more specific. Used to rank overloads. |
| `TypeMatch(match: Dict[str, object], options: List[Callable])` | Callable interface; given a mapping of parameter names to values and a list of candidate functions, return the subset of winners (highest‑score functions). |

## `wizedispatcher.WizeDispatcher`

`WizeDispatcher` creates namespaced decorators for registering
function and method overloads. A global instance `dispatch` is
exported for convenience. You typically use `@dispatch.target_name` to
register overloads for `target_name`.

### Methods and Attributes

| Method/Attribute | Description |
|---|---|
| `dispatch.<function>` | Access attribute on `dispatch` to return a decorator factory for registering overloads on the function `function`. |
| `_param_order(sig, skip_first)` | Utility to compute the dispatch parameter order from a signature. |
| `_normalize_expected(t)` | Normalize typing constructs into runtime‑checkable targets. Internally relies on `TypingNormalize`. |
| `_register_function_overload(target_name, func, decorator_types, decorator_pos)` | Register an overload for a free function in its module. |
| `_resolve_hints(func, g=None, localns=None)` | Resolve annotations for a function with safe globals/locals. |
| `_merge_types(order, decorator_types, fn_ann)` | Merge decorator‑provided types with function annotations for the parameter order. |
| `_OverloadDescriptor` | Descriptor used internally to collect overloads when decorating methods. |

### `dispatch` Instance

The module exports a `dispatch` instance that you use to decorate
functions, methods, class methods, static methods, or property
setters. Access attributes of `dispatch` to create decorators for
each target.

Example:

```python
from wizedispatcher import dispatch

@dispatch.process(int)
def process(value: int) -> str:
    return f"Processing {value}"
```

This registers an overload for `process` with a positional type
constraint.

## Base Types and Constants

- `wizedispatcher.WILDCARD` – sentinel used internally to
  represent an unconstrained type.

## `wizedispatcher.TypingNormalize`

`TypingNormalize(tp: object) -> object` converts any type-like expression into a
canonical `typing.*` form suitable for downstream checks and pretty‑printing.

Highlights:

- Collapses `Union`/PEP 604 unions, orders `None` first, and reduces unions
  containing `Any` to `Any`.
- Maps PEP 585 builtins/ABCs and concrete collections to `typing.*`.
- Adds `Any` defaults to bare generics.
- Preserves callable origins (`Callable[[...], R]` vs `Callable[..., R]`).
- Simplifies `Callable[Concatenate[..., P], R]` and `Callable[P, R]` to
  `Callable[..., R]`.
- Resolves `Type["name"]` and `Type[ForwardRef("name")]` to real types while
  preserving actual classes.

Example:

```python
from typing import Callable, Concatenate, Optional, Type, Union
from wizedispatcher.typingnormalize import TypingNormalize

assert repr(TypingNormalize(Union[int, str | None])) \
    == "typing.Union[NoneType, int, str]"
assert repr(TypingNormalize(Callable[Concatenate[int, ...], str])) \
    == "typing.Callable[..., str]"
assert repr(TypingNormalize(Type["int"])) == "typing.Type[int]"
```

Signature:

- Parameters: `tp: object` – any annotation or type‑like object, including
  strings and `ForwardRef`.
- Returns: `object` – a canonical `typing.*` shape or original class when that
  is the canonical representation.

Notes:

- Idempotent: `TypingNormalize(TypingNormalize(tp))` yields an equivalent
  object.
- Used internally by `TypeMatch` and `WizeDispatcher` before compatibility and
  scoring; you typically do not need to call it directly.
- See the dedicated wiki page for a comprehensive feature list and caveats:
  [TypingNormalize](typingnormalize.md).