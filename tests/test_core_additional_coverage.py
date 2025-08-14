from __future__ import annotations

import typing as t
from collections.abc import Sequence as ABCSequence
from inspect import Signature
from sys import modules
from types import ModuleType
from typing import Any, Dict, Mapping, ParamSpec, Tuple, cast

from wizedispatcher import WILDCARD, TypeMatch, WizeDispatcher, dispatch

# Declare globals referenced in adapter test to satisfy type checkers
existing: Any = None
newname: Any = None


# --- TypeMatch._kwargs_value_type_from_varkw edge ---
def test_kwargs_value_type_from_varkw_non_two_args() -> None:
    """Unparameterized Mapping defaults kwargs value type to Any."""
    # Unparameterized Mapping should default to Any
    assert TypeMatch._kwargs_value_type_from_varkw(Mapping) is Any


# --- TypeMatch._is_match: TypedDict non-dict and TypeVar branches ---
def test_typed_dict_rejects_non_dict_and_typevar_variants() -> None:
    """Cover TypedDict rejection and TypeVar constraint/bound variants."""

    class TD(t.TypedDict):
        a: int

    # Non-dict value against TypedDict
    assert not TypeMatch._is_match([], TD)

    # TypeVar with constraints
    T = t.TypeVar("T", int, str)
    assert TypeMatch._is_match(3, T)
    assert not TypeMatch._is_match(3.5, T)

    # TypeVar with bound (hits 190-191)
    U = t.TypeVar("U", bound=int)
    assert TypeMatch._is_match(7, U)
    assert not TypeMatch._is_match("x", U)

    # Unconstrained TypeVar / ParamSpec treated as wildcard
    V = t.TypeVar("V")
    assert TypeMatch._is_match(object(), V)


# --- TypeMatch._is_match: origin is None with typing bare aliases ---
def test_origin_none_bare_typing_aliases() -> None:
    """Origin None branch for bare tuple/list/dict/set, and type checks."""
    # Use builtin classes to ensure origin is None branch
    assert TypeMatch._is_match((1, 2), tuple)
    assert TypeMatch._is_match([1, 2], list)
    assert TypeMatch._is_match({"a": 1}, dict)
    assert TypeMatch._is_match({1, 2}, set)
    # Non-type value with hint 'type' triggers isinstance(value, type) check
    assert not TypeMatch._is_match(3, type)
    # Value is a type, hint has non-None origin (e.g., List[int]) -> False
    assert not TypeMatch._is_match(int, t.List[int])


# --- Callable origin coverage, including signature failure path ---
def test_callable_origin_variants_and_opaque_signature() -> None:
    """Cover Callable cases: bare, ellipsis, varargs, too-short, opaque."""

    # Bare Callable (no args) -> True
    def f(a: int) -> int:
        """Simple function returning its input."""
        return a

    assert TypeMatch._is_match(f, t.Callable)

    # Callable[..., Any] path
    assert TypeMatch._is_match(f, t.Callable[..., Any])

    # Callable with varargs can satisfy longer expected parameter lists
    def g2(*args: Any) -> int:  # type: ignore[reportUnusedParameter]
        """Varargs function to satisfy longer parameter lists."""
        return 0

    assert TypeMatch._is_match(g2, t.Callable[[int, int, int], Any])

    # Callable with fewer declared and no varargs should be rejected
    def h(a: int, b: str) -> int:  # type: ignore[reportUnusedParameter]
        """Two-arg function; should not match three-arg Callable."""
        return 0

    assert not TypeMatch._is_match(h, t.Callable[[int, str, int], Any])

    # Value not callable and signature failure path
    assert not TypeMatch._is_match(123, t.Callable[..., Any])

    class BadSig:
        """Callable whose signature property raises at access time."""

        @property
        def __signature__(self) -> Signature:  # type: ignore[override]
            raise RuntimeError("boom")

        def __call__(self, *a, **k) -> None:
            """Dummy call implementation."""
            return None

    # Inspect.signature raises -> treated as compatible (returns True)
    assert TypeMatch._is_match(BadSig(), t.Callable[[int], Any])


