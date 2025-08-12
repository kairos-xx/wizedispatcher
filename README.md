<div align="center">
  <img src="https://github.com/kairos-xx/wizedispatcher/raw/main/resources/icon_raster.png" alt="Tree Interval Logo" width="150"/>
    <h1>WizeDispatcher</h1>
  <p><em>A lightweight, version-robust Python runtime dispatch library with powerful overload registration and type-based selection</em></p>

  <a href="https://replit.com/@kairos/wizedispatcher">
    <img src="https://github.com/kairos-xx/wizedispatcher/raw/main/resources/replit.png" alt="Try it on Replit" width="150"/>
  </a>

</div>

## 1. ✨ Features

- 🎯 **Overload Registration via Decorators**  
  Register multiple implementations for the same function, method, or property setter, with **keyword** or **positional** type constraints.

- 📝 **Type Hint Overrides**  
  Overloads can specify types in the decorator to **override** or **partially use** type hints from the function signature.

- ⚙ **Partial Type Specification**  
  Missing type constraints in an overload are automatically filled from the fallback/default implementation.

- 📊 **Weighted Specificity Scoring**  
  Runtime match scoring system is heuristic-based and typing-aware (see Weight-Based Evaluation).

- 🛠 **Full Typing Support**  
  `Union`, `Optional`, `Literal`, generic containers (`list[int]`, `tuple[int, ...]`), and callable detection.

- 📦 **Method & Property Support**  
  Works with instance methods, `@classmethod`, `@staticmethod`, and property setters.

- 🚀 **Fast Cached Dispatch**  
  Caches previous matches to speed up repeated calls.

- 🧩 **Varargs & Kwargs Handling**  
  Fully supports `*args` and `**kwargs` in overloads, resolving them according to parameter order.

- 🐍 **Version Robust**  
  Works consistently across Python 3.8+ with no dependencies.




## 2. 🚀 Quick Start

### 2.1 Basic Usage Example

```python
from wizedispatcher import dispatch

# Fallback
def greet(name: object) -> str:
    return f"Hello, {name}!"

# Keyword constraint
@dispatch.greet(name=str)
def _(name: str) -> str:
    return f"Hello, {name}, nice to meet you."

# Positional constraint
@dispatch.greet(str, int)
def _(name, age) -> str:
    return f"{name} is {age} years old"

print(greet("Alice"))   # Hello, Alice, nice to meet you.
print(greet("Bob", 30)) # Bob is 30 years old
```

## 3. 📊 Weight-Based Evaluation

### 3.1 Matching and Scoring Overview

WizeDispatcher first **filters** overloads by type **compatibility** and then
**scores** the remaining candidates to pick the most specific one.

#### 3.1.1 Compatibility filter

For each parameter in dispatch order, the runtime value must match the
overload’s **effective hint**. Matching supports:

- `Union | PEP 604`, `Optional`, `Literal`, `Annotated`, `ClassVar`
- `Type[T]` / `type`, protocols (runtime), `TypedDict`-like classes
- Callables with parameter shapes, containers (`list/tuple/dict/set/...`)
- `TypeVar` / `ParamSpec` (constraints/bounds respected)

> **Overload defaults participate in matching:**  
> If an overload defines a default for a parameter and the caller omitted it,
> the **default value** is used as the value to match/score for that parameter.

#### 3.1.2 Scoring the compatible candidates

For each parameter, we compute:

```
score += specificity(value, hint)
score += (40 if hint is not Any/object/WILDCARD else 20)
```

Then we apply a small **penalty** if the overload uses `*args`:

```
score -= 2  # has VAR_POSITIONAL
```

Finally, the overload with the **highest total score** wins. If multiple
overloads tie, the one **registered first** remains selected (deterministic).
If no overload is compatible, the **original (fallback)** is called.

#### Specificity highlights (per-parameter)

Below is a compact view of the core heuristic used by
`_type_specificity_score(value, hint)`:

