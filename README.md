
<div align="center">
  <img src="https://github.com/kairos-xx/wizedispatcher/raw/main/resources/icon_raster.png" alt="Tree Interval Logo" width="150"/>
    <h1>WizeDispatcher</h1>
  <p><em>A lightweight, version-robust Python runtime dispatch library with powerful overload registration and type-based selection</em></p>

  <a href="https://replit.com/@kairos/wizedispatcher">
    <img src="https://github.com/kairos-xx/wizedispatcher/raw/main/resources/replit.png" alt="Try it on Replit" width="150"/>
  </a>

</div>

## ✨ Features

- 🎯 **Overload Registration via Decorators**  
  Register multiple implementations for the same function, method, or property setter, with **keyword** or **positional** type constraints.

- 📝 **Type Hint Overrides**  
  Overloads can specify types in the decorator to **override** or **partially use** type hints from the function signature.

- ⚙ **Partial Type Specification**  
  Missing type constraints in an overload are automatically filled from the fallback/default implementation.

- 📊 **Weighted Specificity Scoring**  
  Runtime match scoring system:  
    - `3` → Exact type match  
    - `2` → Instance match  
    - `1` → `Any` annotation match  
    - `0` → Wildcard match (unspecified param)  
    - `-1` → No match

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

## 🚀 Quick Start

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

## 📊 Weight-Based Evaluation

WizeDispatcherevaluates overloads with a **specificity weight system**:

| Weight | Meaning                      |
|--------|------------------------------|
| 3      | Exact type match              |
| 2      | Instance match                |
| 1      | Any annotation match          |
| 0      | Wildcard (unspecified param)  |
| -1     | No match (discarded)          |

Example:  
If two overloads match, the one with the **higher total weight** is chosen.

## 🧩 Partial Type Specification

```python
# Default function defines all parameters
def process(a: int, b: str, c: float) -> str:
    return "default"

# Overload defines only 'a', inherits 'b' and 'c' types from default
@dispatch.process(a=str)
def _(a: str, b, c) -> str:
    return f"a is str, b is {type(b)}, c is {type(c)}"
```

## 🛠 Methods & Properties

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

## 📦 Installation

```bash
pip install wizedispatcher
```

## 📚 Documentation

- **Wiki**: Complete documentation in `/wizedispatcher_wiki`
- **Examples**: Ready-to-run demos in `/demo`

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file.
