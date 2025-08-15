from __future__ import annotations

import typing
from collections import ChainMap as CollChainMap
from collections import Counter as CollCounter
from collections import OrderedDict as CollOrderedDict
from collections import defaultdict as CollDefaultDict
from collections import deque as CollDeque
from collections.abc import AsyncIterable as AbcAsyncIterable
from collections.abc import AsyncIterator as AbcAsyncIterator
from collections.abc import Awaitable as AbcAwaitable
from collections.abc import ByteString as AbcByteString
from collections.abc import Callable as AbcCallable
from collections.abc import Collection as AbcCollection
from collections.abc import Container as AbcContainer
from collections.abc import Coroutine as AbcCoroutine
from collections.abc import Generator as AbcGenerator
from collections.abc import Hashable as AbcHashable
from collections.abc import ItemsView as AbcItemsView
from collections.abc import Iterable as AbcIterable
from collections.abc import Iterator as AbcIterator
from collections.abc import KeysView as AbcKeysView
from collections.abc import Mapping as AbcMapping
from collections.abc import MappingView as AbcMappingView
from collections.abc import MutableMapping as AbcMutableMapping
from collections.abc import MutableSequence as AbcMutableSequence
from collections.abc import Reversible as AbcReversible
from collections.abc import Sequence as AbcSequence
from collections.abc import Set as AbcSet
from collections.abc import Sized as AbcSized
from collections.abc import ValuesView as AbcValuesView
from contextlib import suppress
from re import Match as ReMatch
from re import Pattern as RePattern
from types import UnionType
from typing import (
    AbstractSet,
    Annotated,
    Any,
    AsyncContextManager,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    ByteString,
    Callable,
    ChainMap,
    ClassVar,
    Collection,
    Concatenate,
    Container,
    Coroutine,
    Counter,
    DefaultDict,
    Deque,
    Dict,
    ForwardRef,
    FrozenSet,
    Generator,
    Hashable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    List,
    Literal,
    Mapping,
    MappingView,
    Match,
    MutableMapping,
    MutableSequence,
    Optional,
    OrderedDict,
    ParamSpec,
    Pattern,
    Reversible,
    Sequence,
    Set,
    Sized,
    Tuple,
    Type,
    TypeVar,
    Union,
    ValuesView,
    get_args,
    get_origin,
)