| Hint shape                           | Specificity (approx)                  |
|-------------------------------------|---------------------------------------|
| `Literal[...]`                      | **100**                               |
| `Annotated[T, ...]`                 | `1 + specificity(value, T)`           |
| `ClassVar[T]`                       | `specificity(value, T)`               |
| `Union[T1, T2, ...]`                | `max(specificity(...)) - len(Union)`  |
| `Type[T]` / `type[T]`               | `15 + specificity(value, T)`          |
| Bare `Type` / `type`                | `8`                                   |
| `Callable[[args...], ...]`          | `12 + Σ specificity(arg_i)`           |
| `Mapping[K, V]` / `dict[K, V]`      | `20 + specificity(K) + specificity(V)`|
| `Sequence[T]` / iterables           | `16` (unparam) or `18 + spec(T)`      |
| Concrete container w/ params        | `20 + Σ specificity(param_i)`         |
| Unparameterized `Tuple/List/Dict`   | `10`                                  |
| Concrete class `C`                  | `5 + max(0, 50 - mro_distance(value, C))` |
| `Any`, `object`, or `WILDCARD`      | `0`                                   |

> **Note:** The extra **+40 / +20** bonus per param encourages overloads that
> *declare* types (even loosely) over ones that leave things unconstrained.

### 3.2 Example (why one wins)

```python
# Fallback
def greet(name: object) -> str: ...

@dispatch.greet(name=str)          # declares a concrete type for 'name'
def _(name: str) -> str: ...

@dispatch.greet(Any)               # explicitly Any
def _(name) -> str: ...
```

A call `greet("Alice")`:

- `name=str` overload:
  - Specificity for `str` with value `"Alice"`: high (concrete class match)
  - +40 bonus for a concrete (non-Any) hint
- `name=Any` overload:
  - Specificity: 0
  - +20 bonus (declared but Any)

→ The `name=str` overload’s total is higher, so it wins.

### 3.3 Caching

Selections are cached by the **tuple of runtime parameter types** (in dispatch
order) for fast repeat calls.


## 4. 📐 Type Resolution Precedence

### 4.1 Precedence Rules Overview

WizeDispatcher determines the **effective type** for each parameter using a
clear, three-tier precedence. This governs what is matched and scored.

1) **Decorator overrides function annotations**  
   - `@dispatch.func(a=int)` means: for parameter `a`, **use `int`** even if
     the overload function annotates something else (e.g., `a: str`).  
   - Positional decorator args map by parameter order:
     `@dispatch.func(int, str)` → first param `int`, second `str`.

2) **If the decorator omits a param, use the overload function annotation**  
   - Example: overload is `def _(a: str, b: bytes) -> ...` and decorator
     is `@dispatch.func(a=int)`. Effective types → `a=int` (override),
     `b=bytes` (from function).

3) **If both decorator and overload omit a param, fall back to the default**  
   - The **default (original) function** annotations fill any remaining gaps.
   - If the default is also missing an annotation, that param becomes a
     **wildcard** (matches anything) and scores accordingly.

#### 3.1.4 TL;DR Summary
**Decorator > Overload function annotations > Default function annotations > Wildcard**

---

### 4.2 Case 1 — Bare decorator uses overload annotations — Bare decorator: use **overload function annotations**

```python
from wizedispatcher import dispatch

# Default (fallback) function
def process(a: int, b: str, c: float) -> str:
    return f"default: a={a!r}, b={b!r}, c={c!r}"

# Bare decorator → takes annotations from the overload itself
@dispatch.process
def _(a: int, b: bytes, c: float) -> str:
    return f"overload1: b_is={type(b).__name__}"

print(process(1, b"hi", 2.0))  # ✅ matches overload (b: bytes)
print(process(1, "hi", 2.0))   # ➜ falls back (b is str, not bytes)
```

**Why:** No decorator args were provided, so the overload’s own annotations
(`b: bytes`) are the effective constraint for matching.

---

### 4.3 Case 2 — Decorator overrides overload annotations — Decorator **overrides** overload annotations

```python
from wizedispatcher import dispatch

def process(a: int, b: str, c: float) -> str:
    return "default"

# Decorator forces a=str, overriding the overload's (a: int)
@dispatch.process(a=str)
def _(a: int, b: bytes, c: float) -> str:
    return "overload2"

print(process("x", b"y", 1.0))  # ✅ matches overload (a must be str)
print(process(1, b"y", 1.0))    # ➜ fallback (a is int, but decorator requires str)
```

