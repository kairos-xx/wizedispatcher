from wizedispatcher import dispatch


# Test injection of original *args/**kwargs names into overload globals
def g(a, *varpos, **varkw):  # type: ignore[reportRedeclaration]
    """Fallback target `g` returning its inputs for inspection.

    Args:
      a: Positional argument.
      *varpos: Var-positional extras.
      **varkw: Var-keyword extras.

    Returns:
      Tuple capturing the call shape for assertions.
    """
    return ("base", a, varpos, varkw)


@dispatch.g
def g(a: int):
    """Overload of `g` that relies on injected globals for extras.

    Returns:
      A tuple with count of varpos and sorted varkw keys.
    """
    return (len(varpos), tuple(sorted(varkw)))  # type: ignore[name-defined]


def test_varargs_varkw_globals_injection_empty_when_no_extras() -> None:
    """Extras injection uses empty tuple/dict when none are passed."""
    out = g(1)
    assert out == (0, ())


# Test injection of extra named args into overload globals for undeclared names
def h(  # type: ignore[reportRedeclaration]
    a, *, b: str, **extras
):  # original accepts **extras so binding succeeds
    """Fallback for `h` that accepts keyword-only and extra names.

    Args:
      a: Positional argument.
      b: Required keyword-only string.
      **extras: Any extra keyword names.

    Returns:
      Tuple echoing provided values for assertions.
    """
    return ("base", a, b, extras)


@dispatch.h
def h(a: int):  # type: ignore[reportRedeclaration]
    """Overload of `h` expecting `b` injected into globals."""
    return b  # type: ignore[name-defined]


def test_original_named_kwargs_injected_as_globals() -> None:
    """Named kw-only param from base should be injected into overload."""
    out = h(1, b="B")  # type: ignore[reportCallIssue]
    assert out == "B"