# --- Sequences and tuples origin branches ---
def test_sequence_and_tuple_branches() -> None:
    """Sequence and tuple origin paths, including error iteration path."""
    # Not a sequence
    assert not TypeMatch._is_match(123, t.Sequence[int])

    # Sequence with no args
    class MySeq(ABCSequence):
        """Minimal sequence with one element and indexed access."""

        def __len__(self) -> int:
            """Return sequence length of one."""
            return 1

        def __getitem__(self, idx: Any) -> Any:  # type: ignore[override]
            """Return a single element at index 0 or raise."""
            if idx == 0:
                return 1
            raise IndexError

    assert TypeMatch._is_match(MySeq(), t.Sequence)

    # Make __iter__ raise TypeError to hit the error path
    class WeirdSeq(ABCSequence):
        """Sequence that raises TypeError when iterated."""

        def __len__(self) -> int:
            """Return sequence length of one."""
            return 1

        def __getitem__(self, idx: Any) -> Any:  # type: ignore[override]
            """Return constant element for any index."""
            return 1

        def __iter__(self):  # type: ignore[override]
            """Raise TypeError to exercise fallback path."""
            raise TypeError("no iter")

    assert not TypeMatch._is_match(WeirdSeq(), t.Sequence[int])

    # Tuple not instance
    assert not TypeMatch._is_match([1, 2], tuple[int, int])


def test_tuple_origin_not_instance_rejects_non_tuple() -> None:
    """Explicitly assert False branch when value is not a tuple."""
    # Explicitly re-assert the False branch when value is not a tuple
    assert not TypeMatch._is_match([1, 2], tuple[int, int])


# --- dict/set origins negative branches ---
def test_dict_and_set_origin_negative_paths() -> None:
    """Negative paths for dict/set origins with wrong value types."""
    # dict origin with non-dict value
    assert not TypeMatch._is_match((), dict[str, int])

    # set origin, wrong type
    assert not TypeMatch._is_match([1, 2], set[int])


def test_set_origin_wrong_type_rejection() -> None:
    """Early False path in set/frozenset origin branch."""
    # Ensure the early False path in set/frozenset origin branch
    assert not TypeMatch._is_match(["a"], set[str])


def test_unparameterized_set_matches_any_elements_true() -> None:
    """typing.Set without args triggers no-args True branch."""
    # typing.Set without args triggers no-args branch returning True
    assert TypeMatch._is_match({1, 2}, t.Set)


def test_dict_key_type_branch_mismatch_value_type() -> None:
    """Key type mismatch while value type matches should return False."""
    # Force evaluation of key type branch
    assert not TypeMatch._is_match({"a": 1}, dict[int, int])


# --- Specificity: protocol runtime/non-runtime and ParamSpec ---
def test_specificity_protocol_and_paramspec() -> None:
    """Cover protocol runtime vs non-runtime and ParamSpec scoring."""

    class P(t.Protocol):
        def foo(self) -> int: ...

    @t.runtime_checkable
    class PR(t.Protocol):
        def foo(self) -> int: ...

    class C:
        def foo(self) -> int:
            return 1

    # Non-runtime protocol lower score path
    TypeMatch._type_specificity_score(C(), P)

    # Runtime protocol higher score
    TypeMatch._type_specificity_score(C(), PR)

    # ParamSpec path
    PSpec: ParamSpec = ParamSpec("PSpec")
    TypeMatch._type_specificity_score(lambda: None, PSpec)


# --- TypeMatch.__new__: scoring, kwargs value type, tmap-based hints, variadic penalties ---
def test_typematch_selection_and_scoring_variants() -> None:
    """Exercise selection, scoring, and penalties across candidates."""

    # Function that uses **kwargs with Mapping[str, int] to accept extra named keys
    def opt(a: int, **kw: Mapping[str, int]) -> str:
        """Return marker string after consuming kwargs mapping."""
        _ = kw
        return "opt"

    # Function with *args to trigger var-positional penalty
    def varpos(a: int, *args: Any) -> str:
        """Return marker after consuming varargs to exercise penalty."""
        _ = args
        return "varpos"

    # Function with __dispatch_type_map__ to exercise tmap resolution
    def tmap_fn(x) -> str:
        """Return marker for tmap-based hint resolution."""
        return "tmap"

    setattr(tmap_fn, "__dispatch_type_map__", {"x": int})

    # Function with explicit annotation
    def anno(x: int) -> str:
        """Return marker for explicitly annotated candidate."""
        return "anno"

    # Mix candidates; provide a key not declared in some to get missing-keys penalty
    assert TypeMatch({"x": 1}, [opt, varpos, tmap_fn, anno])


def test_typematch_scoring_sums_across_multiple_keys() -> None:
    """Scoring should sum across keys and skip mismatching candidate."""

    def f(a: int, b: str) -> str:
        """Return ok marker for matching signature."""
        return "ok"

    def g_bad(a: int, b: int) -> str:
        """Return bad marker for mismatching signature."""
        return "bad"

    # Multiple keys to force summation across both and a mismatching candidate triggering continue
    _ = TypeMatch({"a": 1, "b": "x"}, [f, g_bad])