**Positional decorator example** (maps by parameter order):

```python
from wizedispatcher import dispatch

def process(a: int, b: str, c: float) -> str:
    return "default"

# Positional mapping → a=str, b=bytes, c=float
@dispatch.process(str, bytes, float)
def _(a, b, c) -> str:
    return "overload3"

print(process("x", b"y", 1.0))  # ✅ matches overload3
print(process("x", "y", 1.0))   # ➜ fallback (b is str, expected bytes)
```

**Why:** When decorator arguments exist, they **override** the overload’s
annotations for the covered parameters.

---

### 4.4 Case 3 — Missing on both decorator and overload → use default — Missing on both decorator and overload → **use default**

```python
from wizedispatcher import dispatch

# Default provides types for all params
def process(a: int, b: str, c: float) -> str:
    return "default"

# Decorator sets only 'a', overload omits annotation for 'b'
@dispatch.process(a=str)       # no info for 'b' here
def _(a: int, b, c: float) -> str:  # no type for 'b' here either
    return "overload4"

print(process("x", "hello", 1.0))  # ✅ matches overload4
#   effective types: a=str (decorator), b=str (from default), c=float (overload)

print(process("x", 123, 1.0))      # ➜ fallback
#   'b' is int — default says 'b: str', so overload4 is incompatible
```

**Wildcard note:** If the default also lacks an annotation for a parameter,
that parameter becomes a **wildcard** (matches anything but is scored as such).
## 5. 🧩 Partial Type Specification

```python
# Default function defines all parameters
def process(a: int, b: str, c: float) -> str:
    return "default"

# Overload defines only 'a', inherits 'b' and 'c' types from default
@dispatch.process(a=str)
def _(a: str, b, c) -> str:
    return f"a is str, b is {type(b)}, c is {type(c)}"
```

## 6. 🛠 Methods & Properties

```python
class Converter:
    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, val: object) -> None:
        self._value = val  # fallback setter

    @dispatch.value(value=int)
    def _(self, value: int) -> None:
        self._value = value * 10

    @dispatch.value(value=str)
    def _(self, value: str) -> None:
        self._value = int(value)

c = Converter()
c.value = 3
print(c.value)  # 30
c.value = "7"
print(c.value)  # 7
```

## 7. 📦 Installation

```bash
pip install wizedispatcher
```

## 8. 📚 Documentation

- **Wiki**: Complete documentation in `/wizedispatcher_wiki`
- **Examples**: Ready-to-run demos in `/demo`

## 9. 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file.


## 🎯 How Type Constraints Are Determined

When deciding which types to use for overload matching, **WizeDispatcher**
follows a strict precedence order. This allows you to be as explicit or as
implicit as you like when defining overloads.

#### 3.1.1 No decorator arguments

```python
@dispatch.func
def _(a: int, b: str) -> None:
    ...
```
If the decorator has **no arguments**, the type hints are taken **directly**
from the overload function’s own signature.

#### 3.1.2 Decorator with arguments

```python
@dispatch.func(a=str)
def _(a: int, b: str) -> None:
    ...
```
If the decorator **has arguments**, those override the type hints for the
specified parameters, **ignoring** the overload function's own hints for those
parameters.

#### 3.1.3 Missing arguments in both decorator and overload

```python
# Default (fallback) function defines all parameters
def func(a: int, b: str) -> None:
    ...

# Overload defines only 'a' in the decorator, leaves 'b' undefined
@dispatch.func(a=str)
def _(a, b) -> None:
    ...
```
If a parameter is **missing** from both the decorator arguments **and** the
overload function’s type hints, WizeDispatcher uses the type hint from the
**default (fallback) function**.

### Summary Table

| Source                              | Priority |
|-------------------------------------|----------|
| Decorator arguments                 | Highest  |
| Overload function's type hints      | Medium   |
| Default function's type hints       | Lowest   |

This precedence ensures that you can:
- Override only what you need without redefining all types.
- Inherit defaults from the fallback function.
- Use explicit decorator arguments when you want to fully control matching.

