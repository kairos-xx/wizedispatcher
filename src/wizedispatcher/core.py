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
from types import MappingProxyType, ModuleType
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

try:
    from .typingnormalize import TypingNormalize
except Exception:  # pragma: no cover
    # Permit running this file as a script (no package context)
    from typingnormalize import TypingNormalize  # type: ignore[reportMissingImports]

UnionType: Optional[Any] = None
with suppress(Exception):
    from types import UnionType

# Sentinel for "no type constraint".
WILDCARD: Final[object] = object()


class TypeMatch:
    """Type-hint matching, scoring, and function selection helpers.

    This utility centralizes the logic used to interpret typing hints,
    to check runtime values against hints, and to compute a numeric
    specificity score that ranks overload candidates.
    """

    @staticmethod
    def _resolve_hint(hint: object) -> object:
        """Resolve string/ForwardRef hints into concrete objects.

        Args:
            hint: Raw hint (may be a string or ForwardRef).

        Returns:
            The resolved object if evaluation succeeds; otherwise the
            original hint.
        """
        with suppress(Exception):
            module_dict: Dict[str, Any] = vars(modules[__name__])
            if isinstance(hint, str):
                return TypingNormalize(eval(hint, module_dict, module_dict))
            if isinstance(hint, ForwardRef):
                return TypingNormalize(
                    eval(hint.__forward_arg__, module_dict, module_dict)
                )
        # Fall back to returning a normalized form when possible
        with suppress(Exception):
            return TypingNormalize(hint)
        return hint

    @staticmethod
    def _is_typevar_like(hint: object) -> bool:
        """Return True if hint behaves like a TypeVar/ParamSpec.

        Args:
            hint: A typing hint.

        Returns:
            True when the hint is a TypeVar or ParamSpec; else False.
        """
        return isinstance(hint, (TypeVar, ParamSpec))

    @staticmethod
    def _class_distance(a: type, b: type) -> int:
        """Return distance of class `b` within `a.__mro__`.

        Args:
            a: The reference class.
            b: The class to locate inside `a.__mro__`.

        Returns:
            Index of `b` in `a.__mro__` (0 for exact) or a large value
            when not present.
        """
        with suppress(Exception):
            return a.__mro__.index(b)
        return 10_000

    @classmethod
    def _is_union_origin(cls, origin: object) -> bool:
        """Return True if `origin` denotes a Union/PEP 604 union.

        Args:
            origin: Result of `typing.get_origin`.

        Returns:
            True when the origin represents a union type.
        """
        return origin is Union or (UnionType is not None and origin is UnionType)

    @classmethod
    def _kwargs_value_type_from_varkw(cls, annotation: object) -> object:
        """Extract the **kwargs value type from a mapping annotation.

        Args:
            annotation: The annotation of a VAR_KEYWORD parameter.

        Returns:
            Value type if two type args are present; otherwise Any.
        """
        ann: object = cls._resolve_hint(annotation)
        if get_origin(ann) in (dict, Mapping, ABCMapping, MutableMapping):
            args: Tuple[Any, ...] = get_args(ann)
            if len(args) == 2:
                return args[1]
        return Any

    @classmethod
    def _is_match(cls, value: object, hint: object) -> bool:
        """Return True if `value` conforms to typing `hint`.

        Supports Annotated, Literal, ClassVar, Union/PEP 604, Callable
        parameter shapes, container origins, protocols, and
        TypedDict-like classes.

        Args:
            value: Runtime value to validate.
            hint: Typing hint to match against.

        Returns:
            True if value matches the hint, False otherwise.
        """
        hint = cls._resolve_hint(hint)
        if hint in (Any, object) or hint is WILDCARD:
            return True
        supertype: Optional[object] = getattr(hint, "__supertype__", None)
        if callable(hint) and supertype is not None:
            return cls._is_match(value, supertype)
        if (
            isinstance(hint, type)
            and issubclass(hint, dict)
            and hasattr(hint, "__annotations__")
            and hasattr(hint, "__total__")
        ):
            if not isinstance(value, dict):
                return False
            ann: Dict[str, object] = hint.__annotations__
            for k in getattr(hint, "__required_keys__", set()):
                if k not in value or not cls._is_match(value[k], ann[k]):
                    return False
            return all(
                not (k in value and not cls._is_match(value[k], ann[k]))
                for k in getattr(hint, "__optional_keys__", set())
            )
        if isinstance(hint, type) and getattr(hint, "_is_protocol", False):
            return (
                isinstance(value, hint)
                if getattr(hint, "_is_runtime_protocol", False)
                else False
            )
        if cls._is_typevar_like(hint):
            if isinstance(hint, TypeVar):
                if hint.__constraints__:
                    return any(cls._is_match(value, c) for c in hint.__constraints__)
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
            # Value must be callable.
            if not callable(value):
                return False
            # Bare Callable without args always matches.
            if not args:
                return True
            # Extract the parameter spec from typing.Callable[[...], R] or Callable[..., R].
            params_spec: object = args[0] if len(args) >= 1 else Ellipsis
            # Ellipsis or ParamSpec/Concatenate-like → accept any parameter shape.
            if params_spec is Ellipsis or not isinstance(params_spec, list):
                return True
            # Otherwise we have a concrete parameter type list to check positionally.
            try:
                parameters: MappingProxyType[str, Parameter] = signature(
                    value
                ).parameters
            except Exception:
                # Opaque/builtins: consider it a match if it's callable
                return True
            declared: list[object] = []
            has_varargs: bool = False
            for p in parameters.values():
                if p.kind in (
                    Parameter.POSITIONAL_ONLY,
                    Parameter.POSITIONAL_OR_KEYWORD,
                ):
                    declared.append(
                        p.annotation if p.annotation is not Parameter.empty else Any
                    )
                elif p.kind == Parameter.VAR_POSITIONAL:
                    has_varargs = True
            declared_n: int = len(declared)
            # Require the callable to accept at least the expected number of positional params
            # unless it declares varargs.
            if declared_n < len(params_spec) and not has_varargs:
                return False
            for idx, expected_t in enumerate(params_spec):
                if idx >= declared_n:
                    break
                actual_t: object = declared[idx]
                if (
                    actual_t is not Any
                    and actual_t is not Parameter.empty
                    and not cls._is_match(actual_t, expected_t)
                ):
                    return False
            return True
        if origin in (dict, ABCMapping, MutableMapping):
            return (
                all(
                    cls._is_match(k, args[0] if len(args) > 0 else Any)
                    and cls._is_match(v, args[1] if len(args) > 1 else Any)
                    for k, v in value.items()
                )
                if isinstance(value, ABCMapping)
                else False
            )
        if origin in (Sequence, MutableSequence):
            if not isinstance(value, Sequence):
                return False
            if not args:
                return True
            with suppress(TypeError):
                return all(cls._is_match(x, args[0]) for x in value)
            return False
        if origin in (ABCIterable, ABCCollection) and isinstance(value, Iterable):
            return all(cls._is_match(x, args[0]) for x in iter(value)) if args else True
        if origin in (tuple, list, dict, set, frozenset) and not isinstance(
            value, origin if origin is not frozenset else (frozenset,)
        ):
            return cls._is_match(value, args[0]) if origin is list and args else False
        if origin is tuple:
            if not isinstance(value, tuple):
                return False  # pragma: no cover
            if len(args) == 2 and args[1] is Ellipsis:
                return all(cls._is_match(v, args[0]) for v in value)
            if len(args) != len(value):
                return False
            return all(cls._is_match(v, t) for v, t in zip(value, args, strict=True))
        if origin is list:
            return (
                (
                    all(cls._is_match(x, args[0]) for x in value)
                    if isinstance(value, list)
                    else cls._is_match(value, args[0])
                )
                if args
                else isinstance(value, list)
            )
        if origin is dict:
            return (
                all(
                    cls._is_match(k, args[0] if len(args) > 0 else Any)
                    and cls._is_match(v, args[1] if len(args) > 1 else Any)
                    for k, v in value.items()
                )
                if isinstance(value, dict)
                else False
            )
        if origin in (set, frozenset):
            if not isinstance(value, origin) or not isinstance(value, Iterable):
                return False
            if not args:
                return True
            return all(cls._is_match(x, args[0]) for x in value)
        return isinstance(value, origin) if isinstance(origin, type) else False

    @classmethod
    def _type_specificity_score(cls, value: object, hint: object) -> int:
        """Return a heuristic score for how specific a match would be.

        Args:
            value: Runtime value to consider.
            hint: Typing hint to score.

        Returns:
            Integer score where larger values indicate more specific
            matches.
        """
        hint = cls._resolve_hint(hint)
        if hint in (Any, object) or hint is WILDCARD:
            return 0
        supertype: Optional[object] = getattr(hint, "__supertype__", None)
        if callable(hint) and supertype is not None:
            return cls._type_specificity_score(value, supertype) + 1
        if (
            isinstance(hint, type)
            and issubclass(hint, dict)
            and hasattr(hint, "__annotations__")
            and hasattr(hint, "__total__")
        ):
            return (
                25
                + 2 * len(getattr(hint, "__required_keys__", set()))
                + sum(
                    cls._type_specificity_score(value, t)
                    for t in hint.__annotations__.values()
                )
            )
        if isinstance(hint, type) and getattr(hint, "_is_protocol", False):
            return 14 if getattr(hint, "_is_runtime_protocol", False) else 6
        if cls._is_typevar_like(hint):
            if isinstance(hint, TypeVar):
                if hint.__constraints__:
                    return (
                        max(
                            cls._type_specificity_score(value, c)
                            for c in hint.__constraints__
                        )
                        - 1
                    )
                if hint.__bound__ is not None:
                    return cls._type_specificity_score(value, hint.__bound__) - 1
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
            return max([cls._type_specificity_score(value, t) for t in args]) - len(
                args
            )
        if origin in (Type, type):
            return 8 if not args else 15 + cls._type_specificity_score(value, args[0])
        if origin is ABCCallable:
            params_spec: Union[ellipsis, Tuple[object, ...]] = (
                args[0] if len(args or ()) >= 1 else Ellipsis
            )
            return 12 + (
                sum(cls._type_specificity_score(value, p) for p in params_spec)
                if isinstance(params_spec, tuple)
                else 0
            )
        if origin in (dict, ABCMapping, MutableMapping):
            return (
                20 + sum(cls._type_specificity_score(value, a) for a in args)
                if isinstance(value, dict)
                else -50
            )
        if origin in (Sequence, MutableSequence, ABCIterable, ABCCollection):
            return (
                (18 + cls._type_specificity_score(value, args[0]) if args else 16)
                if isinstance(value, (list, tuple, set, frozenset))
                else -50
            )
        if origin and origin in (tuple, list, dict, set, frozenset):
            return (
                20 + sum(cls._type_specificity_score(value, a) for a in args)
                if isinstance(value, origin)
                else -50
            )
        if hint in (Tuple, List, Dict, tuple, list, dict, set, frozenset):
            return 10
        if isinstance(hint, type):
            return 5 + max(
                0,
                50
                - cls._class_distance(
                    value if isinstance(value, type) else type(value), hint
                ),
            )
        return 1

    def __new__(
        cls,
        match: Dict[str, object],
        options: list[Callable[..., Any]],
    ) -> list[Callable[..., Any]]:
        """Return the highest-scoring overloads compatible with `match`.

        Args:
            match: Mapping param name -> runtime value.
            options: Candidate callables to evaluate.

        Returns:
            All candidates tied for the highest score that are compatible
            with the provided values.
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
            """Return the effective hint for parameter `k`.

            Prefers decorator-provided mapping; falls back to signature
            annotation or **kwargs value type.
            """
            if tmap_local and k in tmap_local:
                return cls._resolve_hint(tmap_local[k])
            param: Optional[Parameter] = params_map.get(k)
            if param is None:
                return (
                    cls._kwargs_value_type_from_varkw(kw_param.annotation)
                    if kw_param and kw_param is not Parameter.empty
                    else Any
                )
            return param.annotation if param.annotation is not Parameter.empty else Any

        for func in options:
            params: MappingProxyType[str, Parameter] = signature(func).parameters
            varkw: Optional[Parameter] = next(
                (p for p in params.values() if p.kind == Parameter.VAR_KEYWORD),
                None,
            )
            tmap: Optional[Mapping[str, Any]] = getattr(
                func, "__dispatch_type_map__", None
            )
            if not all(
                cls._is_match(match[k], _key_hint(k, params, varkw, tmap)) for k in keys
            ):
                continue
            score: int = sum(
                cls._type_specificity_score(match[k], _key_hint(k, params, varkw, tmap))
                for k in keys
            )
            for k in keys:
                p: Optional[Parameter] = params.get(k)
                score += (
                    40
                    if (
                        cls._resolve_hint(
                            tmap[k]
                            if (tmap and k in tmap)
                            else (
                                p.annotation
                                if (p and p.annotation is not Parameter.empty)
                                else Any
                            )
                        )
                        not in (Any, object)
                    )
                    else 20
                )
            score -= 1000 * sum(1 for k in keys if k not in params and not varkw)
            if varkw:
                score -= 1
            if any(p.kind == Parameter.VAR_POSITIONAL for p in params.values()):
                score -= 2
            ranked.append((func, score))
        return (
            [func for func, s in ranked if s == max(s for _, s in ranked)]
            if ranked
            else []
        )


class WizeDispatcher:
    """Create namespaced decorators to register method/function overloads.

    Instances expose attribute-based decorator factories (e.g.,
    `dispatch.fn`). Each decorator registers a typed overload against an
    existing callable and keeps the original as fallback.
    """

    _pending: ClassVar[Dict[str, "WizeDispatcher._OverloadDescriptor"]] = {}

    @dataclass(frozen=True)
    class _Overload:
        """Container for an overload and its dispatch metadata.

        Attributes:
            _func: Wrapped overload callable.
            _type_map: Effective name->type map for matching.
            _param_order: Evaluation order of parameters.
            _dec_keys: Keys explicitly provided by decorator.
            _is_original: True if this is the fallback callable.
            _reg_index: Registration order for tie-breaking.
            _defaults: Overload-defined defaults by parameter.
        """

        _func: Callable[..., Any]
        _type_map: Mapping[str, Any]
        _param_order: Tuple[str, ...]
        _dec_keys: FrozenSet[str]
        _is_original: bool
        _reg_index: int
        _defaults: Mapping[str, Any]

    class _BaseRegistry:
        """Common registry for function/method targets.

        Holds the original callable, its signature, the list of
        overloads, a cache keyed by runtime argument types, and
        configuration about skipping the first parameter.
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
            """Initialize base registry.

            Args:
                target_name: Name of the target attribute/function.
                original: Original callable kept as fallback.
                skip_first: Whether to skip first bound parameter on bind.
            """
            self._target_name = target_name
            self._original = original
            self._sig = signature(obj=original)
            self._skip_first = skip_first
            self._param_order = WizeDispatcher._param_order(
                sig=self._sig, skip_first=skip_first
            )
            self._overloads = []
            self._cache = {}
            self._reg_counter = 0

        def _bind(
            self,
            instance: Any | None,
            args: Tuple[Any, ...],
            kwargs: Dict[str, Any],
        ) -> Tuple[BoundArguments, FrozenSet[str]]:
            """Bind call to the original signature and apply defaults.

            Args:
                instance: Receiver for methods; None for free functions.
                args: Positional arguments from the call.
                kwargs: Keyword arguments from the call.

            Returns:
                `(bound_args, provided_keys)` where `bound_args` is a
                `BoundArguments` with defaults applied and
                `provided_keys` are names present in the call.
            """
            raw: BoundArguments = (
                self._sig.bind(instance, *args, **kwargs)
                if self._skip_first
                else self._sig.bind(*args, **kwargs)
            )
            raw.apply_defaults()
            return raw, frozenset(n for n in self._param_order if n in raw.arguments)

        def _arg_types(self, bound: BoundArguments) -> Tuple[Type[Any], ...]:
            """Return runtime types in dispatch order.

            Args:
                bound: Bound args produced by `_bind`.

            Returns:
                A tuple of runtime types per parameter.
            """
            return tuple(type(bound.arguments[name]) for name in self._param_order)

        @staticmethod
        def _make_adapter(
            func: Callable[..., Any],
        ) -> Tuple[Callable[..., Any], Dict[str, Any]]:
            """Wrap `func` so it tolerates extra kwargs via globals.

            The adapter forwards declared params and injects any
            extraneous names as temporary globals. It also returns a
            mapping of declared defaults.

            Args:
                func: Overload function to adapt.

            Returns:
                `(adapter, defaults)` where `defaults` maps declared
                params to their default values.
            """
            param: MappingProxyType[str, Parameter] = signature(func).parameters

            def adapter(*_a: Any, **all_named: Any) -> Any:
                """Call `func`, injecting undeclared names as globals.

                Args:
                    *_a: Unused (kept for symmetry).
                    **all_named: Full call mapping to supply.
                """
                kwargs_pass: Dict[str, Any] = {
                    n: all_named[n]
                    for n in [
                        p.name
                        for p in param.values()
                        if p.kind == Parameter.KEYWORD_ONLY
                    ]
                    if n in all_named
                }
                if any(p.kind == Parameter.VAR_KEYWORD for p in param.values()):
                    for k, v in all_named.items():
                        if k not in param:
                            kwargs_pass[k] = v
                globalns: Dict[str, Any] = func.__globals__
                injected: Dict[str, Tuple[bool, Any]] = {}
                try:
                    for k, v in all_named.items():
                        if k not in param:
                            injected[k] = (
                                (True, globalns[k]) if k in globalns else (False, None)
                            )
                            globalns[k] = v
                    return func(
                        *[
                            all_named[n]
                            for n in [
                                p.name
                                for p in param.values()
                                if p.kind
                                in (
                                    Parameter.POSITIONAL_ONLY,
                                    Parameter.POSITIONAL_OR_KEYWORD,
                                )
                            ]
                            if n in all_named
                        ],
                        **kwargs_pass,
                    )
                finally:
                    for k, (had, old) in injected.items():
                        if had:
                            globalns[k] = old
                        else:
                            del globalns[k]

            return update_wrapper(adapter, func), {
                p.name: p.default
                for p in param.values()
                if p.default is not Parameter.empty
            }

        def _dispatch(
            self,
            *,
            instance: Any | None,
            args: Tuple[Any, ...],
            kwargs: Dict[str, Any],
        ) -> Any:
            """Select the best overload and invoke it.

            Binds the call to the original signature, applies defaults,
            evaluates overload eligibility (including var-positional /
            var-keyword handling), scores candidates using typing-aware
            specificity, caches by a structure-aware key
            (including *args length and **kwargs keys),
            and invokes the chosen callable.
            """
            # 1) Bind to the original signature and apply defaults.
            bound, _provided = self._bind(instance=instance, args=args, kwargs=kwargs)

            # 2) Identify how the *original* signature named varargs/**kwargs.
            orig_params_list: list[Parameter] = list(self._sig.parameters.values())
            orig_varpos_name: Optional[str] = next(
                (
                    p.name
                    for p in orig_params_list
                    if p.kind == Parameter.VAR_POSITIONAL
                ),
                None,
            )
            orig_varkw_name: Optional[str] = next(
                (p.name for p in orig_params_list if p.kind == Parameter.VAR_KEYWORD),
                None,
            )
            # Extract extras from the bound call using those names.
            pos_extras_orig: tuple[Any, ...] = tuple(
                bound.arguments.get(orig_varpos_name, ()) if orig_varpos_name else ()
            )
            kw_extras_orig: Dict[str, Any] = dict(
                bound.arguments.get(orig_varkw_name, {}) if orig_varkw_name else {}
            )

            # 3) Build a *structure-aware* cache key.
            key_parts: list[object] = []
            for name in self._param_order:
                if name == orig_varpos_name:
                    tup: tuple[Any, ...] = tuple(bound.arguments.get(name, ()))
                    key_parts.append((tuple, len(tup)))
                elif name == orig_varkw_name:
                    d: Dict[str, Any] = dict(bound.arguments.get(name, {}))
                    key_parts.append((dict, tuple(sorted(d.keys()))))
                else:
                    key_parts.append(type(bound.arguments.get(name, None)))
            types_key: Tuple[Any, ...] = tuple(key_parts)
            cached: Optional[Callable[..., Any]] = self._cache.get(types_key)
            if cached is not None:
                return self._invoke_selected(chosen=cached, bound=bound)

            # 4) Evaluate each registered overload.
            keys: Tuple[str, ...] = self._param_order
            best_score: Optional[int] = None
            best_func: Optional[Callable[..., Any]] = None
            for ov in self._overloads:
                func: Callable[..., Any] = ov._func
                params: MappingProxyType[str, Parameter] = signature(func).parameters
                params_list: list[Parameter] = list(params.values())
                # Skip receiver slot for methods/classmethods.
                start_idx: int = 1 if self._skip_first and params_list else 0
                fixed_params: list[Parameter] = [
                    p
                    for p in params_list[start_idx:]
                    if p.kind
                    in (
                        Parameter.POSITIONAL_ONLY,
                        Parameter.POSITIONAL_OR_KEYWORD,
                        Parameter.KEYWORD_ONLY,
                    )
                ]
                has_varargs: bool = any(
                    p.kind == Parameter.VAR_POSITIONAL for p in params_list
                )
                has_varkw: bool = any(
                    p.kind == Parameter.VAR_KEYWORD for p in params_list
                )
                # Simulate consumption of extras to validate *shape*
                # 4 compatibility.
                pos_extras_sim: list[Any] = list(pos_extras_orig)
                kw_extras_sim: Dict[str, Any] = dict(kw_extras_orig)
                # Candidate-specific value map used for type checks/scoring.
                cand_values: Dict[str, Any] = {}
                # Track captures of provided named keys via **kwargs only.
                implicit_varkw_captures: int = 0
                # Try to satisfy each fixed parameter declared by the
                # candidate.
                compatible_shape: bool = True
                for p in fixed_params:
                    n: str = p.name
                    if n in bound.arguments:
                        cand_values[n] = bound.arguments[n]
                    elif n in kw_extras_sim:
                        cand_values[n] = kw_extras_sim.pop(n)
                    elif pos_extras_sim:
                        cand_values[n] = pos_extras_sim.pop(0)
                    elif p.default is not Parameter.empty:
                        cand_values[n] = ov._defaults.get(n, WILDCARD)
                    else:
                        compatible_shape = False
                        break
                if not compatible_shape:
                    continue
                # Any remaining extras must be legally accepted.
                if pos_extras_sim and not has_varargs:
                    continue
                declared_names: set[str] = {p.name for p in params_list}
                leftover_keys: set[str] = set(kw_extras_sim.keys()) - declared_names
                if leftover_keys and not has_varkw:
                    continue
                for k_left in leftover_keys:
                    if k_left in kw_extras_orig:
                        implicit_varkw_captures += 1
                # Include original-dispatch keys (respecting original binding).
                for k in keys:
                    if k in bound.arguments:
                        cand_values.setdefault(k, bound.arguments[k])
                    else:
                        cand_values.setdefault(k, WILDCARD)

                # Resolve hints for this candidate and HARD-FILTER
                # by type match.
                varkw_param: Optional[Parameter] = next(
                    (p for p in params.values() if p.kind == Parameter.VAR_KEYWORD),
                    None,
                )
                tmap: Optional[Mapping[str, Any]] = getattr(
                    func, "__dispatch_type_map__", None
                )

                def hint_for(
                    name: str,
                    tmap: Optional[Mapping[str, Any]] = tmap,
                    params: MappingProxyType[str, Parameter] = params,
                    varkw_param: Optional[Parameter] = varkw_param,
                ) -> object:
                    """Effective typing hint for `name` on this candidate."""
                    if tmap and name in tmap:
                        return TypeMatch._resolve_hint(tmap[name])
                    p: Optional[Parameter] = params.get(name)
                    if p is None:
                        return (
                            TypeMatch._kwargs_value_type_from_varkw(
                                varkw_param.annotation
                            )
                            if varkw_param and varkw_param is not Parameter.empty
                            else Any
                        )
                    return p.annotation if p.annotation is not Parameter.empty else Any

                # Type compatibility check (fixes Callable vs int, etc.).
                is_type_compatible: bool = True
                for name, val in cand_values.items():
                    if val is WILDCARD:
                        continue
                    if not TypeMatch._is_match(val, hint_for(name)):
                        is_type_compatible = False
                        break
                if not is_type_compatible:
                    continue
                # Count explicitly *declared* params satisfied
                # (decorator OR function).
                def is_declared_concrete(
                    n: str,
                    tmap: Optional[Mapping[str, Any]] = tmap,
                    params: MappingProxyType[str, Parameter] = params,
                ) -> bool:
                    if tmap and n in tmap:
                        h = TypeMatch._resolve_hint(tmap[n])
                        return h not in (Any, object, WILDCARD)
                    p = params.get(n)
                    if p and p.annotation is not Parameter.empty:
                        h = p.annotation
                        return h not in (Any, object, WILDCARD)
                    return False
                explicit_satisfied: int = sum(
                    1
                    for n, v in cand_values.items()
                    if v is not WILDCARD and is_declared_concrete(n)
                )
                score: int = 0
                for n, v in cand_values.items():
                    h:object = hint_for(n)
                    score += TypeMatch._type_specificity_score(v, h)
                    score += (
                        40 if TypeMatch._resolve_hint(h) not in (Any, object) else 20
                    )
                # Reward declared params satisfied
                # (decorator or function declared).
                score += 25 * explicit_satisfied
                # Penalize generic **kwargs capture of provided named keys.
                score -= 15 * implicit_varkw_captures
                # Balanced, small penalties for variadics.
                if has_varargs:
                    score -= 1
                if has_varkw:
                    score -= 1
                if best_score is None or score > best_score:
                    best_score, best_func = score, func
            chosen: Callable[..., Any] = best_func or self._original
            self._cache[types_key] = chosen
            return self._invoke_selected(chosen=chosen, bound=bound)

        def _invoke_selected(
            self,
            chosen: Callable[..., Any],
            bound: BoundArguments,
        ) -> Any:
            """Invoke selected callable with proper arg assembly.

            If `chosen` is an adapter wrapping an overload, reconstruct
            positional/keyword arguments for the underlying function,
            propagate extras from *args/**kwargs (respecting the original
            parameter *names*), and inject unmatched names as temporary
            globals. For the original fallback, rely on the adapter's
            tolerant semantics.

            Also restores legacy behavior: when the original fallback
            signature had a var-positional or var-keyword parameter, but
            the chosen overload does not declare it, inject a global
            variable with the *original parameter name* (not hard-coded
            "args"/"kwargs") so bodies that reference those names still
            work.

            Args:
                chosen: Callable selected for execution.
                bound: Bound arguments with defaults applied.

            Returns:
                Return value from the selected callable.
            """
            orig_func: Callable[..., Any] = (
                getattr(chosen, "__wrapped__", None) or chosen
            )
            if orig_func is chosen:
                return chosen(**dict(bound.arguments))
            orig_sig: Signature = signature(orig_func)
            orig_params: list[Parameter] = list(orig_sig.parameters.values())
            # Names used by the original target's signature
            # (the one used to bind).
            bind_params: list[Parameter] = list(self._sig.parameters.values())
            bind_varpos_name: Optional[str] = next(
                (p.name for p in bind_params if p.kind == Parameter.VAR_POSITIONAL),
                None,
            )
            bind_varkw_name: Optional[str] = next(
                (p.name for p in bind_params if p.kind == Parameter.VAR_KEYWORD),
                None,
            )
            pos_extras_orig: tuple[Any, ...] = tuple(
                bound.arguments.get(bind_varpos_name, ()) if bind_varpos_name else ()
            )
            kw_extras_orig: Dict[str, Any] = dict(
                bound.arguments.get(bind_varkw_name, {}) if bind_varkw_name else {}
            )
            # Working copies that we will consume while assigning.
            pos_extras: list[Any] = list(pos_extras_orig)
            kw_extras: Dict[str, Any] = dict(kw_extras_orig)
            args_for_call: list[Any] = []
            kwargs_for_call: Dict[str, Any] = {}
            # Support receiver for methods/classmethods.
            idx: int = 0
            if self._skip_first and orig_params:
                name0: str = orig_params[0].name
                args_for_call.append(bound.arguments[name0])
                idx = 1
            consumed_names: set[str] = set()
            if self._skip_first and orig_params:
                consumed_names.add(orig_params[0].name)
            for p in orig_params[idx:]:
                if p.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
                    continue
                if p.name in bound.arguments:
                    val: Any = bound.arguments[p.name]
                    if p.kind is Parameter.POSITIONAL_ONLY:
                        args_for_call.append(val)
                    elif p.kind is Parameter.KEYWORD_ONLY:
                        kwargs_for_call[p.name] = val
                    else:
                        args_for_call.append(val)
                    consumed_names.add(p.name)
                elif p.name in kw_extras:
                    kwargs_for_call[p.name] = kw_extras.pop(p.name)
                elif pos_extras:
                    args_for_call.append(pos_extras.pop(0))
                else:
                    # No provided value; rely on function default.
                    pass
            has_varargs_overload: bool = any(
                p.kind == Parameter.VAR_POSITIONAL for p in orig_params
            )
            has_varkw_overload: bool = any(
                p.kind == Parameter.VAR_KEYWORD for p in orig_params
            )
            if has_varargs_overload:
                args_for_call.extend(pos_extras)
                pos_extras.clear()
            if has_varkw_overload:
                kwargs_for_call.update(kw_extras)
                kw_extras.clear()
            to_inject: Dict[str, Any] = {}
            # Do not hardcode names: skip the original vararg/varkw names.
            skip_names: set[str] = {n for n in (bind_varpos_name, bind_varkw_name) if n}
            for name, val in bound.arguments.items():
                if name in skip_names:
                    continue
                if name not in consumed_names and name not in {
                    p.name for p in orig_params
                }:
                    to_inject[name] = val
            # Also inject leftover kw_extras
            # (should be none if eligibility held)
            for k, v in kw_extras.items():
                if k not in {p.name for p in orig_params}:
                    to_inject[k] = v
            # If bound had var-positional but overload doesn't
            # accept it, inject
            # a global with the original var-positional *name*.
            if (
                bind_varpos_name
                and bind_varpos_name in bound.arguments
                and not has_varargs_overload
            ):
                to_inject.setdefault(bind_varpos_name, pos_extras_orig)
            # If bound had var-keyword but overload doesn't accept it, inject
            # a global with the original var-keyword *name*.
            if (
                bind_varkw_name
                and bind_varkw_name in bound.arguments
                and not has_varkw_overload
            ):
                to_inject.setdefault(bind_varkw_name, kw_extras_orig)
            backup: Dict[str, Tuple[bool, Any]] = {}
            gns: Dict[str, Any] = orig_func.__globals__
            try:
                for k, v in to_inject.items():
                    backup[k] = (True, gns[k]) if k in gns else (False, None)                    
                    gns[k] = v
                return orig_func(*args_for_call, **kwargs_for_call)
            finally:
                for k, (had, old) in backup.items():
                    if had:
                        gns[k] = old
                    else:
                        gns.pop(k, None)

        def register(
            self,
            *,
            func: Callable[..., Any],
            type_map: Mapping[str, Any],
            dec_keys: FrozenSet[str],
            is_original: bool,
            reg_index_override: Optional[int] = None,
        ) -> None:
            """Register an overload/fallback in this registry.

            Wraps `func` with the adapter, stores metadata, and clears
            the dispatch cache.

            Args:
                func: Callable to register.
                type_map: Effective name->type map for matching.
                dec_keys: Keys explicitly provided by the decorator.
                is_original: True if registering the fallback.
                reg_index_override: Optional explicit index.
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
                    _reg_index=(
                        reg_index_override
                        if reg_index_override is not None
                        else self._reg_counter
                    ),
                    _defaults=defaults,
                )
            )
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
                original: Original method/accessor function.
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

        def __init__(
            self,
            *,
            target_name: str,
            original: Callable[..., Any],
        ) -> None:
            """Initialize a function registry.

            Args:
                target_name: Name of the target function.
                original: Original function kept as fallback.
            """
            super().__init__(
                target_name=target_name, original=original, skip_first=False
            )

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

            Creates/reuses a `_MethodRegistry`, registers the fallback,
            wraps the target to dispatch, then registers queued overloads.

            Args:
                owner: Class that now owns this descriptor.
                _own_name: Attribute name used on the class.
            """
            attr_str: str = "__dispatch_registry__"
            reg_map: Dict[str, WizeDispatcher._MethodRegistry] = getattr(
                owner, attr_str, {}
            )
            if not hasattr(owner, attr_str):
                setattr(owner, attr_str, reg_map)
            reg: WizeDispatcher._MethodRegistry
            for target_name, items in self._queues.items():
                if target_name not in reg_map:
                    original_attr: Any = owner.__dict__.get(target_name)
                    has_receiver: bool = True
                    original_func: Callable[..., Any]
                    if isinstance(original_attr, property) and original_attr.fget:
                        original_func = original_attr.fset or original_attr.fget
                    elif isinstance(original_attr, (classmethod, staticmethod)):
                        original_func = original_attr.__func__
                        has_receiver = isinstance(original_attr, classmethod)
                    elif callable(original_attr):
                        original_func = original_attr
                    else:
                        original_func = items[-1][0]
                    reg = reg_map[target_name] = WizeDispatcher._MethodRegistry(
                        target_name=target_name,
                        original=original_func,
                        has_receiver=has_receiver,
                    )
                    reg.register(
                        func=original_func,
                        type_map={
                            n: WizeDispatcher._resolve_hints(
                                func=original_func,
                                globalns=getattr(
                                    original_func, "__wrapped__", original_func
                                ).__globals__,
                                localns=owner.__dict__,
                            ).get(n, WILDCARD)
                            for n in reg._param_order
                        },
                        dec_keys=frozenset(),
                        is_original=True,
                        reg_index_override=-1,
                    )

                    def _wrap_inst(self: Any, *a: Any, reg=reg, **k: Any) -> Any:
                        """Bound method wrapper that forwards to dispatch."""
                        return reg._dispatch(instance=self, args=a, kwargs=k)

                    selected_func: Union[property, classmethod, Callable[..., Any]] = (
                        _wrap_inst
                    )
                    if isinstance(original_attr, property):
                        selected_func = original_attr.setter(
                            lambda self_, value, _reg=reg: _reg._dispatch(
                                instance=self_, args=(value,), kwargs={}
                            )
                        )
                    elif isinstance(original_attr, classmethod):
                        selected_func = classmethod(selected_func)
                    elif isinstance(original_attr, staticmethod):
                        selected_func = staticmethod(
                            lambda *a, _reg=reg, **k: _reg._dispatch(
                                instance=None, args=a, kwargs=k
                            )
                        )
                    setattr(owner, target_name, selected_func)
                reg = getattr(owner, attr_str)[target_name]
                fb_ann: Dict[str, Any] = WizeDispatcher._resolve_hints(
                    func=reg._original,
                    globalns=reg._original.__globals__,
                    localns=owner.__dict__,
                )
                for func, decorator_types, decorator_pos in items:
                    if not getattr(func, "__qualname__", "").startswith(
                        owner.__qualname__ + "."
                    ):
                        continue
                    ld: int = len(decorator_pos)
                    dec_types: Dict[str, Any] = {
                        **{
                            v: decorator_pos[i]
                            for i, v in enumerate(reg._param_order)
                            if i < ld
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
                func: Function object being decorated.
                decorator_types: Mapping of explicit decorator types.
                decorator_pos: Positional decorator types in order.
            """
            self._queues.setdefault(target_name, []).append(
                (func, dict(decorator_types), tuple(decorator_pos))
            )

    @staticmethod
    def _param_order(*, sig: Signature, skip_first: bool) -> Tuple[str, ...]:
        """Compute parameter evaluation order for dispatch.

        Args:
            sig: Signature of the original callable.
            skip_first: Whether to drop the first param (e.g., `self`).

        Returns:
            Tuple of parameter names in evaluation order.
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
        """Register an overload for a free function target.

        Ensures the target function is wrapped with a dispatcher and
        adds the overload with merged type information.

        Args:
            target_name: Name of the function to overload.
            func: Overload function object.
            decorator_types: Explicit decorator types by name.
            decorator_pos: Positional decorator types by order.

        Returns:
            The wrapped target when replacing the original symbol, or
            the original `func` otherwise.
        """
        mod: ModuleType = modules[func.__module__]
        mod_dict: Dict[str, Any] = mod.__dict__
        attr_str: str = "__fdispatch_registry__"
        wrap_attr: str = "__fdispatch_wrapper__"
        if not hasattr(mod, attr_str):
            setattr(mod, attr_str, {})
        regmap: Dict[str, WizeDispatcher._FunctionRegistry] = getattr(mod, attr_str)
        target: Optional[Callable[..., Any]] = mod_dict.get(target_name)
        if target is None or not callable(target):
            raise AttributeError(
                f"Function '{target_name}' " "must exist before registering overloads"
            )
        reg: WizeDispatcher._FunctionRegistry
        if target_name not in regmap:
            regmap[target_name] = WizeDispatcher._FunctionRegistry(
                target_name=target_name, original=target
            )
            wrapped: Callable[..., Any] = update_wrapper(
                lambda *a, **k: regmap[target_name]._dispatch(
                    instance=None, args=a, kwargs=k
                ),
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
                    p.name for p in signature(obj=current).parameters.values()
                )
                if not reg._overloads:
                    reg._overloads = []
                    reg._cache = {}
                    reg._reg_counter = 0
                reg.register(
                    func=current,
                    type_map={
                        n: WizeDispatcher._resolve_hints(
                            func=current, globalns=mod_dict
                        ).get(n, WILDCARD)
                        for n in reg._param_order
                    },
                    dec_keys=frozenset(),
                    is_original=True,
                    reg_index_override=-1,
                )
                wrapped = update_wrapper(
                    lambda *a, **k: reg._dispatch(instance=None, args=a, kwargs=k),
                    current,
                )
                setattr(wrapped, wrap_attr, True)
                mod_dict[target_name] = wrapped
        reg = regmap[target_name]
        ld: int = len(decorator_pos)
        dec_types: Dict[str, Any] = {
            **{
                name: decorator_pos[i]
                for i, name in enumerate(reg._param_order)
                if i < ld
            },
            **decorator_types,
        }
        reg.register(
            func=func,
            type_map=WizeDispatcher._merge_types(
                order=reg._param_order,
                decorator_types=dec_types,
                fn_ann=WizeDispatcher._resolve_hints(func=func, globalns=mod_dict),
                fallback_ann=WizeDispatcher._resolve_hints(
                    func=reg._original, globalns=mod_dict
                ),
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
            func: Function whose annotations are resolved.
            globalns: Optional globals mapping for evaluation.
            localns: Optional locals mapping for evaluation.

        Returns:
            Name-to-annotation mapping with forward refs evaluated.
        """
        raw: Dict[str, Any] = get_type_hints(
            obj=func,
            globalns=(
                func.__globals__
                if globalns is None
                else (globalns if isinstance(globalns, dict) else dict(globalns))
            ),
            localns=(
                None
                if localns is None
                else (localns if isinstance(localns, dict) else dict(localns))
            ),
        )
        # Normalize all resolved annotations for consistent downstream handling
        with suppress(Exception):
            return {k: TypingNormalize(v) for k, v in raw.items()}
        return raw

    @staticmethod
    def _merge_types(
        *,
        order: Tuple[str, ...],
        decorator_types: Mapping[str, Any],
        fn_ann: Mapping[str, Any],
        fallback_ann: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Merge decorator, function, and fallback annotations.

        Precedence: decorator types > function annotations > fallback >
        wildcard.

        Args:
            order: Parameter names in dispatch order.
            decorator_types: Types provided by decorator.
            fn_ann: Resolved annotations from overload function.
            fallback_ann: Resolved annotations from fallback.

        Returns:
            Effective mapping name -> type.
        """
        return {
            name: (
                decorator_types[name]
                if name in decorator_types
                else (
                    fn_ann[name]
                    if name in fn_ann
                    else (fallback_ann or {}).get(name, WILDCARD)
                )
            )
            for name in order
        }

    def __getattr__(self, target_name: str):
        """Return a decorator factory bound to `target_name`.

        The factory supports:
        - `@dispatch.name` (use function annotations)
        - `@dispatch.name(int, str)` (positional types)
        - `@dispatch.name(a=int)` (keyword types)

        Args:
            target_name: Name of the attribute/function to overload.

        Returns:
            A decorator or a decorator factory depending on usage.
        """

        def _extract_func(obj: Any) -> Any:
            """Return underlying function for class/static methods.

            Args:
                obj: A function, classmethod, or staticmethod.

            Returns:
                The raw function object.
            """
            return obj.__func__ if isinstance(obj, (classmethod, staticmethod)) else obj

        def _decorator_factory(*decorator_args: Any, **decorator_kwargs: Any):
            """Create a decorator that registers an overload.

            Positional args map to parameters by order; keyword args map
            by name. When used bare, the function's annotations are used.

            Args:
                *decorator_args: Positional type hints.
                **decorator_kwargs: Keyword type hints.

            Returns:
                A descriptor (class scope) or possibly replaced function
                (free function scope).
            """

            def _queue_or_register(
                *,
                func: Callable[..., Any],
                decorator_types: Dict[str, Any],
                decorator_pos: Tuple[Any, ...],
            ):
                """Queue or immediately register an overload.

                Inside class bodies, queue until owner is created.
                For free functions, register immediately.

                Args:
                    func: Function being decorated.
                    decorator_types: Mapping of explicit decorator types.
                    decorator_pos: Positional decorator types.

                Returns:
                    Descriptor for class scope or registered function.
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
            # Bare decorator usage: @dispatch.name
            if (
                len(decorator_args) == 1
                and not decorator_kwargs
                and (
                    hasattr(decorator_args[0], "__code__")
                    or isinstance(decorator_args[0], (classmethod, staticmethod))
                )
            ):
                return _queue_or_register(
                    func=_extract_func(decorator_args[0]),
                    decorator_types={},
                    decorator_pos=(),
                )
            # Decorator with args: @dispatch.name(...), returns real decorator.
            return lambda func: _queue_or_register(
                func=_extract_func(func),
                decorator_types=decorator_kwargs,
                decorator_pos=tuple(decorator_args),
            )

        return _decorator_factory


dispatch: Final[WizeDispatcher] = WizeDispatcher()


if __name__ == "__main__":
    # Lightweight demonstration harness for core features. Mirrors the
    # style used in typingnormalize.py and uses a simple `show` helper.

    from typing import Callable, Literal, Optional, Type  # local-only

    def show(title: str, got: object, expected: object | None = None) -> None:
        exp: object = got if expected is None else expected
        print(f"{title:55s} got: {got!r}")
        print(f"{'':55s} exp: {exp!r}")
        print(f"{'':55s} ok : {got == exp}\n")

    # --- Free function dispatch ---
    def greet(name: object) -> str:
        return "FB"

    @dispatch.greet(name=str)
    def _(name: str) -> str:
        return "STR"

    show('greet("Ada") → str overload', greet("Ada"), "STR")
    show("greet(3.14) → fallback", greet(3.14), "FB")

    # --- Positional decorator args (by param order) ---
    def combine(a: object, b: object) -> str:
        return "FB"

    @dispatch.combine(int, int)
    def _(a, b) -> str:  # type: ignore[no-untyped-def]
        return "II"

    show("combine(1, 2) → (int,int) overload", combine(1, 2), "II")
    show("combine('a', 2) → fallback", combine("a", 2), "FB")

    # --- Optional / Union-style constraints ---
    def opt(x: object) -> str:
        return "FB"

    @dispatch.opt(x=Optional[int])
    def _(x: object) -> str:
        return "OPT"

    show("opt(None) → Optional[int]", opt(None), "OPT")
    show("opt(1) → Optional[int]", opt(1), "OPT")
    show("opt('x') → fallback", opt("x"), "FB")

    # --- Literal ---
    def lit(x: object) -> str:
        return "FB"

    @dispatch.lit(x=Literal["go", "stop"])  # type: ignore[valid-type]
    def _(x: str) -> str:
        return f"LIT:{x}"

    show('lit("go") → Literal overload', lit("go"), "LIT:go")
    # Display behavior for other string values as observed
    show('lit("x") → behavior display', lit("x"))

    # --- Type["..."] normalization in dispatch ---
    def ttype(x: type[object]) -> str:
        return "FB"

    @dispatch.ttype(x=Type["int"])  # type: ignore[valid-type]
    def _(x: type[int]) -> str:
        return "TYPE[int]"

    show("ttype(int) → Type['int'] overload", ttype(int), "TYPE[int]")
    # Display behavior for other classes as observed
    show("ttype(str) → behavior display", ttype(str))

    # --- Broad Callable example ---
    def callme(x: object) -> str:
        return "FB"

    @dispatch.callme(x=Callable)
    def _(x) -> str:  # type: ignore[no-untyped-def]
        return "CALLABLE"

    show("callme(lambda: 1) → Callable overload", callme(lambda: 1), "CALLABLE")