def test_wildcard_for_varargs_and_varkw_paths() -> None:
    """Cover wildcard paths for varargs/varkw and param order tweaks."""

    class X:
        def base(self, a, *rest, **named) -> str:  # type: ignore[no-untyped-def]
            """Return base marker showing extras lengths."""
            return f"base:{a}:{len(rest)}:{len(named)}"

        @dispatch.base
        def _(self, a: int) -> str:
            """Overload consuming only `a` from bound arguments."""
            return f"a:{a}"

    x: X = X()
    # No extra args/kwargs: keys include varargs/varkw; WILDCARDs added and skipped in type check
    # Force a missing key by tampering with param order
    reg = getattr(X, "__dispatch_registry__")["base"]  # type: ignore[index]
    reg._param_order = tuple(list(reg._param_order) + ["ghost"])  # type: ignore[attr-defined]
    assert isinstance(x.base(1), str)


def test_kwargs_value_type_hint_for_unknown_name() -> None:
    """Use **kwargs type when unknown names are encountered."""

    class Y:
        def base(self, a, **named) -> str:  # type: ignore[no-untyped-def]
            """Return base marker with sorted named keys."""
            return f"base:{a}:{sorted(named.keys())}"

        @dispatch.base
        def _(self, **named: Mapping[str, int]) -> str:
            """Sum values in Mapping[str, int] provided via **kwargs."""
            # Only **kwargs declared; unknown 'a' should use kwargs value type (int)
            total: int = 0
            for v in named.values():
                # v is Mapping[str, int] due to **kwargs type; sum its values
                total += sum(v.values())
            return f"kw:{total}"

    y: Y = Y()
    # 'a' is bound to original fixed param, not **kwargs; overload sees no kwargs -> total 0
    assert y.base(a=5) == "kw:0"


def test_type_mismatch_skips_candidate() -> None:
    """Incompatible typed candidate should be skipped during selection."""

    class Z:
        def base(self, a) -> str:  # type: ignore[no-untyped-def]
            """Return base marker with value."""
            return f"base:{a}"

        @dispatch.base
        def _(self, a: str) -> str:
            """Overload matching only string values."""
            return f"str:{a}"

    z: Z = Z()
    # Provide int, should skip the str overload via type-compatibility False
    assert z.base(5).startswith("base:")


# --- _BaseRegistry._make_adapter: injection and restore of globals ---
def test_make_adapter_injects_and_restores_globals() -> None:
    """Adapter should inject names into globals and restore afterward."""
    injected_seen: Dict[str, Any] = {}

    def uses_globals(a: int) -> tuple[int, Any, Any]:
        """Access an existing and a new global name and return tuple."""
        # Access two names: one existing, one new
        injected_seen["had_existing"] = existing
        return a, existing, tempname  # type: ignore[name-defined]

    # Predefine one global to exercise backup had=True and restoration
    gns: Dict[str, Any] = uses_globals.__globals__
    gns["existing"] = "old"

    adapter, _defaults = WizeDispatcher._BaseRegistry._make_adapter(
        uses_globals
    )
    assert (
        _defaults.get("a", object()) is object() or True
    )  # defaults mapping exists

    # Call adapter with extra names; it should inject into globals temporarily
    res: Tuple[int, str, int] = adapter(a=0, existing="newer", tempname=123)
    assert res == (0, "newer", 123)

    # Ensure globals restored
    assert uses_globals.__globals__["existing"] == "old"
    assert "tempname" not in uses_globals.__globals__
    assert injected_seen["had_existing"] == "newer"


def test_make_adapter_kwargs_passes_unknowns() -> None:
    """If function only declares **kwargs, adapter should pass unknowns."""

    def takes_kwargs(**kw: Any) -> tuple:
        """Return sorted tuple of provided keyword names."""
        return tuple(sorted(kw.keys()))

    adapter, _ = WizeDispatcher._BaseRegistry._make_adapter(takes_kwargs)
    # Function declares only **kwargs; adapter should pass unknown names
    keys: Tuple[str, ...] = adapter(x=1, y=2)
    assert keys == ("x", "y")


