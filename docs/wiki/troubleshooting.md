# Troubleshooting

This section covers common pitfalls when using WizeDispatcher and
how to resolve them.

## TypeError: too many positional arguments

If you attempt to dispatch on a property setter without defining a
base setter, you may see an error like:

```
TypeError: too many positional arguments
```

This occurs because WizeDispatcher uses the getter’s signature to
build the registry when no setter exists. To fix this, define a
base setter:

```python
class Q:
    @property
    def v(self) -> Any:
        return getattr(self, "_v", None)

    @v.setter
    def v(self, value) -> None:
        # base setter needed to establish signature
        self._v = value

    @dispatch.v(value=int)
    def _(self, value) -> None:
        self._v = value * 2

    @dispatch.v(value=str)
    def _(self, value) -> None:
        self._v = f"({value})"
```

## Overload not selected

If the overload you expect is not selected, check the following:

- Are you annotating or providing the correct types? Decorator
  keyword arguments override annotations.
- Are string-based or forward-ref types being resolved as expected? WizeDispatcher
  normalizes `Type["int"]` to `Type[int]` and flattens unions before matching.
- Are you accidentally passing a subclass? The specificity scoring
  may select a more specific overload for subclasses.
- Are you mixing positional and keyword constraints correctly?
  Provide positional type constraints in order for the constrained
  parameters.

## Missing import of `dispatch`

Ensure you import the `dispatch` object from `wizedispatcher`:

```python
from wizedispatcher import dispatch
```

## Using Union, Literal, or Optional with generics

When using `Union`, `Literal`, or `Optional` inside generic
containers like `list` or `tuple`, note that WizeDispatcher
checks element‑wise types where possible. For example,
`list[Union[int, str]]` matches lists containing both ints and
strings.

If you see unexpected matches, try annotating the elements
explicitly or splitting overloads for each case.

## Callable parameters don’t seem to match

If you constrain a parameter as `Callable[[T1, T2], R]`, WizeDispatcher checks
the callable’s declared positional parameters when they’re visible to
`inspect.signature`. Unknown or built-in callables are treated as compatible.
When using `ParamSpec` or `Concatenate`, normalization converts them to
`Callable[..., R]`, which accepts any parameter shape.