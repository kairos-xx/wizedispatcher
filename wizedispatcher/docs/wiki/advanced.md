# Advanced Usage

WizeDispatcher is designed to handle a wide range of typing
scenarios. This section explores more advanced features.

## Method and Property Dispatch

You can register overloads for instance methods, class methods,
static methods, and property setters. WizeDispatcher
automatically creates a registry for each decorated attribute and
uses the instance (`self`) or class (`cls`) receiver as
appropriate. Here’s an example using a simple class:

```python
from wizedispatcher import dispatch

class Converter:
    @property
    def value(self) -> int:
        # getter
        return self._value

    @value.setter
    def value(self, val: object) -> None:
        # base setter used as fallback
        self._value = val

    @dispatch.value(value=int)
    def _(self, value: int) -> None:
        # overload for integer
        self._value = value * 10

    @dispatch.value(value=str)
    def _(self, value: str) -> None:
        # overload for string
        self._value = int(value)

c = Converter()
c.value = 3
assert c.value == 30
c.value = "7"
assert c.value == 7
```

In this example the property setter is dispatched based on the
runtime type of the `value` being assigned. Without defining a
base setter, WizeDispatcher cannot determine the correct
signature for the setter (see the troubleshooting section).

## Union, Literal, and Optional Types

WizeDispatcher supports standard typing constructs. For example:

- Use `Union[T1, T2]` to accept multiple types.
- Use `Literal[...]` to match specific values.
- Use `Optional[T]` to accept `None` or `T`.

```python
from typing import Union, Optional, Literal

@dispatch.process(value=Union[int, float])
def _(value: Union[int, float]) -> str:
    return f"Number: {value}"

@dispatch.process(value=Literal[1, 2, 3])
def _(value: int) -> str:
    return f"Small number: {value}"

@dispatch.process(value=Optional[str])
def _(value: Optional[str]) -> str:
    return "No text" if value is None else f"Text: {value}"
```

## Callable and Generic Type Support

Overloads can constrain parameters that are callables or
generic containers like `list[T]`, `tuple[T, ...]`, `dict[K, V]`,
`set[T]`, or classes implementing protocols. When no type
parameters are provided, any elements are accepted. When a type
parameter is provided, elements of the container are checked
recursively.

```python
@dispatch.handle(items=list[int])
def _(items: list[int]) -> int:
    # sum only works if items are ints
    return sum(items)

@dispatch.handle(items=dict[str, int])
def _(items: dict[str, int]) -> int:
    return sum(items.values())
```

## Ranking and Specificity

When multiple overloads could match a given call, WizeDispatcher
uses a heuristic to select the most specific one. The
`TypeMatch` algorithm assigns a specificity score based on:

- Whether the annotation is `Any`, a wildcard, or a specific type.
- Distance in the class hierarchy (closer subclasses are more
  specific).
- Number of required keys in `TypedDict`s.
- Constrained `TypeVar`s and bounds.
- Literal values and annotated elements.

The dispatcher sums the specificity scores for each parameter,
applies bonuses for explicit annotations, subtracts penalties for
missing parameters, and prefers functions with fewer variable
arguments. The overload(s) with the highest score are considered
winners; ties are resolved by registration order.

Understanding these rules helps you predict which overload will
be selected when argument types overlap.

## Using Decorator Keyword vs Positional Arguments

You can register overloads by specifying types in two ways:

- **Keyword arguments**: map parameter names to types.

  ```python
  @dispatch.fn(a=int, c=str)
  def _(a, b, c):
      ...
  ```

- **Positional arguments**: provide types in the same order as
  parameters.

  ```python
  @dispatch.fn(int, int)
  def _(a, b, c):
      ...
  ```
  In this case only `a` and `b` are constrained; `c` remains
  unconstrained.

It is valid to mix keyword arguments and default function
annotations; decorator‑provided types override annotations.

## Runtime‑Checkable Protocols and TypeVars

Overloads can require that an argument implements a runtime‑checkable
protocol. The dispatcher only treats protocols with
`_is_runtime_protocol = True` as valid. TypeVars and ParamSpecs are
supported with constraints and bounds. If a `TypeVar` has
constraints, any matching constraint passes; if it has a bound, the
bound is checked. Otherwise, it is treated as unconstrained.