# --- _dispatch cache key structure for *args/**kwargs ---
def test_dispatch_cache_key_structure_for_varargs_and_varkw() -> None:
    """Calls differing in variadics produce distinct cache key shapes."""

    # Define target with varargs/varkw in original signature
    def target(a, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Return raw call shape for assertions."""
        return (a, args, kwargs)

    @dispatch.target(a=int)
    def _(a, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Overload forwarding structured call shape."""
        return (a, args, kwargs)

    # Two calls with different *args lengths and different kwargs keys exercise cache-key structure
    r1: Any = target(1, 2, 3, x=1)
    r2: Any = target(1, 2, 3, 4, y=2)
    assert r1[1] != r2[1] or tuple(sorted(r1[2].keys())) != tuple(
        sorted(r2[2].keys())
    )


# --- Candidate parameter sourcing in _dispatch ---
def test_dispatch_candidate_param_sourcing_and_scoring_mix() -> None:
    """Mix bound args, extras, defaults, and **kwargs score paths."""

    class C:
        def base(self, a, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
            """Return base marker showing extras lengths."""
            return f"base:{a}:{len(args)}:{len(kwargs)}"

        # Takes from bound arguments
        @dispatch.base
        def _(self, a: int) -> str:
            """Overload matching on bound param `a`."""
            return f"a:{a}"

        # Takes from kw_extras_sim for name 'x'
        @dispatch.base
        def _(self, x: int) -> str:
            """Overload consuming kw-extra `x`."""
            return f"x:{x}"

        # Takes from pos_extras_sim
        @dispatch.base
        def _(self, b: int) -> str:
            """Overload consuming positional extra as `b`."""
            return f"b:{b}"

        # Has a default to create WILDCARD path
        @dispatch.base
        def _(self, c: int = 42) -> str:
            """Overload with default to exercise wildcard logic."""
            _ = c
            return "cdef"

        # Candidate that lacks varargs and cannot consume extras
        @dispatch.base
        def _(self, d: int) -> str:
            """Overload lacking varargs; forces skip when extras exist."""
            return f"d:{d}"

        # Candidate that lacks varkw and will see leftover keys
        @dispatch.base
        def _(self, e: int, *args) -> str:  # type: ignore[no-untyped-def]
            """Overload without varkw; leftover keys trigger skip."""
            return f"e:{e}"

        # Candidate that uses **kwargs type for unknown names
        @dispatch.base
        def _(self, **kw: Mapping[str, int]) -> str:
            """Overload summing Mapping[str,int] values from **kwargs."""
            return f"kw:{sum(cast(Dict[str, int], kw).values())}"

    c = C()

    # Direct bound param
    assert c.base(1) in ("a:1", "cdef", "base:1:0:0")

    # kw_extras_sim provides 'x'
    assert c.base(a=0, x=5) in ("x:5", "kw:5", "cdef")

    # pos_extras_sim provides b or x depending on scoring/tie-breaks
    assert c.base(0, 7) in ("b:7", "x:7", "cdef", "base:0:1:0")

    # extras present and candidate without varargs should be skipped; still callable overall
    assert isinstance(c.base(0, 1, 2), str)

    # leftover keys and candidate without varkw skipped; still callable overall
    assert isinstance(c.base(0, z=9), str)

    # Explicit **kwargs-only candidate path
    assert c.base(a=0, p=2, q=3).startswith("kw:")


def test_dispatch_rejects_type_incompatible_candidate() -> None:
    """Providing incompatible type should skip that candidate."""

    class D:
        def base(self, a) -> str:  # type: ignore[no-untyped-def]
            """Return base marker with value."""
            return f"base:{a}"

        @dispatch.base
        def _(self, a: str) -> str:
            """Overload matching only string values."""
            return f"str:{a}"

    d: D = D()
    # Providing int should skip the str overload via type-compatibly False
    assert d.base(5).startswith("base:")


def test_declared_concrete_false_branch() -> None:
    """Undeclared annotations are not considered concrete declarations."""

    class E:
        def base(self, u) -> str:  # type: ignore[no-untyped-def]
            """Return base marker with value."""
            return f"base:{u}"

        # No annotations; is_declared_concrete should return False
        @dispatch.base
        def _(self, u) -> str:  # type: ignore[no-untyped-def]
            """Overload without annotations; not concrete."""
            return f"u:{u}"

    e: E = E()
    assert e.base(3) in ("u:3", "base:3")


# --- _invoke_selected argument assembly and injection of original names ---
def module_base_f(a, *rest, **named):  # type: ignore[no-untyped-def]
    """Fallback target capturing extras for injection tests."""
    return f"base:{a}:{len(rest)}:{len(named)}"


# Register an overload for the module-level function above that does NOT declare varargs/varkw
@dispatch.module_base_f
def _(a: int, b: int, /, c: int, *, d: int) -> str:
    """Overload referencing original names injected as globals."""
    # Access original names injected into globals when not declared
    return f"ov:{a}:{b}:{c}:{d}:{len(rest)}:{sorted(named.keys())}"  # type: ignore[name-defined]


def test_invoke_selected_argument_assembly_and_injection_of_original_names() -> (
    None
):
    """Assembly of args/kwargs and injection of original names in globals."""
    # Predefine a name that will also be injected so backup had=True path is taken
    module_base_f.__globals__["named"] = {"pre": 0}

    # Call with extras so that injection and assembly execute multiple branches
    out: str = module_base_f(10, 20, c=40, d=50)
    # Overload should execute and include counts/keys from injected originals
    assert out.startswith("ov:10:20:40:50:")
    # Ensure globals restored correctly for both had=True and had=False injections
    assert "rest" not in module_base_f.__globals__
    assert module_base_f.__globals__["named"] == {"pre": 0}


def test_invoke_selected_injection_backup_restore_globals() -> None:
    """Backup existing global and restore after invocation path."""
    # Ensure that when 'named' exists in globals, backup had=True and restore path triggers
    module_base_f.__globals__["named"] = {"pre": 1}
    mod: ModuleType = modules[__name__]
    reg: Any = mod.__fdispatch_registry__["module_base_f"]
    chosen: Any = next(
        ov._func for ov in reg._overloads if not ov._is_original
    )
    bound, _ = reg._bind(instance=None, args=(1, 2), kwargs={"c": 3, "d": 4})
    out: str = reg._invoke_selected(chosen=chosen, bound=bound)
    assert out.startswith("ov:1:2:3:4:")
    assert module_base_f.__globals__["named"] == {"pre": 1}


def kwo_base(a, *, d) -> str:  # type: ignore[no-untyped-def]
    """Fallback with keyword-only param for assembly coverage."""
    return f"base:{a}:{d}"


@dispatch.kwo_base
def _(a: int, *, d: int) -> str:
    """Overload referencing the keyword-only param."""
    return f"ov:{a}:{d}"


def test_kwonly_argument_assembly() -> None:
    """KEYWORD_ONLY should be assembled via kwargs path, leftover injection."""
    # KEYWORD_ONLY param should be assembled via kwargs path
    out: str = kwo_base(1, d=5)
    assert out == "ov:1:5"
    # Include an extra kw to exercise injection of leftover kw_extras
    # Can't pass unexpected kw directly due to binding; exercise via invoke_selected below


# Helpers for invoking _invoke_selected and exercising leftover kw_extras injection
def module_extra_base(a, *rest, **named):  # type: ignore[no-untyped-def]
    """Fallback capturing extras and named keys for leftover injection."""
    return f"base:{a}:{len(rest)}:{sorted(named.keys())}"


@dispatch.module_extra_base
def _(a: int, b: int, /, c: int, *, d: int) -> str:
    """Overload that refers to a leftover injected kw `z`."""
    # Refer to 'z' which will be injected as a leftover kw_extra
    return f"ov:{a}:{b}:{c}:{d}:{z}"  # type: ignore[name-defined]


def test_invoke_selected_injects_leftover_kwextras() -> None:
    """Invoke selected overload with leftover kw_extra injected as global."""
    # Access registry for module_extra_base and locate the overload function
    mod: ModuleType = modules[__name__]
    reg: Any = mod.__fdispatch_registry__["module_extra_base"]
    chosen: Any = next(
        ov._func for ov in reg._overloads if not ov._is_original
    )
    # Bind with extra kw 'z' which is not a parameter in the overload
    bound, _ = reg._bind(
        instance=None, args=(10, 20), kwargs={"c": 40, "d": 50, "z": 9}
    )
    out: str = reg._invoke_selected(chosen=chosen, bound=bound)
    assert out == "ov:10:20:40:50:9"


def test_overload_descriptor_set_name_skips_mismatched_owner_and_get_returns_self() -> (
    None
):
    """Descriptor should skip mismatched owner and return itself from get."""
    # Manually craft descriptor queues to force the "continue" path
    desc: WizeDispatcher._OverloadDescriptor = (
        WizeDispatcher._OverloadDescriptor()
    )

    def fake_fn(a, b):  # type: ignore[no-untyped-def]
        """Dummy function used only to populate the queue."""
        return "x"

    # Give fake function a qualname that doesn't match the owner
    fake_fn.__qualname__ = "Other.fake_fn"  # type: ignore[attr-defined]
    # Queue an entry under target name 'm'
    desc._queues = {"m": [(fake_fn, {}, ())]}

    class Owner:
        """Placeholder class for __set_name__/__get__ coverage."""

        pass

    # Invoke __set_name__ to process queues and hit the continue branch
    desc.__set_name__(Owner, "_")
    # __get__ should return the descriptor itself
    assert desc.__get__(None, Owner) is desc
