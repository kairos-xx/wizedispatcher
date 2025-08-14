# Quickstart

This section shows how to define a base function and register
overloads using WizeDispatcher. The dispatcher selects the best
implementation at runtime based on argument types.

## Simple Function Dispatch

```python
from wizedispatcher import dispatch

# Base function used as fallback
def greet(name: object) -> str:
    return f"Hello, {name}!"

# Register an overload for strings
@dispatch.greet(name=str)
def _(name: str) -> str:
    return f"Hello, {name}, nice to meet you."

# Register an overload for integers
@dispatch.greet(name=int)
def _(name: int) -> str:
    return f"Hello, person #{name}."

# Usage
print(greet("Alice"))  # Hello, Alice, nice to meet you.
print(greet(7))        # Hello, person #7.
print(greet(3.14))     # Hello, 3.14!
```

In this example:

- We define a base function `greet` which acts as a fallback
  implementation when no overload matches the argument types.
- We register two overloads using `@dispatch.greet(...)` with type
  constraints. The decorator can take keyword arguments mapping
  parameter names to types or positional types that correspond to
  parameters in order.
- When you call `greet(...)`, the dispatcher inspects the runtime
  type of the argument and invokes the most specific matching
  overload, falling back to the base implementation if no overload
  matches.

## Dispatch on Multiple Parameters

Overloads can constrain multiple parameters. For example:

```python
@dispatch.combine(a=int, b=str)
def _(a: int, b: str) -> str:
    return f"Int={a}, Str={b}"

@dispatch.combine(a=str, b=int)
def _(a: str, b: int) -> str:
    return f"Str={a}, Int={b}"

@dispatch.combine
def combine(a: object, b: object) -> str:
    return f"Generic {a}, {b}"

print(combine(1, "x"))  # Int=1, Str=x
print(combine("y", 2))  # Str=y, Int=2
print(combine(3, 4))     # Generic 3, 4
```

## Dispatch on Methods and Properties

WizeDispatcher also supports instance methods, class methods,
static methods, and property setters. See the
[Advanced Usage](advanced.md) section for examples.

### Quickstart with Partial Hints

You can define overloads that omit some parameters; WizeDispatcher fills
missing ones from the fallback.

### Typing normalization (at a glance)

Before matching, WizeDispatcher canonicalizes common typing forms:

- PEP 604 unions are flattened and ordered (`None` first when present).
- Bare generics (e.g., `List`) gain `Any` defaults → `List[Any]`.
- `Callable[Concatenate[..., P], R]` and `Callable[P, R]` normalize to
  `Callable[..., R]`.
- `Type["int"]` resolves to `Type[int]`; actual classes are preserved in
  `Type[...]` and `Union[...]`.

This keeps overload resolution consistent across Python versions and import
styles.

```python
def concat(a: Any, b: Any, c: str = "default") -> str:
    return f"default - {a}{b}{c}"

@dispatch.concat
def _a(a: int, b: int) -> str:
    return f"_a - {a + b}{c}"  # c provided by fallback
```
