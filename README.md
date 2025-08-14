<div align="center">
  <img src="https://github.com/kairos-xx/wizedispatcher/raw/main/resources/icon_raster.png" alt="WizeDispatcher Logo" width="140"/>
  <h1>WizeDispatcher</h1>
  <p><em>Runtime multiple dispatch for Python — precise, fast, and ergonomic.<br/>Typed overloads for functions, methods, and <strong>property setters</strong>.</em></p>

  <a href="https://replit.com/@kairos/wizedispatcher">
    <img src="https://github.com/kairos-xx/wizedispatcher/raw/main/resources/replit.png" alt="Try it on Replit" width="150"/>
  </a>
</div>

> Zero dependencies · Python 3.8+ · Works with `typing`/PEP 604 · Structure-aware caching · Canonical typing normalization

---

## Table of Contents

1. [Why WizeDispatcher](#1-why-wizedispatcher)  
2. [Quick Start](#2-quick-start)  
3. [Declaring Overloads](#3-declaring-overloads)  
   - [Precedence of Types](#31-precedence-of-types)  
   - [Positional vs Keyword Decorators](#32-positional-vs-keyword-decorators)  
   - [Partial Specs & Fallback Fill-In](#33-partial-specs--fallback-fill-in)  
4. [Dispatch Semantics](#4-dispatch-semantics)  
   - [Compatibility Filtering](#41-compatibility-filtering)  
   - [Specificity Scoring](#42-specificity-scoring)  
    - [Structure-Aware Caching](#43-structure-aware-caching)  
    - [Globals Injection for Extras](#44-globals-injection-for-extras)  
5. [Using With Methods](#5-using-with-methods)  
   - [Instance Methods](#51-instance-methods)  
   - [Class & Static Methods](#52-class--static-methods)  
6. [Property Setter Dispatch](#6-property-setter-dispatch)  
7. [Varargs & Kwargs Patterns](#7-varargs--kwargs-patterns)  
8. [Typing Power-Ups](#8-typing-power-ups)  
   - [Typing normalization & TypingNormalize](#81-typing-normalization--typingnormalize)  
9. [Performance](#9-performance)  
10. [Comparisons](#10-comparisons)  
11. [Use Cases](#11-use-cases)  
12. [API Notes & Best Practices](#12-api-notes--best-practices)  
13. [Demos](#13-demos)  
14. [Installation](#14-installation) · [License](#15-license)

---

## 1) Why WizeDispatcher

- **Precise**: Honors modern typing (`Union`/PEP 604, `Annotated`, `Literal`, `Type[T]`, containers, callable shapes, TypedDict-like, runtime protocols).  
- **Fast**: One-time selection per call shape; subsequent calls hit a **structure-aware cache**.  
- **Ergonomic**: Simple decorators, no metaclass tricks, no custom dunder protocols.  
- **Complete**: Works on free functions, methods, class/static methods, and **property setters**.  
- **Deterministic**: Hard type checks first, then a transparent specificity score.  
- **Consistent**: Built-in typing normalization canonicalizes hints (including string `Type["int"]` and `ForwardRef`) so selection works uniformly across Python versions.

[Back to top ↑](#table-of-contents)

---

## 2) Quick Start

```python
from wizedispatcher import dispatch

# Fallback (kept as a callable and used when no overload matches)
def greet(name: object) -> str:
    return f"Hello, {name}!"

# Overload using keyworded decorator args
@dispatch.greet(name=str)
def _(name: str) -> str:
    return f"Hello, {name}, nice to meet you."

# Overload using positional decorator args (map by parameter order)
@dispatch.greet(str, int)
def _(name, age) -> str:
    return f\"{name} is {age} years old\"

print(greet(\"Ada\"))     # → str overload
print(greet(\"Bob\", 30)) # → (str, int) overload
```

[Back to top ↑](#table-of-contents)

---

## 3) Declaring Overloads

### 3.1 Precedence of Types

Effective type per parameter is resolved in this order:

**Decorator args** ➜ **Overload annotations** ➜ **Fallback annotations** ➜ **Wildcard**

```python
def f(a: int, b: str) -> None: ...    # fallback

@dispatch.f               # uses overload annotations
def _(a: int, b: bytes) -> None:    # effective: a=int, b=bytes
    ...

@dispatch.f(b=bytes)      # decorator overrides only 'b'
def _(a: int, b: str) -> None:    # effective: a=int (fn), b=bytes (decorator)
    ...

@dispatch.f(int, bytes)   # positional mapping by parameter order
def _(a, b) -> None:
    ...
```

### 3.2 Positional vs Keyword Decorators

- **Positional**: `@dispatch.func(int, str)` → (`param0=int`, `param1=str`, …)  
- **Keyword**: `@dispatch.func(x=int, y=str)` → named mapping; best for clarity and defaults.

### 3.3 Partial Specs & Fallback Fill-In

If a param is unspecified in both decorator and overload, it **inherits** the fallback’s annotation:

```python
def process(a: int, b: str, c: float) -> None: ...

@dispatch.process(a=str)   # no info for 'b' here
def _(a, b, c: float) -> None:     # no annotation for 'b' either
    ...                    # effective: a=str (dec), b=str (fallback), c=float (fn)
```

[Back to top ↑](#table-of-contents)

---

## 4) Dispatch Semantics

### 4.1 Compatibility Filtering
Before scoring, each overload must pass a **hard** runtime check against its effective type hints. Supported patterns include:

- `Union` / PEP 604 (`int | str`), `Optional[T]`  
- `Annotated[T, meta...]`, `Literal[\"a\", 3]`, `ClassVar[T]`  
- `Type[T]` / `type[T]`, runtime protocols (`typing.Protocol` with `runtime_checkable`)  
- Callable shapes (`Callable[[int, str], X]`)  
- Containers & iterables (`list[int]`, `tuple[int, ...]`, `Mapping[K, V]`, `Sequence[T]`)  
- `TypeVar` / `ParamSpec` (constraints/bounds observed)  
- TypedDict-like classes (required/optional keys honored)

### 4.2 Specificity Scoring
Compatible overloads are scored per parameter:

- Base **specificity** heuristic (concrete classes > Any; `Literal` very strong; container shapes add weight).
- **+40** if the hint is concrete (not `Any/object/wildcard`), else **+20** if declared but generic.  
- **+25** for each **declared** param satisfied (declared via decorator or annotation).  
- **−15** for provided named keys captured only via `**kwargs`.  
- **−1** if the overload declares `*args`; **−1** if it declares `**kwargs`.

The highest total wins; registration order breaks ties.

### 4.3 Structure-Aware Caching
Selections are cached by a key that reflects both types **and** call shape:

- Regular params → `type(value)`  
- `*args` → `(tuple, len(*args))`  
- `**kwargs` → `(dict, tuple(sorted(kwargs.keys())))`

This prevents cache collisions between e.g. `(x=1)` vs `(x=1,y=2)` or different kwargs sets.

### 4.4 Globals Injection for Extras
If the fallback signature included `*args` or `**kwargs` but the selected overload does not, WizeDispatcher temporarily injects globals named after the original parameters so bodies that rely on those names continue to work. Undeclared names passed by the call are also injected during the call and then restored.

[Back to top ↑](#table-of-contents)

---

## 5) Using With Methods

### 5.1 Instance Methods

```python
from typing import Any, Callable
from wizedispatcher import dispatch

class T:
    # Fallback
    def m(self, x: Any, y: Callable[..., Any]) -> str:
        return "FB"

    @dispatch.m
    def _(self, x: int, y: int) -> str:
        return "int,int"

    @dispatch.m
    def _(self, x: str, y: str) -> str:
        return "str,str"

    # Decorator enforces x=float; overload annotates y=float
    @dispatch.m(x=float)
    def _(self, y: float) -> str:
        return "float,float"

    # Positional decorator: (bool, bool)
    @dispatch.m(bool, bool)
    def _(self) -> str:
        return "bool,bool"

    # First param is Callable (decorator); y inherits Callable from fallback
    @dispatch.m(Callable)
    def _(self) -> str:
        return "callable,callable"
```

### 5.2 Class & Static Methods

Decorator order around `@classmethod` / `@staticmethod` is flexible.

```python
class U:
    @classmethod
    def cm(cls, x: object, y: object) -> str:  # fallback
        return "FB cm"

    @dispatch.cm
    @classmethod
    def _(cls, x: int, y: int) -> str:
        return "cm int,int"

    @classmethod
    @dispatch.cm
    def _(cls, x: str, y: str) -> str:
        return "cm str,str"

    @staticmethod
    def sm(x: object, y: object) -> str:       # fallback
        return "FB sm"

    @dispatch.sm
    @staticmethod
    def _(x: int, y: int) -> str:
        return "sm int,int"

    @staticmethod
    @dispatch.sm
    def _(x: str, y: str) -> str:
        return "sm str,str"
```

[Back to top ↑](#table-of-contents)

---

## 6) Property Setter Dispatch

Decorate the property name on `dispatch` to add typed setter overloads:

```python
from wizedispatcher import dispatch

class Converter:
    def __init__(self) -> None:
        self._v = 0

    @property
    def v(self) -> int:
        return self._v

    @v.setter
    def v(self, value) -> None:
        # Fallback setter: accept anything
        self._v = value

    # Overloaded setter: when 'value' is str, store its length instead
    @dispatch.v(value=str)
    def _(self, value: str) -> None:
        self._v = len(value)

c = Converter()
c.v = 3          # uses fallback setter → _v = 3
c.v = "hello"    # uses str-overload   → _v = 5
```

[Back to top ↑](#table-of-contents)

---

## 7) Varargs & Kwargs Patterns

Choose the overload that best reflects call shape and types:

```python
from typing import Any, Dict
from wizedispatcher import dispatch

def handle(x: Any, *args: Any, **kwargs: Any) -> str:
    return "FB"

@dispatch.handle
def _(x: int, y: int) -> str:
    return "x:int, y:int"

@dispatch.handle
def _(x: int, *args: Any) -> str:
    return "x:int, *args"

@dispatch.handle
def _(x: int, **kwargs: Dict[str, Any]) -> str:
    return "x:int, **kwargs"
```

[Back to top ↑](#table-of-contents)

---

## 8) Typing Power-Ups

```python
from typing import Callable, Literal, Sequence, Mapping, TypedDict, runtime_checkable, Protocol, Type

# Callable with parameter shape
def act(x: Callable[[int, str], object]) -> str: return "FB"

@dispatch.act
def _(x: Callable[[int, str], object]) -> str: return "callable-shaped"

# Literal
@dispatch.act(x=Literal["go", "stop"])
def _(x: str) -> str: return f"literal={x}"

# Sequences & containers
@dispatch.act(x=Sequence[int])
def _(x) -> str: return "seq[int]"

@dispatch.act(x=Mapping[str, int])
def _(x) -> str: return "map[str,int]"

# Type[...] supports strings and ForwardRef, and actual classes are preserved
@dispatch.act(x=Type["int"])  # strings resolve to real types
def _(x) -> str: return "type[int]"

# TypedDict-like
class User(TypedDict):
    name: str
    age: int

@dispatch.act(x=User)
def _(x) -> str: return "user-td"

# Runtime protocol
@runtime_checkable
class Named(Protocol):
    @property
    def name(self) -> str: ...

@dispatch.act(x=Named)
def _(x) -> str: return f"Named: {x.name}"
```

[Back to top ↑](#table-of-contents)

---

### 8.1 Typing normalization & TypingNormalize

WizeDispatcher applies a normalization pass so matching/scoring work on
canonical `typing.*` shapes, independent of import style or Python version.

- Normalizes `Union`/PEP 604 (`|`) and `Optional[T]`; flattens/orders with
  `None` first; any union containing `Any` becomes `Any`.
- Maps PEP 585 builtins/ABCs (`list[int]`, `collections.abc.*`) to
  `typing.*` counterparts; bare generics gain `Any` (e.g., `List` →
  `List[Any]`).
- Preserves callable origins and simplifies parameter specs:
  `Callable[[...], R]` vs `Callable[..., R]`; `ParamSpec`/`Concatenate`
  collapse to `Callable[..., R]`.
- Handles `Type[...]` robustly: resolves `Type["int"]` and
  `Type[ForwardRef("int")]` to `Type[int]`; preserves actual classes.
- Passes through and preserves structure for `Annotated`, `Literal`, and
  `ClassVar`.

You typically do not call it directly, but it is available for tooling:

```python
from typing import Callable, Concatenate, Type, Union
from wizedispatcher.typingnormalize import TypingNormalize

# Normalize to canonical forms
u = TypingNormalize(Union[int, str | None])
c = TypingNormalize(Callable[Concatenate[int, ...], str])
t = TypingNormalize(Type["int"])  # → typing.Type[int]
```

See the dedicated wiki page for a comprehensive reference:
[TypingNormalize (wiki)](docs/wiki/typingnormalize.md).

[Back to top ↑](#table-of-contents)

---

## 9) Performance

### Model
- **Cold path**: O(#overloads) — bind once, hard-filter, score compatible candidates.  
- **Hot path**: **O(1)** — structure-aware cache hit.  
- Cache key: `tuple(type/shape per param, (*args length), (**kwargs key set))`.

### Micro-benchmark Harness
Run this snippet locally to measure warm vs cold behavior:

```python
import timeit
from typing import Any
from wizedispatcher import dispatch

def f(x: Any, y: Any = 0, **kw): return 0  # fallback

@dispatch.f
def _(x: int, y: int): return 1

@dispatch.f
def _(x: float, y: float): return 2

@dispatch.f
def _(x: str, y: str): return 3

def run(n=100_000):
    # warm-up (populate cache)
    for _ in range(10_000): f(1, 2); f(1.0, 2.0); f("a", "b")

    t_hot = timeit.timeit("f(1, 2); f(1.0, 2.0); f('a','b')", globals=globals(), number=n)
    t_cold = timeit.timeit("f(1, 2)", globals=globals(), number=10_000)  # quick cold probe

    print(f"hot per call: {t_hot/(3*n):.3e}s")
    print(f"cold probe avg: {t_cold/10_000:.3e}s")

if __name__ == "__main__":
    run()
```

**What to expect (indicative):**
- Hot calls in the **low tens of nanoseconds to microseconds** range depending on Python version and machine.  
- Cold path scales linearly with the number and complexity of overloads.

### Tips for speed
- Prefer narrower, explicit types (less to score; faster cache warm-up).  
- Group common shapes first (they’ll dominate caches).  
- Avoid registering overloads dynamically at high frequency.

[Back to top ↑](#table-of-contents)

---

## 10) Comparisons

| Capability / Library                            | **WizeDispatcher** | `functools.singledispatch` | `multipledispatch` (lib) | `multimethod` (lib) | `plum` (lib) |
|---|:--:|:--:|:--:|:--:|:--:|
| Multiple params (true multiple dispatch)         | ✅ | ❌ (single param) | ✅ | ✅ | ✅ |
| Works on methods                                 | ✅ | ➖ (`singledispatchmethod` only) | ✅ | ✅ | ✅ |
| **Property setter** overloads                    | ✅ | ❌ | ❌ | ➖ (usually manual) | ➖ |
| Decorator precedence (override vs annotations)   | ✅ | ➖ | ➖ | ➖ | ✅ |
| Hard type filter + scoring                       | ✅ | ➖ | varies | varies | ✅ |
| Callable shape matching                           | ✅ | ❌ | varies | varies | ✅ |
| TypedDict-like, runtime protocol support         | ✅ | ❌ | varies | varies | ✅ |
| Structure-aware cache (*args len / kwargs keys)  | ✅ | ➖ | varies | varies | ? |
| Zero dependencies                                | ✅ | ✅ | varies | varies | varies |

> Notes: Third-party libraries differ by version/config; the table reflects typical defaults. WizeDispatcher emphasizes **modern typing**, **predictable precedence**, and **property setter** coverage.

When to use **WizeDispatcher**:
- You need per-parameter typing (not just first argument).  
- You want overloads on methods and **properties** with a single, uniform interface.  
- You care about modern typing features and deterministic, explainable selection.

[Back to top ↑](#table-of-contents)

---

## 11) Use Cases

- **API gateways / routers**: Dispatch by payload shape (TypedDict-like), verb, or header types.  
- **Numeric kernels**: Specialize by numeric dtypes (`int`, `float`, `complex`) and container forms.  
- **Plugin points**: Accept a `Protocol` and route to specific implementations.  
- **Serialization**: Overload on `Mapping[str, Any]` vs `Sequence[T]` vs `bytes`.  
- **UI / CLI adaptors**: `Callable` signatures route to proper wrappers.  
- **Domain models**: Property setters that coerce inputs (`str → int`, etc.) via typed overloads.

[Back to top ↑](#table-of-contents)

---

## 12) API Notes & Best Practices

- **Register at import time**. Overloads are inexpensive to register and benefit from a warm cache.  
- **Prefer keyworded decorator args** for clarity (`@dispatch.func(x=int)` over positional).  
- **Remember `bool <: int`**. If booleans need a different path, add a `bool` overload; it will outscore `int` for boolean values.  
- **Varargs/kwargs**: Provide explicit overloads for common shapes (e.g., `(x:int, y:int)`) and let `(x:int, *args)` / `(x:int, **kwargs)` handle the tail.  
- **Threading**: Dispatch is read-mostly after registration; registration should happen before multi-threaded usage.  
- **Debugging**: If selection surprises you, check the effective types (decorator vs annotations vs fallback) and whether a value passes the hard type filter.

[Back to top ↑](#table-of-contents)

---

## 13) Demos

Explore runnable examples in [`demos/`](demos/):

- [`demos/typing_constructs.py`](demos/typing_constructs.py): coverage of `Annotated`, `Literal`, union flattening, callable shapes.
- [`demos/methods_and_property.py`](demos/methods_and_property.py): instance/class/static methods and property setter overloads.
- [`demos/forwardref_and_strings.py`](demos/forwardref_and_strings.py): normalization of `Type["int"]` and forward references.
- [`demos/containers_and_tuples.py`](demos/containers_and_tuples.py): container/tuple matching examples.
- [`demos/run_all.py`](demos/run_all.py): execute all demos at once.

Run all demos:

```bash
python -m demos.run_all
```

[Back to top ↑](#table-of-contents)

---

## 14) Installation

```bash
pip install wizedispatcher
```

*Optional dev tooling:* `pytest`, `ruff`, `pyright`.

---

## 15) License

MIT — see [`LICENSE`](LICENSE).

---

*Questions or ideas?* Open an issue or try it live on Replit (button at the top).