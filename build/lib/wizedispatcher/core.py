"""Runtime dispatch and type-matching utilities with decorator-based
overload registration.

This module provides:

- `TypeMatch`: helpers to check values against type hints and to compute
  a specificity score used to rank overload candidates.
- `WizeDispatcher`: a builder that creates namespaced decorators (e.g.,
  `@dispatch.func`) for registering overloads on free functions and on
  methods, including instance/class/static methods and property setters.

It keeps the original callable as a fallback, binds calls according to
the original signature, and selects the best overload using typing-aware
matching rules.

The public instance `dispatch` is used to decorate overloads.
"""

from __future__ import annotations

from collections.abc import Callable as ABCCallable
from collections.abc import Collection as ABCCollection
from collections.abc import Iterable as ABCIterable
from collections.abc import Mapping as ABCMapping
from collections.abc import MutableMapping, MutableSequence, Sequence
from contextlib import suppress
from dataclasses import dataclass
from functools import update_wrapper
from inspect import BoundArguments, Parameter, Signature, signature
from sys import modules
from types import EllipsisType, MappingProxyType, ModuleType
from typing import (
    Annotated,
    Any,
    Callable,
    ClassVar,
    Dict,
    Final,
    ForwardRef,
    FrozenSet,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    ParamSpec,
    Self,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

UnionType: Optional[Any] = None
with suppress(Exception):
    from types import UnionType
# Sentinel for "no type constraint".
WILDCARD: Final[object] = object()


class TypeMatch:
    """Type-hint matching, scoring, and function selection helpers.

    This utility centralizes all logic used to interpret typing hints,
    check whether a runtime value conforms to a hint, and compute a
    numeric specificity score. The score is used to rank overload
    candidates. All methods are pure helpers and side-effect free.
    """

    @staticmethod
    def _resolve_hint(hint: object) -> object:
        """Resolve string and ForwardRef hints into concrete types.

        The resolution is performed against this module's global
        namespace to support self-referential and deferred annotations.

        Args:
            hint: The raw hint object (may be str or ForwardRef).

        Returns:
            The resolved hint if evaluation succeeds; otherwise the
            original `hint` is returned unchanged.
        """
        with suppress(Exception):
            module_dict: Dict[str, Any] = vars(modules[__name__])
            if isinstance(hint, str):
                return eval(hint, module_dict, module_dict)
            if isinstance(hint, ForwardRef):
                return eval(hint.__forward_arg__, module_dict, module_dict)
        return hint

    @staticmethod
    def _is_typevar_like(hint: object) -> bool:
        """Return True if the hint behaves like a TypeVar/ParamSpec.

        Args:
            hint: A typing hint to inspect.

        Returns:
            True when `hint` is a `TypeVar` or `ParamSpec`, else False.
        """
        return isinstance(hint, (TypeVar, ParamSpec))

    @staticmethod
    def _class_distance(a: type, b: type) -> int:
        """Compute distance of type `b` within `a.__mro__`.

        This is used to score class hierarchy proximity. A smaller
        value means `b` is closer to `a` in the MRO.

        Args:
            a: The concrete class used as the reference.
            b: The class to look up within `a.__mro__`.

        Returns:
            Index of `b` within `a.__mro__` if present; a large number
            when `b` is not in the MRO.
        """
        with suppress(Exception):
            return a.__mro__.index(b)
        return 10_000

    @classmethod
    def _is_union_origin(cls, origin: object) -> bool:
        """Return True if `origin` denotes a Union/PEP 604 union.

        Args:
            origin: The origin object from `typing.get_origin`.

        Returns:
            True when the origin represents a Union type.
        """
        return origin is Union or (UnionType is not None
                                   and origin is UnionType)

    @classmethod
    def _kwargs_value_type_from_varkw(cls, annotation: object) -> object:
        """Extract value type from a **kwargs mapping annotation.

        Args:
            annotation: The annotation of a VAR_KEYWORD parameter.

        Returns:
            The value type if the annotation is a mapping with two type
            arguments; otherwise `Any`.
        """
        ann: object = cls._resolve_hint(annotation)
        if get_origin(ann) in (dict, Mapping, ABCMapping, MutableMapping):
            args: Tuple[Any, ...] = get_args(ann)
            if len(args) == 2:
                return args[1]
        return Any

    @classmethod
    def _is_match(cls, value: object, hint: object) -> bool:
        """Return True if `value` conforms to `hint`.

        This function supports a broad subset of typing, including
        `Annotated`, `Literal`, `ClassVar`, `Union` (and PEP 604),
        `Callable` parameter shapes, container origins, protocols, and
        TypedDict-like classes.

        Args:
            value: The runtime value to test.
            hint: The typing hint to validate against.

        Returns:
            True if `value` matches `hint`; otherwise False.
        """
        hint = cls._resolve_hint(hint)
        if hint in (Any, object) or hint is WILDCARD:
            return True
        supertype: Optional[object] = getattr(hint, "__supertype__", None)
        if callable(hint) and supertype is not None:
            return cls._is_match(value, supertype)
        if (isinstance(hint, type) and issubclass(hint, dict)
                and hasattr(hint, "__annotations__")
                and hasattr(hint, "__total__")):
            if not isinstance(value, dict):
                return False
            ann: Dict[str, object] = hint.__annotations__
            for k in getattr(hint, "__required_keys__", set()):
                if k not in value or not cls._is_match(value[k], ann[k]):
                    return False
            return all(not (k in value and not cls._is_match(value[k], ann[k]))
                       for k in getattr(hint, "__optional_keys__", set()))
        if isinstance(hint, type) and getattr(hint, "_is_protocol", False):
            return (isinstance(value, hint)
                    if getattr(hint, "_is_runtime_protocol", False) else False)
        if cls._is_typevar_like(hint):
            if isinstance(hint, TypeVar):
                if hint.__constraints__:
                    return any(
                        cls._is_match(value, c) for c in hint.__constraints__)
                if hint.__bound__ is not None:
                    return cls._is_match(value, hint.__bound__)
            return True
        origin: Optional[type] = get_origin(hint)
        args: Tuple[Any, ...] = get_args(hint)
        if origin is Annotated:
            return cls._is_match(value, args[0])
        if origin is ClassVar:
            return cls._is_match(value, args[0]) if args else True
        if origin is Literal:
            return any(value == lit for lit in args)
        if isinstance(value, type):
            if origin in (Type, type):
                return cls._is_match(value, args[0] if args else Any)
            if origin is None and isinstance(hint, type):
                return issubclass(value, hint)
            return False
        if origin is None:
            if hint in (Tuple, tuple):
                return isinstance(value, tuple)
            if hint in (List, list):
                return isinstance(value, list)
            if hint in (Dict, dict):
                return isinstance(value, dict)
            if hint in (set, frozenset):
                return isinstance(value, (set, frozenset))
            if hint in (type, Type):
                return isinstance(value, type)
            return isinstance(value, hint) if isinstance(hint, type) else False
        if cls._is_union_origin(origin):
            return any(cls._is_match(value, t) for t in args)
        if origin in (Type, type):
            return False
        if origin is ABCCallable:
            if not callable(value):
                return False
            if not args:
                return True
            params_spec: Union[EllipsisType,
                               Tuple[object, ...]] = (args[0] if len(args) >= 1
                                                      else Ellipsis)
            if isinstance(params_spec, EllipsisType):
                return True
            try:
                parameters: MappingProxyType[str, Parameter] = signature(
                    value).parameters
            except Exception:
                return True
            declared: list[object] = []
            has_varargs: bool = False
            for p in parameters.values():
                if p.kind in (
                        Parameter.POSITIONAL_ONLY,
                        Parameter.POSITIONAL_OR_KEYWORD,
                ):
                    declared.append(p.annotation if p.
                                    annotation is not Parameter.empty else Any)
                elif p.kind == Parameter.VAR_POSITIONAL:
                    has_varargs = True
            declared_n: int = len(declared)
            if declared_n < len(params_spec) and not has_varargs:
                return False
            for i, expected_t in enumerate(params_spec):
                if i < declared_n:
                    actual_t: object = declared[i]
                    if (actual_t is not Any and actual_t is not Parameter.empty
                            and not cls._is_match(actual_t, expected_t)):
                        return False
                else:
                    break
            return True
        if origin in (dict, ABCMapping, MutableMapping):
            return (all(
                cls._is_match(k, args[0] if len(args) > 0 else Any)
                and cls._is_match(v, args[1] if len(args) > 1 else Any)
                for k, v in value.items())
                    if isinstance(value, ABCMapping) else False)
        if origin in (Sequence, MutableSequence):
            if not isinstance(value, Sequence):
                return False
            if not args:
                return True
            with suppress(TypeError):
                return all(cls._is_match(x, args[0]) for x in value)
            return False
        if origin in (ABCIterable, ABCCollection) and isinstance(
                value, Iterable):
            return (all(cls._is_match(x, args[0])
                        for x in iter(value)) if args else True)
        if origin in (tuple, list, dict, set, frozenset) and not isinstance(
                value, origin if origin is not frozenset else (frozenset, )):
            return (cls._is_match(value, args[0])
                    if origin is list and args else False)
        if origin is tuple:
            if not isinstance(value, tuple):
                return False
            if len(args) == 2 and args[1] is Ellipsis:
                return all(cls._is_match(v, args[0]) for v in value)
            if len(args) != len(value):
                return False
            return all(
                cls._is_match(v, t) for v, t in zip(value, args, strict=True))
        if origin is list:
            return ((all(
                cls._is_match(x, args[0])
                for x in value) if isinstance(value, list) else cls._is_match(
                    value, args[0])) if args else isinstance(value, list))
        if origin is dict:
            return (all(
                cls._is_match(k, args[0] if len(args) > 0 else Any)
                and cls._is_match(v, args[1] if len(args) > 1 else Any)
                for k, v in value.items())
                    if isinstance(value, dict) else False)
        if origin in (set, frozenset):
            if not isinstance(value, origin) or not isinstance(
                    value, Iterable):
                return False
            if not args:
                return True
            return all(cls._is_match(x, args[0]) for x in value)
        return isinstance(value, origin) if isinstance(origin, type) else False

    @classmethod
    def _type_specificity_score(cls, value: object, hint: object) -> int:
        """Compute a numeric score that reflects match specificity.

        Larger scores indicate a more specific and therefore preferred
        match. The scoring is heuristic and considers constructs such as
        `Literal`, `Annotated`, unions, callables, containers, and class
        hierarchy distance.

        Args:
            value: The runtime value under evaluation.
            hint: The typing hint used for scoring.

        Returns:
            An integer score. Higher is better.
        """
        hint = cls._resolve_hint(hint)
        if hint in (Any, object) or hint is WILDCARD:
            return 0
        supertype: Optional[object] = getattr(hint, "__supertype__", None)
        if callable(hint) and supertype is not None:
            return cls._type_specificity_score(value, supertype) + 1
        if (isinstance(hint, type) and issubclass(hint, dict)
                and hasattr(hint, "__annotations__")
                and hasattr(hint, "__total__")):
            return (25 + 2 * len(getattr(hint, "__required_keys__", set())) +
                    sum(
                        cls._type_specificity_score(value, t)
                        for t in hint.__annotations__.values()))
        if isinstance(hint, type) and getattr(hint, "_is_protocol", False):
            return 14 if getattr(hint, "_is_runtime_protocol", False) else 6
        if cls._is_typevar_like(hint):
            if isinstance(hint, TypeVar):
                if hint.__constraints__:
                    return (max(
                        cls._type_specificity_score(value, c)
                        for c in hint.__constraints__) - 1)
                if hint.__bound__ is not None:
                    return (
                        cls._type_specificity_score(value, hint.__bound__) - 1)
            return 1
        origin: Optional[type] = get_origin(hint)
        args: Tuple[Any, ...] = get_args(hint)
        if origin is Literal:
            return 100
        if origin is Annotated:
            return 1 + cls._type_specificity_score(value, args[0])
        if origin is ClassVar:
            return cls._type_specificity_score(value, args[0]) if args else 1
        if cls._is_union_origin(origin):
            return max([cls._type_specificity_score(value, t)
                        for t in args]) - len(args)
        if origin in (Type, type):
            return (8 if not args else 15 +
                    cls._type_specificity_score(value, args[0]))
        if origin is ABCCallable:
            params_spec: Union[EllipsisType,
                               Tuple[object, ...]] = (args[0] if len(
                                   args or ()) >= 1 else Ellipsis)
            return 12 + (0 if isinstance(params_spec, EllipsisType) else sum(
                cls._type_specificity_score(value, p) for p in params_spec))
        if origin in (dict, ABCMapping, MutableMapping):
            return (20 +
                    sum(cls._type_specificity_score(value, a)
                        for a in args) if isinstance(value, dict) else -50)
        if origin in (Sequence, MutableSequence, ABCIterable, ABCCollection):
            return ((18 +
                     cls._type_specificity_score(value, args[0]) if args else
                     16) if isinstance(value,
                                       (list, tuple, set, frozenset)) else -50)
        if origin and origin in (tuple, list, dict, set, frozenset):
            return ((20 +
                     sum(cls._type_specificity_score(value, a)
                         for a in args)) if isinstance(value, origin) else -50)
        if hint in (Tuple, List, Dict, tuple, list, dict, set, frozenset):
            return 10
        if isinstance(hint, type):
            return 5 + max(
                0,
                50 - cls._class_distance(
                    value if isinstance(value, type) else type(value), hint),
            )
        return 1

    def __new__(
        cls,
        match: Dict[str, object],
        options: list[Callable[..., Any]],
    ) -> list[Callable[..., Any]]:
        """Return overloads that best match the provided argument mapping.

        The function filters `options` by compatibility with `match` and
        then computes a score for each candidate using
        `_type_specificity_score`. All candidates tied for the highest
        score are returned.

        Args:
            match: Mapping from parameter name to runtime value.
            options: List of candidate callables to evaluate.

        Returns:
            A list of callable overloads with the highest score that
            still satisfy type compatibility for all keys in `match`.
        """
        if not match or not options:
            return []
        keys: Tuple[str, ...] = tuple(match.keys())
        ranked: list[Tuple[Callable[..., Any], int]] = []

        def _key_hint(
            k: str,
            params_map: Mapping[str, Parameter],
            kw_param: Optional[Parameter],
            tmap_local: Optional[Mapping[str, Any]],
        ) -> object:
            """Resolve the effective hint for parameter `k`.

            The resolution prefers decorator-provided type maps over the
            function signature, and supports **kwargs value types.

            Args:
                k: Parameter name.
                params_map: Map of parameter names to `Parameter`.
                kw_param: The VAR_KEYWORD parameter if present.
                tmap_local: Optional decorator type map for the function.

            Returns:
                The effective typing hint for `k`.
            """
            if tmap_local and k in tmap_local:
                return cls._resolve_hint(tmap_local[k])
            param: Optional[Parameter] = params_map.get(k)
            if param is None:
                return (cls._kwargs_value_type_from_varkw(kw_param.annotation)
                        if kw_param and kw_param is not Parameter.empty else
                        Any)
            return (param.annotation
                    if param.annotation is not Parameter.empty else Any)

        for func in options:
            params: MappingProxyType[str,
                                     Parameter] = signature(func).parameters
            varkw: Optional[Parameter] = next(
                (p
                 for p in params.values() if p.kind == Parameter.VAR_KEYWORD),
                None,
            )
            tmap: Optional[Mapping[str,
                                   Any]] = getattr(func,
                                                   "__dispatch_type_map__",
                                                   None)
            if not all(
                    cls._is_match(match[k], _key_hint(k, params, varkw, tmap))
                    for k in keys):
                continue
            score: int = sum(
                cls._type_specificity_score(match[k],
                                            _key_hint(k, params, varkw, tmap))
                for k in keys)
            for k in keys:
                p: Optional[Parameter] = params.get(k)
                score += (40 if (cls._resolve_hint(tmap[k] if (
                    tmap and k in tmap) else (p.annotation if (
                        p and p.annotation is not Parameter.empty) else Any)))
                          not in (Any, object) else 20)
            score -= 1000 * sum(1
                                for k in keys if k not in params and not varkw)
            if varkw:
                score -= 1
            if any(p.kind == Parameter.VAR_POSITIONAL
                   for p in params.values()):
                score -= 2
            ranked.append((func, score))
        return [func for func, s in ranked
                if s == max(s for _, s in ranked)] if ranked else []


class WizeDispatcher:
    """Create namespaced decorators to register method/function overloads.

    Instances expose attribute-based decorator factories (e.g.,
    `dispatch.fn`). Each decorator registers a typed overload against an
    existing function or method, keeping the original callable as the
    fallback. Dispatch binds calls using the original signature, ranks
    candidates with `TypeMatch`, and invokes the best match.
    """

    _pending: ClassVar[Dict[str, "WizeDispatcher._OverloadDescriptor"]] = {}

    @dataclass(frozen=True)
    class _Overload:
        """Container for a single overload and its metadata.

        Attributes:
            _func: Wrapped callable that implements the overload.
            _type_map: Effective type map used for dispatch matching.
            _param_order: Parameter order used by the dispatcher.
            _dec_keys: Keys explicitly provided via decorator typing.
            _is_original: True if this entry refers to the fallback.
            _reg_index: Registration order index for tie-breaking.
            _defaults: Overload-defined default values by parameter.
        """
        _func: Callable[..., Any]
        _type_map: Mapping[str, Any]
        _param_order: Tuple[str, ...]
        _dec_keys: FrozenSet[str]
        _is_original: bool
        _reg_index: int
        _defaults: Mapping[str, Any]  # overload-provided defaults per name

    class _BaseRegistry:
        """Common registry logic for function and method targets.

        This class holds the list of overloads, the original callable,
        the bound signature, and a small cache keyed by runtime argument
        types. Subclasses specialize receiver handling.
        """
        _target_name: str
        _original: Callable[..., Any]
        _sig: Signature
        _param_order: Tuple[str, ...]
        _overloads: list["WizeDispatcher._Overload"]
        _cache: Dict[Tuple[Type[Any], ...], Callable[..., Any]]
        _reg_counter: int
        _skip_first: bool

        def __init__(
            self,
            *,
            target_name: str,
            original: Callable[..., Any],
            skip_first: bool,
        ) -> None:
            """Initialize registry for a target function or method.

            Args:
                target_name: Name of the target attribute/function.
                original: The original callable kept as fallback.
                skip_first: Whether to skip the first param when binding
                    (True for instance/class methods and setters).
            """
            self._target_name = target_name
            self._original = original
            self._sig = signature(obj=original)
            self._skip_first = skip_first
            self._param_order = WizeDispatcher._param_order(
                sig=self._sig, skip_first=skip_first)
            self._overloads = []
            self._cache = {}
            self._reg_counter = 0

        def _bind(
            self,
            instance: Any | None,
            args: Tuple[Any, ...],
            kwargs: Dict[str, Any],
        ) -> Tuple[BoundArguments, FrozenSet[str]]:
            """Bind a call to the original signature and add defaults.

            Args:
                instance: Receiver for methods; None for free functions.
                args: Positional arguments provided by the caller.
                kwargs: Keyword arguments provided by the caller.

            Returns:
                A tuple of `(bound_args, provided_keys)` where
                `bound_args` is a `BoundArguments` with defaults applied,
                and `provided_keys` are the names present in the call.
            """
            raw: BoundArguments = (self._sig.bind(instance, *args, **kwargs)
                                   if self._skip_first else self._sig.bind(
                                       *args, **kwargs))
            raw.apply_defaults()
            return raw, frozenset(n for n in self._param_order
                                  if n in raw.arguments)

        def _arg_types(self, bound: BoundArguments) -> Tuple[Type[Any], ...]:
            """Return the runtime types for parameters in dispatch order.

            Args:
                bound: Bound arguments produced by `_bind`.

            Returns:
                A tuple of concrete runtime types per parameter.
            """
            return tuple(
                type(bound.arguments[name]) for name in self._param_order)

        @staticmethod
        def _make_adapter(
            func: Callable[...,
                           Any]) -> Tuple[Callable[..., Any], Dict[str, Any]]:
            """Wrap `func` so it can be called with the full kwargs map.

            The adapter allows bodies that omit parameters in their
            signature to still reference those names. Missing names are
            injected temporarily into the function's globals.

            Args:
                func: The overload function to adapt.

            Returns:
                A tuple `(adapter, defaults)` where `adapter` is a
                callable with the same semantics as `func` but tolerant
                to extra kwargs, and `defaults` maps each declared
                parameter to its default value if present.
            """
            param: MappingProxyType[str,
                                    Parameter] = signature(func).parameters

            def adapter(*_a: Any, **all_named: Any) -> Any:
                """Invoke `func`, injecting undeclared names as globals.

                The adapter extracts arguments in the function's own
                declared order, passes keyword-only arguments directly,
                forwards unknown keywords if `**kwargs` is declared, and
                temporarily adds extra names to `func.__globals__`.
                """
                # Build args/kwargs for declared params
                kwargs_pass: Dict[str, Any] = {
                    n: all_named[n]
                    for n in [
                        p.name for p in param.values()
                        if p.kind == Parameter.KEYWORD_ONLY
                    ] if n in all_named
                }
                if any(p.kind == Parameter.VAR_KEYWORD
                       for p in param.values()):
                    for k, v in all_named.items():
                        if k not in param:
                            kwargs_pass[k] = v

                globalns: Dict[str, Any] = func.__globals__
                injected: Dict[str, Tuple[bool, Any]] = {}
                try:
                    for k, v in all_named.items():
                        if k not in param:
                            injected[k] = (True,
                                           globalns[k]) if k in globalns else (
                                               False, None)
                            globalns[k] = v
                    return func(
                        *[
                            all_named[n] for n in [
                                p.name for p in param.values()
                                if p.kind in (Parameter.POSITIONAL_ONLY,
                                              Parameter.POSITIONAL_OR_KEYWORD)
                            ] if n in all_named
                        ], **kwargs_pass)
                finally:
                    for k, (had, old) in injected.items():
                        if had:
                            globalns[k] = old
                        else:
                            del globalns[k]

            return update_wrapper(adapter, func), {
                p.name: p.default
                for p in param.values() if p.default is not Parameter.empty
            }

        def _invoke(self, func: Callable[..., Any],
                    bound: BoundArguments) -> Any:
            """Invoke `func` using the full bound argument mapping.

            The adapter produced by `_make_adapter` ignores extraneous
            names, so we always pass the complete mapping.

            Args:
                func: The chosen callable to invoke.
                bound: Bound arguments with defaults applied.

            Returns:
                The callable's return value.
            """
            # We always pass the full named argument map; adapters trim it.
            return func(**dict(bound.arguments))

        def _dispatch(
            self,
            *,
            instance: Any | None,
            args: Tuple[Any, ...],
            kwargs: Dict[str, Any],
        ) -> Any:
            """Select the best overload and invoke it.

            The call is bound to the original signature, defaults are
            applied, runtime values are scored against each overload's
            effective hints, and the best-scoring compatible candidate
            is executed.

            Args:
                instance: Receiver for methods or None for functions.
                args: Positional arguments.
                kwargs: Keyword arguments.

            Returns:
                The result of the selected callable.
            """
            bound, provided = self._bind(instance, args, kwargs)
            types_key: Tuple[Type[Any], ...] = self._arg_types(bound)
            chosen: Optional[Callable[..., Any]]
            if (chosen := self._cache.get(types_key)) is not None:
                return self._invoke(chosen, bound)
            keys: Tuple[str, ...] = self._param_order
            best_score: Optional[int] = None
            best_func: Optional[Callable[..., Any]] = None

            def key_hint(
                param_name: str,
                params_map: Mapping[str, Parameter],
                kw_param: Optional[Parameter],
                tmap_local: Optional[Mapping[str, Any]],
            ) -> object:
                """Resolve the effective hint for parameter `param_name`.

                Prefers decorator-provided type map entries over the
                function annotation. Falls back to **kwargs value types.

                Args:
                    param_name: Parameter name.
                    params_map: Map of parameter names to `Parameter`.
                    kw_param: The VAR_KEYWORD parameter if present.
                    tmap_local: Optional decorator type map for `func`.

                Returns:
                    The effective typing hint for `param_name`.
                """
                if tmap_local and param_name in tmap_local:
                    return TypeMatch._resolve_hint(tmap_local[param_name])
                param: Optional[Parameter] = params_map.get(k)
                if param is None:
                    return (TypeMatch._kwargs_value_type_from_varkw(
                        kw_param.annotation) if kw_param
                            and kw_param is not Parameter.empty else Any)
                return (param.annotation
                        if param.annotation is not Parameter.empty else Any)

            # Evaluate each overload with candidate-specific defaults
            for ov in self._overloads:
                # Per-candidate value selection: use overload default if
                # the caller didn't provide this argument.
                def val_for(k: str, ov: WizeDispatcher._Overload = ov) -> Any:
                    """Return the matching-time value for parameter `k`.

                    Values come from the bound call unless the overload
                    defines a default for `k`, in which case the default
                    is used for matching.
                    """
                    return ov._defaults[
                        k] if k in ov._defaults else bound.arguments[k]

                func: Callable[..., Any] = ov._func
                params: MappingProxyType[str, Parameter] = signature(
                    func).parameters
                varkw: Optional[Parameter] = next(
                    (p for p in params.values()
                     if p.kind == Parameter.VAR_KEYWORD), None)
                tmap: Optional[Mapping[str, Any]] = getattr(
                    func, "__dispatch_type_map__", None)
                # Eligibility check
                if not all(
                        TypeMatch._is_match(val_for(k),
                                            key_hint(k, params, varkw, tmap))
                        for k in keys):
                    continue
                # Scoring (mirrors TypeMatch.__new__ logic; no penalty for
                # omitted params because adapters accept full kwargs)
                score: int = 0
                for k in keys:
                    hint: object = key_hint(k, params, varkw, tmap)
                    score += TypeMatch._type_specificity_score(
                        val_for(k),
                        hint) + (40 if TypeMatch._resolve_hint(hint)
                                 not in (Any, object) else 20)
                if any(p.kind == Parameter.VAR_POSITIONAL
                       for p in params.values()):
                    score -= 2
                if best_score is None or score > best_score:
                    best_score, best_func = score, func
            chosen = best_func or self._original
            self._cache[types_key] = chosen
            return self._invoke(chosen, bound)

        def register(
            self,
            *,
            func: Callable[..., Any],
            type_map: Mapping[str, Any],
            dec_keys: FrozenSet[str],
            is_original: bool,
            reg_index_override: Optional[int] = None,
        ) -> None:
            """Register an overload against this registry.

            The function is wrapped by `_make_adapter` so it can accept
            the full kwargs map. The resulting metadata is appended to
            the overload list and the dispatch cache is cleared.

            Args:
                func: The overload function to register.
                type_map: Effective type map for dispatch matching.
                dec_keys: Keys explicitly provided by the decorator.
                is_original: True when `func` is the fallback callable.
                reg_index_override: Optional explicit registration index.
            """
            attr_str: str = "__dispatch_type_map__"
            wrapped: Any
            defaults: Dict[str, Any]
            wrapped, defaults = self._make_adapter(func)
            setattr(wrapped, attr_str, dict(type_map))
            self._overloads.append(
                WizeDispatcher._Overload(
                    _func=wrapped,
                    _type_map=type_map,
                    _param_order=self._param_order,
                    _dec_keys=dec_keys,
                    _is_original=is_original,
                    _reg_index=(reg_index_override if reg_index_override
                                is not None else self._reg_counter),
                    _defaults=defaults,
                ))
            self._reg_counter += 1
            self._cache.clear()

    class _MethodRegistry(_BaseRegistry):
        """Registry specialization for methods and property setters."""

        def __init__(
            self,
            *,
            target_name: str,
            original: Callable[..., Any],
            has_receiver: bool,
        ) -> None:
            """Initialize a method registry.

            Args:
                target_name: Name of the target method/property.
                original: The original method or accessor function.
                has_receiver: True for instance/class methods and
                    property setters; False for static methods.
            """
            super().__init__(
                target_name=target_name,
                original=original,
                skip_first=has_receiver,
            )

    class _FunctionRegistry(_BaseRegistry):
        """Registry specialization for top-level free functions."""

        def __init__(self, *, target_name: str,
                     original: Callable[..., Any]) -> None:
            """Initialize a function registry.

            Args:
                target_name: Name of the target function.
                original: The original function kept as fallback.
            """
            super().__init__(target_name=target_name,
                             original=original,
                             skip_first=False)

    class _OverloadDescriptor:
        """Descriptor that queues method overloads during class creation.

        Overloads declared inside a class body are collected here and
        materialized when the owner class is finalized (`__set_name__`).
        """
        _queues: Dict[
            str,
            list[Tuple[Callable[..., Any], Dict[str, Any], Tuple[Any, ...]]],
        ]

        def __init__(self) -> None:
            """Initialize an empty queue of pending overload entries."""
            self._queues = {}

        def __set_name__(self, owner: Type[Any], _own_name: str) -> None:
            """Finalize queued registrations for the owning class.

            This creates or reuses a `_MethodRegistry`, registers the
            fallback signature, wraps the target attribute to dispatch,
            and then registers all queued overloads.

            Args:
                owner: The class that now owns this descriptor.
                _own_name: The attribute name used on the class.
            """
            attr_str: str = "__dispatch_registry__"
            reg_map: Dict[str, WizeDispatcher._MethodRegistry] = getattr(
                owner, attr_str, {})
            if not hasattr(owner, attr_str):
                setattr(owner, attr_str, reg_map)
            reg: WizeDispatcher._MethodRegistry
            for target_name, items in self._queues.items():
                if target_name not in reg_map:
                    original_attr: Any = owner.__dict__.get(target_name)
                    has_receiver: bool = True
                    original_func: Callable[..., Any]
                    if (isinstance(original_attr, property)
                            and original_attr.fget):
                        original_func = (original_attr.fset
                                         or original_attr.fget)
                    elif isinstance(original_attr,
                                    (classmethod, staticmethod)):
                        original_func = original_attr.__func__
                        has_receiver = isinstance(original_attr, classmethod)
                    elif callable(original_attr):
                        original_func = original_attr
                    else:
                        original_func = items[-1][0]
                    reg = reg_map[target_name] = (
                        WizeDispatcher._MethodRegistry(
                            target_name=target_name,
                            original=original_func,
                            has_receiver=has_receiver,
                        ))
                    reg.register(
                        func=original_func,
                        type_map={
                            n:
                            WizeDispatcher._resolve_hints(
                                func=original_func,
                                globalns=getattr(original_func, "__wrapped__",
                                                 original_func).__globals__,
                                localns=owner.__dict__,
                            ).get(n, WILDCARD)
                            for n in reg._param_order
                        },
                        dec_keys=frozenset(),
                        is_original=True,
                        reg_index_override=-1,
                    )

                    def _wrap_inst(self: Any,
                                   *a: Any,
                                   reg=reg,
                                   **k: Any) -> Any:
                        """Bound method wrapper that forwards to dispatch."""
                        return reg._dispatch(instance=self, args=a, kwargs=k)

                    selected_func: Union[property, classmethod,
                                         Callable[..., Any]] = _wrap_inst
                    if isinstance(original_attr, property):
                        selected_func = original_attr.setter(
                            lambda self_, value, _reg=reg: _reg._dispatch(
                                instance=self_, args=(value, ), kwargs={}))
                    elif isinstance(original_attr, classmethod):
                        selected_func = classmethod(selected_func)
                    elif isinstance(original_attr, staticmethod):
                        selected_func = staticmethod(
                            lambda *a, _reg=reg, **k: _reg._dispatch(
                                instance=None, args=a, kwargs=k))
                    setattr(owner, target_name, selected_func)
                reg = getattr(owner, attr_str)[target_name]
                # Fallback annotations from the original (for merging)
                fb_ann: Dict[str, Any] = WizeDispatcher._resolve_hints(
                    func=reg._original,
                    globalns=reg._original.__globals__,
                    localns=owner.__dict__,
                )
                for func, decorator_types, decorator_pos in items:
                    if not getattr(func, "__qualname__",
                                   "").startswith(owner.__qualname__ + "."):
                        continue
                    dec_types: Dict[str, Any] = {
                        **{
                            v: decorator_pos[i]
                            for i, v in enumerate(reg._param_order) if \
                            i < len(decorator_pos)
                        },
                        **decorator_types,
                    }
                    reg.register(
                        func=func,
                        type_map=WizeDispatcher._merge_types(
                            order=reg._param_order,
                            decorator_types=dec_types,
                            fn_ann=WizeDispatcher._resolve_hints(
                                func=func,
                                globalns=func.__globals__,
                                localns=owner.__dict__,
                            ),
                            fallback_ann=fb_ann,
                        ),
                        dec_keys=frozenset(dec_types.keys()),
                        is_original=False,
                    )
            WizeDispatcher._pending.pop(owner.__qualname__, None)

        def __get__(self, instance: Any, owner: Optional[type] = None) -> Self:
            """Return the descriptor itself (not a bound object)."""
            return self

        def _add(
            self,
            *,
            target_name: str,
            func: Callable[..., Any],
            decorator_types: Dict[str, Any],
            decorator_pos: Tuple[Any, ...],
        ) -> None:
            """Queue an overload declared within a class body.

            Args:
                target_name: Name of the target attribute.
                func: The function object being decorated.
                decorator_types: Mapping of explicit decorator types.
                decorator_pos: Positional decorator types in order.
            """
            self._queues.setdefault(target_name, []).append(
                (func, dict(decorator_types), tuple(decorator_pos)))

    @staticmethod
    def _param_order(*, sig: Signature, skip_first: bool) -> Tuple[str, ...]:
        """Compute parameter order used during dispatch.

        Args:
            sig: Signature of the original callable.
            skip_first: Whether to drop the first parameter (e.g., `self`).

        Returns:
            A tuple of parameter names in evaluation order.
        """
        params: list[Parameter] = list(sig.parameters.values())
        if skip_first and params:
            params = params[1:]
        return tuple(p.name for p in params)

    @staticmethod
    def _register_function_overload(
            *,
            target_name: str,
            func: Callable[..., Any],
            decorator_types: Mapping[str, Any],
            decorator_pos: Tuple[Any, ...] = (),
    ) -> Callable[..., Any]:
        """Register an overload for a top-level function target.

        This ensures the target function is wrapped with a dispatcher
        and adds the provided overload with merged type information.

        Args:
            target_name: Name of the existing function to overload.
            func: Overload function object to register.
            decorator_types: Mapping of explicit decorator types.
            decorator_pos: Positional decorator types by parameter order.

        Returns:
            Either the wrapped target function (when replacing the
            original symbol) or the original `func`.
        """
        mod: ModuleType = modules[func.__module__]
        mod_dict: Dict[str, Any] = mod.__dict__
        attr_str: str = "__fdispatch_registry__"
        wrap_attr: str = "__fdispatch_wrapper__"
        if not hasattr(mod, attr_str):
            setattr(mod, attr_str, {})
        regmap: Dict[str, WizeDispatcher._FunctionRegistry] = getattr(
            mod, attr_str)
        target: Optional[Callable[..., Any]] = mod_dict.get(target_name)
        if target is None or not callable(target):
            raise AttributeError(f"Function '{target_name}' "
                                 "must exist before registering overloads")
        reg: WizeDispatcher._FunctionRegistry
        if target_name not in regmap:
            regmap[target_name] = WizeDispatcher._FunctionRegistry(
                target_name=target_name, original=target)
            wrapped: Callable[..., Any] = update_wrapper(
                lambda *a, **k: regmap[target_name]._dispatch(
                    instance=None, args=a, kwargs=k),
                target,
            )
            setattr(wrapped, wrap_attr, True)
            mod_dict[target_name] = wrapped
        else:
            current: Callable[..., Any] = mod_dict[target_name]
            if not getattr(current, wrap_attr, False):
                reg = regmap[target_name]
                reg._original = current
                reg._sig = signature(obj=current)
                reg._param_order = tuple(
                    p.name for p in signature(obj=current).parameters.values())
                if not reg._overloads:
                    reg._overloads = []
                    reg._cache = {}
                    reg._reg_counter = 0
                reg.register(
                    func=current,
                    type_map={
                        n:
                        WizeDispatcher._resolve_hints(func=current,
                                                      globalns=mod_dict).get(
                                                          n, WILDCARD)
                        for n in reg._param_order
                    },
                    dec_keys=frozenset(),
                    is_original=True,
                    reg_index_override=-1,
                )
                wrapped = update_wrapper(
                    lambda *a, **k: reg._dispatch(
                        instance=None, args=a, kwargs=k),
                    current,
                )
                setattr(wrapped, wrap_attr, True)
                mod_dict[target_name] = wrapped
        reg = regmap[target_name]
        dec_types: Dict[str, Any] = {
            **{
                name: decorator_pos[i]
                for i, name in enumerate(reg._param_order) if \
                i < len(decorator_pos)
            },
            **decorator_types,
        }
        reg.register(
            func=func,
            type_map=WizeDispatcher._merge_types(
                order=reg._param_order,
                decorator_types=dec_types,
                fn_ann=WizeDispatcher._resolve_hints(func=func,
                                                     globalns=mod_dict),
                fallback_ann=WizeDispatcher._resolve_hints(func=reg._original,
                                                           globalns=mod_dict),
            ),
            dec_keys=frozenset(dec_types.keys()),
            is_original=False,
        )
        return mod_dict[target_name] if func.__name__ == target_name else func

    @staticmethod
    def _resolve_hints(
        *,
        func: Callable[..., Any],
        globalns: Optional[Mapping[str, Any]] = None,
        localns: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resolve annotations for `func` using provided namespaces.

        Args:
            func: The function whose annotations will be resolved.
            globalns: Optional globals mapping to use for evaluation.
            localns: Optional locals mapping to use for evaluation.

        Returns:
            A name-to-annotation mapping with all forward references
            evaluated to concrete objects where possible.
        """
        return get_type_hints(
            obj=func,
            globalns=(func.__globals__ if globalns is None else (
                globalns if isinstance(globalns, dict) else dict(globalns))),
            localns=(None if localns is None else (
                localns if isinstance(localns, dict) else dict(localns))),
        )

    @staticmethod
    def _merge_types(
        *,
        order: Tuple[str, ...],
        decorator_types: Mapping[str, Any],
        fn_ann: Mapping[str, Any],
        fallback_ann: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Merge decorator, function, and fallback annotations.

        The precedence is: decorator types > function annotations >
        fallback annotations > wildcard.

        Args:
            order: Parameter names in dispatch order.
            decorator_types: Types explicitly provided by decorator.
            fn_ann: Resolved annotations from the overload function.
            fallback_ann: Resolved annotations from the fallback.

        Returns:
            A dict mapping parameter names to the effective types.
        """
        return {
            name: (decorator_types[name] if name in decorator_types else
                   (fn_ann[name] if name in fn_ann else
                    (fallback_ann or {}).get(name, WILDCARD)))
            for name in order
        }

    def __getattr__(self, target_name: str):
        """Create a decorator factory bound to `target_name`.

        The returned callable supports three forms:
        - `@dispatch.name` (use function annotations)
        - `@dispatch.name(int, str)` (positional types)
        - `@dispatch.name(a=int)` (keyword types)
        """

        def _extract_func(obj):
            """Return the underlying function for class/static methods.

            Args:
                obj: A function, `classmethod`, or `staticmethod`.

            Returns:
                The raw function object.
            """
            return obj.__func__ if isinstance(obj, (classmethod,
                                                    staticmethod)) else obj

        def _decorator_factory(*decorator_args, **decorator_kwargs):
            """Return a decorator that registers an overload.

            Positional arguments map to parameters by position, and
            keyword arguments map by name. When used as a bare decorator,
            the function's own annotations are used.
            """

            def _queue_or_register(*, func, decorator_types, decorator_pos):
                """Queue or immediately register an overload.

                Overloads defined inside a class body are queued and
                materialized by `_OverloadDescriptor.__set_name__`. Free
                functions are registered immediately.

                Args:
                    func: The function being decorated.
                    decorator_types: Mapping of types by parameter name.
                    decorator_pos: Positional types by parameter order.

                Returns:
                    A descriptor (for class scope) or the possibly
                    replaced function (for free functions).
                """
                qual: str = getattr(func, "__qualname__", "")
                if "." in qual:
                    owner_qual: str = qual.split(".", 1)[0]
                    desc: Any = WizeDispatcher._pending.get(owner_qual)
                    if desc is None:
                        desc = self._OverloadDescriptor()
                        WizeDispatcher._pending[owner_qual] = desc
                    desc._add(
                        target_name=target_name,
                        func=func,
                        decorator_types=dict(decorator_types),
                        decorator_pos=tuple(decorator_pos),
                    )
                    return desc
                return self._register_function_overload(
                    target_name=target_name,
                    func=func,
                    decorator_types=dict(decorator_types),
                    decorator_pos=tuple(decorator_pos),
                )

            return _queue_or_register(
                func=_extract_func(decorator_args[0]),
                decorator_types={},
                decorator_pos=(),
            ) if (len(decorator_args) == 1 and not decorator_kwargs and
                  (hasattr(decorator_args[0], "__code__")
                   or isinstance(decorator_args[0],
                                 (classmethod, staticmethod)))
                  ) else lambda func: _queue_or_register(
                      func=_extract_func(func),
                      decorator_types=decorator_kwargs,
                      decorator_pos=tuple(decorator_args),
                  )

        return _decorator_factory


dispatch: Final[WizeDispatcher] = WizeDispatcher()