class TypingNormalize:
    """Normalize annotations to canonical typing.* constructs.

    Usage:
      norm: object = TypingNormalize(tp)

    Guarantees:
      * Removes TypeVar, ParamSpec, Concatenate, Optional, and '|'.
      * Unions are typing.Union[..., ...] with None placed first.
      * Builtins/ABCs/concrete collections → typing.* equivalents.
      * Bare typing generics gain Any defaults (e.g., Type[Any]).
      * Callable with ParamSpec/Concatenate → Callable[..., R].
      * String-based Type annotations (e.g., Type["int"]) → Type[int].
      * Actual class objects in Type[] and Union[] are preserved (e.g.,
        Type[custom_class]).
      * Generic arguments are normalized recursively.
    """

    _ORIGIN_TO_TYPING: Dict[object, str] = {
        # PEP 585 builtins
        list: "List",
        dict: "Dict",
        set: "Set",
        frozenset: "FrozenSet",
        tuple: "Tuple",
        type: "Type",
        # collections concrete
        CollDeque: "Deque",
        CollDefaultDict: "DefaultDict",
        CollOrderedDict: "OrderedDict",
        CollCounter: "Counter",
        CollChainMap: "ChainMap",
        # ABCs to typing
        AbcMapping: "Mapping",
        AbcMutableMapping: "MutableMapping",
        AbcSequence: "Sequence",
        AbcMutableSequence: "MutableSequence",
        AbcIterable: "Iterable",
        AbcIterator: "Iterator",
        AbcCollection: "Collection",
        AbcSet: "AbstractSet",
        AbcByteString: "ByteString",
        AbcReversible: "Reversible",
        AbcSized: "Sized",
        AbcContainer: "Container",
        AbcHashable: "Hashable",
        AbcAwaitable: "Awaitable",
        AbcCoroutine: "Coroutine",
        AbcAsyncIterable: "AsyncIterable",
        AbcAsyncIterator: "AsyncIterator",
        AbcGenerator: "Generator",
        AbcMappingView: "MappingView",
        AbcKeysView: "KeysView",
        AbcItemsView: "ItemsView",
        AbcValuesView: "ValuesView",
        # regex runtime → typing
        RePattern: "Pattern",
        ReMatch: "Match",
    }
    _TYPING_MAP: Dict[object, str] = {
        List: "List",
        Dict: "Dict",
        Set: "Set",
        FrozenSet: "FrozenSet",
        Tuple: "Tuple",
        Type: "Type",
        Deque: "Deque",
        DefaultDict: "DefaultDict",
        OrderedDict: "OrderedDict",
        Counter: "Counter",
        ChainMap: "ChainMap",
        Mapping: "Mapping",
        MutableMapping: "MutableMapping",
        Sequence: "Sequence",
        MutableSequence: "MutableSequence",
        Iterable: "Iterable",
        Iterator: "Iterator",
        Collection: "Collection",
        AbstractSet: "AbstractSet",
        ByteString: "ByteString",
        Reversible: "Reversible",
        Sized: "Sized",
        Container: "Container",
        Hashable: "Hashable",
        Awaitable: "Awaitable",
        Coroutine: "Coroutine",
        AsyncIterable: "AsyncIterable",
        AsyncIterator: "AsyncIterator",
        Generator: "Generator",
        MappingView: "MappingView",
        KeysView: "KeysView",
        ItemsView: "ItemsView",
        ValuesView: "ValuesView",
        AsyncContextManager: "AsyncContextManager",
        Pattern: "Pattern",
        Match: "Match",
        Callable: "Callable",
        Union: "Union",
    }

    def __new__(cls, tp: object) -> object:
        """Return the normalized typing form of ``tp``.

        Args:
          tp: Any annotation or runtime type to normalize.

        Returns:
          A typing.* object representing the normalized annotation.
        """
        return cls._norm(tp)

    # -------------------- detection helpers --------------------

    @staticmethod
    def _is_typevar(obj: object) -> bool:
        """Return True if obj appears to be a TypeVar.

        Args:
          obj: Object to test.

        Returns:
          True if obj behaves like a TypeVar, else False.
        """
        return hasattr(obj, "__constraints__") and (obj.__class__.__name__
                                                    == "TypeVar")

    @staticmethod
    def _is_paramspec(obj: object) -> bool:
        """Return True if obj appears to be a ParamSpec.

        Args:
          obj: Object to test.

        Returns:
          True if obj behaves like a ParamSpec, else False.
        """
        return (hasattr(obj, "args") and hasattr(obj, "kwargs")
                and (obj.__class__.__name__ == "ParamSpec"))

    @staticmethod
    def _is_union_like(tp: object) -> bool:
        """Return True if ``tp`` is a typing or PEP 604 union.

        Args:
          tp: Type expression to inspect.

        Returns:
          True if union-like, else False.
        """
        return get_origin(tp) is Union or isinstance(tp, UnionType)

    @staticmethod
    def _is_callable_origin(origin: object | None) -> bool:
        """Return True if origin corresponds to collections.abc.Callable.

        Args:
          origin: Value from typing.get_origin(...).

        Returns:
          True if it is the Callable origin, else False.
        """
        return origin is AbcCallable

    @staticmethod
    def _is_concatenate(tp: object) -> bool:
        """Return True if ``tp`` is typing.Concatenate[...].

        Args:
          tp: Type expression to inspect.

        Returns:
          True if it is a Concatenate, else False.
        """
        return get_origin(tp) is Concatenate

    @staticmethod
    def _string_to_type(type_name: str) -> object:
        """Convert a string type name to the actual type object.

        Args:
          type_name: String representation of a type (e.g., "int", "str").

        Returns:
          The actual type object if found, otherwise Any.
        """
        # Common builtin types
        builtin_types = {
            "int": int,
            "str": str,
            "bytes": bytes,
            "float": float,
            "bool": bool,
            "complex": complex,
            "list": list,
            "dict": dict,
            "set": set,
            "frozenset": frozenset,
            "tuple": tuple,
            "type": type,
            "object": object,
            "None": type(None),
            "NoneType": type(None),
        }
        # Try to get from builtins first
        if type_name in builtin_types:
            return builtin_types[type_name]
        # Try to get from globals (for user-defined types)
        with suppress(ImportError, AttributeError):
            import builtins

            if hasattr(builtins, type_name):
                return getattr(builtins, type_name)
        # If we can't resolve the type, return Any
        return Any

    @staticmethod
    def _resolve_forward_ref(forward_ref: ForwardRef) -> object:
        """Resolve a ForwardRef to its actual type.

        Args:
          forward_ref: A ForwardRef object.

        Returns:
          The resolved type object if possible, otherwise Any.
        """
        with suppress(ImportError, AttributeError):
            return TypingNormalize._string_to_type(forward_ref.__forward_arg__)
        return Any

    @staticmethod
    def _norm(tp: object) -> object:
        """Normalize any annotation to canonical typing constructs.

        Args:
          tp: Any annotation or runtime type.

        Returns:
          A typing.* object where generics and unions are normalized.
        """
        if TypingNormalize._is_typevar(tp):
            constraints: Tuple[object, ...] = getattr(tp, "__constraints__",
                                                      ())
            if constraints:
                return TypingNormalize._to_union(*constraints)
            bound: object | None = getattr(tp, "__bound__", None)
            return Any if bound is None else TypingNormalize._norm(bound)
        if TypingNormalize._is_paramspec(tp):
            return Any
        if TypingNormalize._is_union_like(tp):
            return TypingNormalize._to_union(*get_args(tp))
        # Bare typing generics (e.g., List, Dict, Type) → defaults
        defaulted: object | None = TypingNormalize._plain_typing_to_defaults(
            tp)
        if defaulted is not None:
            return defaulted
        origin: object | None = get_origin(tp)
        if TypingNormalize._is_callable_origin(origin):
            params_ret: Tuple[object, ...] = get_args(tp)
            if len(params_ret) != 2:
                return Callable[..., Any]
            params: object = params_ret[0]
            ret: object = TypingNormalize._norm(params_ret[1])
            return (TypingNormalize._tsub(
                "Callable",
                ([TypingNormalize._norm(p) for p in params], ret),
            ) if isinstance(params, list) else TypingNormalize._tsub(
                "Callable", (Ellipsis, ret)))
        # Handle Type annotations - convert strings/ForwardRefs but preserve
        # actual class objects
        if origin is type:
            args: Tuple[object, ...] = get_args(tp)
            if len(args) == 1:
                arg = args[0]
                if isinstance(arg, str):
                    # Convert string to actual type if possible
                    normalized_arg = TypingNormalize._string_to_type(arg)
                    return TypingNormalize._tsub("Type", (normalized_arg, ))
                elif isinstance(arg, ForwardRef):
                    # Convert ForwardRef to actual type if possible
                    normalized_arg = TypingNormalize._resolve_forward_ref(arg)
                    return TypingNormalize._tsub("Type", (normalized_arg, ))
                else:
                    # Preserve actual class objects (e.g., Type[custom_class])
                    # Just normalize the class object itself if it's a generic
                    normalized_arg = TypingNormalize._norm(arg)
                    return TypingNormalize._tsub("Type", (normalized_arg, ))
        return (TypingNormalize._plain_runtime_to_typing(tp)
                if origin is None else TypingNormalize._from_origin(
                    origin,
                    tuple(TypingNormalize._norm(a) for a in get_args(tp))))

    @staticmethod
    def _to_union(*parts: object) -> object:
        """Build typing.Union[...] from arbitrary union-like parts.

        Args:
          parts: Pieces that may include unions or plain types.

        Returns:
          A flattened typing.Union[...] with None first if present, or a
          single member type if only one remains.
        """
        flat: List[object] = TypingNormalize._explode(parts)
        seen: Set[object] = set()
        uniq: List[object] = []
        none_t: type = type(None)
        has_none: bool = False
        for p in flat:
            if p is none_t:
                has_none = True
            if p not in seen:
                seen.add(p)
                uniq.append(p)
        if not uniq or Any in uniq:
            return Any
        if has_none:
            uniq = [none_t] + [x for x in uniq if x is not none_t]
        if len(uniq) == 1:
            return uniq[0]
        return TypingNormalize._tsub("Union", tuple(uniq))

    @staticmethod
    def _explode(items: Tuple[object, ...]) -> List[object]:
        """Flatten nested union-like structures.

        Args:
          items: Candidate types which may contain unions.

        Returns:
          A flat list of normalized, non-union parts.
        """
        out: List[object] = []
        for it in items:
            itn: object = TypingNormalize._norm(it)
            if TypingNormalize._is_union_like(itn):
                out.extend(TypingNormalize._explode(get_args(itn)))
            else:
                out.append(itn)
        return out

    @staticmethod
    def _from_origin(origin: object, args: Tuple[object, ...]) -> object:
        """Build a typing.* type from an origin and normalized args.

        Args:
          origin: The origin returned by typing.get_origin(...).
          args: The already normalized generic arguments.

        Returns:
          A typing.* object (e.g., typing.List[T]) built from the origin.
        """
        # Handle typing special forms that require specific subscription shapes
        if origin is ClassVar:
            # ClassVar expects a single type argument
            if not args:
                return ClassVar
            return ClassVar[args[0]]  # type: ignore[index]
        if origin is Annotated:
            # Annotated accepts (type, *metadata)
            return Annotated[args]  # type: ignore[index]
        if origin is Literal:
            # Literal accepts a variadic list of literal values
            return Literal[args]  # type: ignore[index]

        name: str | None = TypingNormalize._ORIGIN_TO_TYPING.get(origin)
        if name is None:
            # Fallback: construct using the origin directly if it supports
            # subscription
            try:
                return origin[args]  # type: ignore[index]
            except Exception:
                return origin
        return ((TypingNormalize._tsub("Tuple",
                                       tuple(args[:-1]) + (Ellipsis, )))
                if name == "Tuple" and args and args[-1] is Ellipsis else
                TypingNormalize._tsub(name, args))

    @staticmethod
    def _plain_runtime_to_typing(tp: object) -> object:
        """Map bare runtime builtins/ABCs to typing with Any defaults.

        Args:
          tp: A non-parameterized builtin or ABC or concrete collection.

        Returns:
          A typing.* type with default Any params, or the input if unknown.
        """
        if tp is list:
            return TypingNormalize._tsub("List", (Any, ))
        if tp is dict:
            return TypingNormalize._tsub("Dict", (Any, Any))
        if tp is set:
            return TypingNormalize._tsub("Set", (Any, ))
        if tp is frozenset:
            return TypingNormalize._tsub("FrozenSet", (Any, ))
        if tp is tuple:
            return TypingNormalize._tsub("Tuple", (Any, Ellipsis))
        if tp is type:
            return TypingNormalize._tsub("Type", (Any, ))
        if tp is AbcCallable or tp is callable:
            return TypingNormalize._tsub("Callable", (Ellipsis, Any))
        name: str | None = TypingNormalize._ORIGIN_TO_TYPING.get(tp)
        return (tp if name is None else
                TypingNormalize._typing_defaults_by_name(name))

    @staticmethod
    def _plain_typing_to_defaults(tp: object) -> object | None:
        """Return defaulted typing generics for bare typing.* names.

        Args:
          tp: A typing.* generic like List, Dict, Type, Mapping, etc.

        Returns:
          A parameterized typing.* type with Any defaults, or None if
          ``tp`` is not a bare typing generic.
        """
        name: str | None = TypingNormalize._TYPING_MAP.get(tp)
        return (None if name is None else
                TypingNormalize._typing_defaults_by_name(name))

    @staticmethod
    def _typing_defaults_by_name(name: str) -> object:
        """Build parameterized typing.* defaults by standardized name.

        Args:
          name: Standardized typing name (e.g., 'List', 'Type').

        Returns:
          A parameterized typing.* type with Any defaults.
        """
        if name == "List":
            return TypingNormalize._tsub("List", (Any, ))
        if name == "Dict":
            return TypingNormalize._tsub("Dict", (Any, Any))
        if name == "Set":
            return TypingNormalize._tsub("Set", (Any, ))
        if name == "FrozenSet":
            return TypingNormalize._tsub("FrozenSet", (Any, ))
        if name == "Tuple":
            return TypingNormalize._tsub("Tuple", (Any, Ellipsis))
        if name == "Type":
            return TypingNormalize._tsub("Type", (Any, ))
        if name == "Deque":
            return TypingNormalize._tsub("Deque", (Any, ))
        if name == "DefaultDict":
            return TypingNormalize._tsub("DefaultDict", (Any, Any))
        if name == "OrderedDict":
            return TypingNormalize._tsub("OrderedDict", (Any, Any))
        if name == "Counter":
            return TypingNormalize._tsub("Counter", (Any, ))
        if name == "ChainMap":
            return TypingNormalize._tsub("ChainMap", (Any, Any))
        if name in {"Mapping", "MutableMapping"}:
            return TypingNormalize._tsub(name, (Any, Any))
        if name in {
                "Iterable",
                "Iterator",
                "AsyncIterable",
                "AsyncIterator",
                "Sequence",
                "MutableSequence",
                "Collection",
                "AbstractSet",
                "Reversible",
                "ContextManager",
                "AsyncContextManager",
                "Pattern",
                "Match",
        }:
            return TypingNormalize._tsub(name, (Any, ))
        if name in {"Coroutine", "Generator"}:
            return TypingNormalize._tsub(name, (Any, Any, Any))
        if name in {"MappingView", "KeysView", "ItemsView", "ValuesView"}:
            return getattr(typing, name)
        if name == "Callable":
            return TypingNormalize._tsub("Callable", (Ellipsis, Any))
        if name == "Union":
            return Any
        return getattr(typing, name)

    @staticmethod
    def _tsub(typing_name: str, args: object) -> object:
        """Build ``typing.<Name>[...]``

        Args:
          typing_name: Name inside typing (e.g., 'List', 'Union').
          args: Subscript args. For Callable, pass ([params], ret) or
            (Ellipsis, ret). For others, pass a tuple of args.

        Returns:
          A typing object such as typing.List[T] or typing.Union[...].

        Raises:
          ValueError: If the arguments' shape is invalid for the target.
        """
        if typing_name == "Union":
            if not isinstance(args, tuple):
                raise ValueError("Union expects a tuple of arguments.")
            if len(args) == 0:
                return Union
            return Union[args]
        if typing_name == "Callable":
            if not isinstance(args, tuple) or len(args) != 2:
                raise ValueError("Callable expects (params, return).")
            params: object = args[0]
            ret: object = args[1]
            if params is Ellipsis:
                return getattr(typing, typing_name)[..., ret]
            if isinstance(params, list):
                return getattr(typing, typing_name)[params, ret]
            raise ValueError("Callable params must be list or Ellipsis.")
        if not isinstance(args, tuple):
            raise ValueError("Generic expects a tuple of arguments.")
        try:
            return getattr(typing, typing_name)[args]
        except Exception as exc:
            raise ValueError(
                f"Unknown typing target: {typing_name!r}") from exc


if __name__ == "__main__":

    def show(title: str,
             input_tp: object,
             expected: str | None = None) -> None:
        out_str: str = repr(TypingNormalize(input_tp))
        exp_str: str = out_str if expected is None else expected
        print(f"{title:61s} in : {input_tp!r}")
        print(f"{'':61s} out: {out_str}")
        print(f"{'':61s} exp: {exp_str}")
        print(f"{'':61s} valid: {out_str == exp_str}\n")

    # ---------------------- TypeVar cases -----------------------
    T: TypeVar = TypeVar("T", str, bytes)
    U: TypeVar = TypeVar("U", bound=BaseException)
    V: TypeVar = TypeVar("V")

    show("TypeVar constraints -> Union", T, "typing.Union[str, bytes]")
    show("TypeVar bound -> bound type", U, "<class 'BaseException'>")
    show("Unconstrained TypeVar -> Any", V, "typing.Any")

    # ---------------------- ParamSpec / Concatenate -------------
    P: ParamSpec = ParamSpec("P")
    show(
        "Callable[ParamSpec, R] -> Callable[..., R]",
        Callable[P, int],  # type: ignore[reportGeneralTypeIssues]
        "typing.Callable[..., int]",
    )
    show(
        "Callable[Concatenate[..., P], R] -> Callable[..., R]",
        Callable[
            Concatenate[int, P],  # type: ignore[reportGeneralTypeIssues] str
        ],
        "typing.Callable[..., str]",
    )

    # ---------------------- Optional / '|' unions ----------------
    show("Optional[T] stays Optional[T]", Optional[int],
         "typing.Optional[int]")
    show(
        "PEP 604 unions flattened; None first",
        int | str | None,
        "typing.Union[NoneType, int, str]",
    )
    show(
        "Nested unions flatten",
        Union[Union[int, str], Union[str, bytes]],
        "typing.Union[int, str, bytes]",
    )
    show("Union with Any collapses to Any", Union[int, Any], "typing.Any")
    show("Any in PEP 604 union collapses to Any", int | Any, "typing.Any")
    show("Optional[Any] collapses to Any", Optional[Any], "typing.Any")
    show("None|Any collapses to Any", None | Any, "typing.Any")

    # ---------------------- Builtins (PEP 585) -------------------
    show(
        "PEP 585 list[...] -> typing.List[...]",
        list[int | str],
        "typing.List[typing.Union[int, str]]",
    )
    show(
        "PEP 585 dict[...] -> typing.Dict[...]",
        dict[str, bytes],
        "typing.Dict[str, bytes]",
    )
    show("PEP 585 set[...] -> typing.Set[...]", set[bytes],
         "typing.Set[bytes]")
    show(
        "PEP 585 frozenset[...] -> typing.FrozenSet[...]",
        frozenset[int],
        "typing.FrozenSet[int]",
    )
    show(
        "PEP 585 tuple[T, U] -> typing.Tuple[T, U]",
        tuple[int, str],
        "typing.Tuple[int, str]",
    )
    show(
        "PEP 585 tuple[T, ...] -> typing.Tuple[T, ...]",
        tuple[int, ...],
        "typing.Tuple[int, ...]",
    )
    show("PEP 585 type[T] -> typing.Type[T]", type[int], "typing.Type[int]")
    show(
        "typing.Callable[...] remains typing.Callable[...]",
        Callable[[int, str], bytes],
        "typing.Callable[[int, str], bytes]",
    )

    # Bare builtins -> typing with Any defaults
    show("Bare list -> typing.List[Any]", list, "typing.List[typing.Any]")
    show(
        "Bare dict -> typing.Dict[Any, Any]",
        dict,
        "typing.Dict[typing.Any, typing.Any]",
    )
    show(
        "Bare tuple -> typing.Tuple[Any, ...]",
        tuple,
        "typing.Tuple[typing.Any, ...]",
    )
    show("Bare type -> typing.Type[Any]", type, "typing.Type[typing.Any]")
    show(
        "Bare callable -> typing.Callable[..., Any]",
        callable,
        "typing.Callable[..., typing.Any]",
    )

    # ---------------------- collections concrete -----------------
    show(
        "collections.deque[T] -> typing.Deque[T]",
        CollDeque[int],
        "typing.Deque[int]",
    )
    show(
        "collections.defaultdict[K,V] -> typing.DefaultDict[K,V]",
        CollDefaultDict[str, int],
        "typing.DefaultDict[str, int]",
    )
    show(
        "collections.OrderedDict[K,V] -> typing.OrderedDict[K,V]",
        CollOrderedDict[str, int],
        "typing.OrderedDict[str, int]",
    )
    show(
        "collections.Counter[T] -> typing.Counter[T]",
        CollCounter[int],
        "typing.Counter[int]",
    )
    show(
        "collections.ChainMap[K,V] -> typing.ChainMap[K,V]",
        CollChainMap[str, int],
        "typing.ChainMap[str, int]",
    )

    # Bare concrete -> defaults
    show(
        "Bare collections.deque -> typing.Deque[Any]",
        CollDeque,
        "typing.Deque[typing.Any]",
    )
    show(
        "Bare collections.defaultdict -> typing.DefaultDict[Any, Any]",
        CollDefaultDict,
        "typing.DefaultDict[typing.Any, typing.Any]",
    )
    show(
        "Bare collections.OrderedDict -> typing.OrderedDict[Any, Any]",
        CollOrderedDict,
        "typing.OrderedDict[typing.Any, typing.Any]",
    )
    show(
        "Bare collections.Counter -> typing.Counter[Any]",
        CollCounter,
        "typing.Counter[typing.Any]",
    )
    show(
        "Bare collections.ChainMap -> typing.ChainMap[Any, Any]",
        CollChainMap,
        "typing.ChainMap[typing.Any, typing.Any]",
    )

    # ---------------------- collections.abc ----------------------
    show(
        "collections.abc Mapping[K,V] -> typing.Mapping[K,V]",
        AbcMapping[str, int],
        "typing.Mapping[str, int]",
    )
    show(
        "collections.abc Sequence[T] -> typing.Sequence[T]",
        AbcSequence[int],
        "typing.Sequence[int]",
    )
    show(
        "collections.abc Iterable[T] -> typing.Iterable[T]",
        AbcIterable[int],
        "typing.Iterable[int]",
    )
    show(
        "collections.abc AsyncIterator[T] -> typing.AsyncIterator[T]",
        AbcAsyncIterator[int],
        "typing.AsyncIterator[int]",
    )
    show(
        "collections.abc Generator[T,T,T] -> typing.Generator[T,T,T]",
        AbcGenerator[int, int, int],
        "typing.Generator[int, int, int]",
    )

    # ---------------------- regex runtime ↔ typing ---------------
    show(
        "re.Pattern[T] -> typing.Pattern[T]",
        RePattern[str],
        "typing.Pattern[str]",
    )
    show("re.Match[T] -> typing.Match[T]", ReMatch[str], "typing.Match[str]")
    show(
        "Bare re.Pattern -> typing.Pattern[Any]",
        RePattern,
        "typing.Pattern[typing.Any]",
    )
    show(
        "Bare re.Match -> typing.Match[Any]",
        ReMatch,
        "typing.Match[typing.Any]",
    )

    # ---------------------- Bare typing generics -----------------
    show("Bare typing.List -> typing.List[Any]", List,
         "typing.List[typing.Any]")
    show(
        "Bare typing.Dict -> typing.Dict[Any, Any]",
        Dict,
        "typing.Dict[typing.Any, typing.Any]",
    )
    show("Bare typing.Set -> typing.Set[Any]", Set, "typing.Set[typing.Any]")
    show(
        "Bare typing.FrozenSet -> typing.FrozenSet[Any]",
        FrozenSet,
        "typing.FrozenSet[typing.Any]",
    )
    show(
        "Bare typing.Tuple -> typing.Tuple[Any, ...]",
        Tuple,
        "typing.Tuple[typing.Any, ...]",
    )
    show("Bare typing.Type -> typing.Type[Any]", Type,
         "typing.Type[typing.Any]")
    show(
        "Bare typing.Deque -> typing.Deque[Any]",
        Deque,
        "typing.Deque[typing.Any]",
    )
    show(
        "Bare typing.DefaultDict -> typing.DefaultDict[Any, Any]",
        DefaultDict,
        "typing.DefaultDict[typing.Any, typing.Any]",
    )
    show(
        "Bare typing.OrderedDict -> typing.OrderedDict[Any, Any]",
        OrderedDict,
        "typing.OrderedDict[typing.Any, typing.Any]",
    )
    show(
        "Bare typing.Counter -> typing.Counter[Any]",
        Counter,
        "typing.Counter[typing.Any]",
    )
    show(
        "Bare typing.ChainMap -> typing.ChainMap[Any, Any]",
        ChainMap,
        "typing.ChainMap[typing.Any, typing.Any]",
    )
    show(
        "Bare typing.Mapping -> typing.Mapping[Any, Any]",
        Mapping,
        "typing.Mapping[typing.Any, typing.Any]",
    )
    show(
        "Bare typing.MutableMapping -> typing.MutableMapping[Any, Any]",
        MutableMapping,
        "typing.MutableMapping[typing.Any, typing.Any]",
    )
    show(
        "Bare typing.Sequence -> typing.Sequence[Any]",
        Sequence,
        "typing.Sequence[typing.Any]",
    )
    show(
        "Bare typing.MutableSequence -> typing.MutableSequence[Any]",
        MutableSequence,
        "typing.MutableSequence[typing.Any]",
    )
    show(
        "Bare typing.Iterable -> typing.Iterable[Any]",
        Iterable,
        "typing.Iterable[typing.Any]",
    )
    show(
        "Bare typing.Iterator -> typing.Iterator[Any]",
        Iterator,
        "typing.Iterator[typing.Any]",
    )
    show(
        "Bare typing.Collection -> typing.Collection[Any]",
        Collection,
        "typing.Collection[typing.Any]",
    )
    show(
        "Bare typing.AbstractSet -> typing.AbstractSet[Any]",
        AbstractSet,
        "typing.AbstractSet[typing.Any]",
    )
    show(
        "Bare typing.ByteString -> typing.ByteString",
        ByteString,
        "typing.ByteString",
    )
    show(
        "Bare typing.Reversible -> typing.Reversible[Any]",
        Reversible,
        "typing.Reversible[typing.Any]",
    )
    show("Bare typing.Sized -> typing.Sized", Sized, "typing.Sized")
    show(
        "Bare typing.Container -> typing.Container",
        Container,
        "typing.Container",
    )
    show("Bare typing.Hashable -> typing.Hashable", Hashable,
         "typing.Hashable")
    show(
        "Bare typing.Awaitable -> typing.Awaitable",
        Awaitable,
        "typing.Awaitable",
    )
    show(
        "Bare typing.Coroutine -> typing.Coroutine[Any, Any, Any]",
        Coroutine,
        "typing.Coroutine[typing.Any, typing.Any, typing.Any]",
    )
    show(
        "Bare typing.AsyncIterable -> typing.AsyncIterable[Any]",
        AsyncIterable,
        "typing.AsyncIterable[typing.Any]",
    )
    show(
        "Bare typing.AsyncIterator -> typing.AsyncIterator[Any]",
        AsyncIterator,
        "typing.AsyncIterator[typing.Any]",
    )
    show(
        "Bare typing.Generator -> typing.Generator[Any, Any, Any]",
        Generator,
        "typing.Generator[typing.Any, typing.Any, typing.Any]",
    )
    show(
        "Bare typing.AsyncContextManager gets defaults",
        AsyncContextManager,
        "typing.AsyncContextManager[typing.Any, bool | None]",
    )
    show(
        "Bare typing.Pattern -> typing.Pattern[Any]",
        Pattern,
        "typing.Pattern[typing.Any]",
    )
    show(
        "Bare typing.Match -> typing.Match[Any]",
        Match,
        "typing.Match[typing.Any]",
    )
    show(
        "Bare typing.Callable -> typing.Callable[..., Any]",
        Callable,
        "typing.Callable[..., typing.Any]",
    )
    show("Bare typing.Union -> typing.Any", Union, "typing.Any")

    # ---------------------- Nested generics ----------------------
    show(
        "Nested generics + unions normalize (Dict[...] example)",
        dict[str | None, list[Optional[int | bytes]]],
        ("typing.Dict[typing.Optional[str],"
         "typing.List[typing.Union[NoneType, int, bytes]]]"),
    )
    show(
        "Nested generics normalize (List[Dict[...]] example)",
        List[Dict[str, List[int | str]]],
        "typing.List[typing.Dict[str, typing.List[int | str]]]",
    )

    # ---------------------- Callable specifics -------------------
    show(
        "Callable with nested generics normalizes recursively",
        Callable[[list[int | str], Optional[bytes]], Optional[str]],
        ("typing.Callable[[typing.List[typing.Union[int, str]], "
         "typing.Optional[bytes]], typing.Optional[str]]"),
    )

    # ---------------------- String-based Type annotations --------
    show(
        "Type['int'] -> typing.Type[int]",
        Type["int"],
        "typing.Type[int]",
    )
    show(
        "Type['str'] -> typing.Type[str]",
        Type["str"],
        "typing.Type[str]",
    )
    show(
        "Type['list'] -> typing.Type[list]",
        Type["list"],
        "typing.Type[list]",
    )
    show(
        "Type['dict'] -> typing.Type[dict]",
        Type["dict"],
        "typing.Type[dict]",
    )
    show(
        "Type['None'] -> typing.Type[NoneType]",
        Type["None"],
        "typing.Type[NoneType]",
    )
    show(
        "Type['NoneType'] -> typing.Type[NoneType]",
        Type["NoneType"],  # type: ignore[reportUndefinedVariable]
        "typing.Type[NoneType]",
    )
    show(
        "Type['object'] -> typing.Type[object]",
        Type["object"],
        "typing.Type[object]",
    )
    show(
        "Type['complex'] -> typing.Type[complex]",
        Type["complex"],
        "typing.Type[complex]",
    )
    show(
        "Type['bool'] -> typing.Type[bool]",
        Type["bool"],
        "typing.Type[bool]",
    )
    show(
        "Type['float'] -> typing.Type[float]",
        Type["float"],
        "typing.Type[float]",
    )
    show(
        "Type['bytes'] -> typing.Type[bytes]",
        Type["bytes"],
        "typing.Type[bytes]",
    )
    show(
        "Type['set'] -> typing.Type[set]",
        Type["set"],
        "typing.Type[set]",
    )
    show(
        "Type['frozenset'] -> typing.Type[frozenset]",
        Type["frozenset"],
        "typing.Type[frozenset]",
    )
    show(
        "Type['tuple'] -> typing.Type[tuple]",
        Type["tuple"],
        "typing.Type[tuple]",
    )
    show(
        "Type['unknown_type'] -> typing.Type[Any]",
        Type["unknown_type"],  # type: ignore[reportUndefinedVariable]
        "typing.Type[typing.Any]",
    )

    show(
        "Nested Type with string args normalizes recursively",
        List[Type["int"]],
        "typing.List[typing.Type[int]]",
    )

    # ---------------------- Custom class preservation -------------
    # Define some custom classes for testing
    class CustomClass:
        pass

    class AnotherClass:
        pass

    show(
        "Type[custom_class] preserves actual class objects",
        Type[CustomClass],
        "typing.Type[__main__.CustomClass]",
    )
    show(
        "Type[AnotherClass] preserves actual class objects",
        Type[AnotherClass],
        "typing.Type[__main__.AnotherClass]",
    )
    show(
        "Union[custom_class, int] preserves actual class objects",
        Union[CustomClass, int],
        "typing.Union[__main__.CustomClass, int]",
    )
    show(
        "Union[int, custom_class] preserves actual class objects",
        Union[int, AnotherClass],
        "typing.Union[int, __main__.AnotherClass]",
    )
    show(
        "List[Type[custom_class]] preserves actual class objects",
        List[Type[CustomClass]],
        "typing.List[typing.Type[__main__.CustomClass]]",
    )
    show(
        "Dict[str, Type[custom_class]] preserves actual class objects",
        Dict[str, Type[CustomClass]],
        "typing.Dict[str, typing.Type[__main__.CustomClass]]",
    )
    show(
        "Union[Type[custom_class], Type[str]] mixed case",
        Union[Type[CustomClass], Type["str"]],
        "typing.Union[typing.Type[__main__.CustomClass], typing.Type[str]]",
    )
    show(
        "Callable[[Type[custom_class]], int] preserves actual class objects",
        Callable[[Type[CustomClass]], int],
        "typing.Callable[[typing.Type[__main__.CustomClass]], int]",
    )
