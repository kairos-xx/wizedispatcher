from __future__ import annotations

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
from re import Match as ReMatch
from re import Pattern as RePattern
from types import UnionType
from typing import (
    AbstractSet,
    Any,
    AsyncContextManager,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    ByteString,
    Callable,
    ChainMap,
    Collection,
    Concatenate,
    Container,
    Coroutine,
    Counter,
    DefaultDict,
    Deque,
    Dict,
    FrozenSet,
    Generator,
    Hashable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    List,
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
      * Bare typing generics gain sensible Any defaults (e.g., Type[Any]).
      * Callable with ParamSpec/Concatenate → Callable[..., R].
      * Generic arguments are normalized recursively.
    """

    def __new__(cls, tp: object) -> object:
        """Return the normalized typing form of ``tp``.

        Args:
          tp: Any annotation or runtime type to normalize.

        Returns:
          A typing.* object representing the normalized annotation.

        Raises:
          Nothing.
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

        Raises:
          Nothing.
        """
        return hasattr(obj, "__constraints__") and (obj.__class__.__name__ == "TypeVar")

    @staticmethod
    def _is_paramspec(obj: object) -> bool:
        """Return True if obj appears to be a ParamSpec.

        Args:
          obj: Object to test.

        Returns:
          True if obj behaves like a ParamSpec, else False.

        Raises:
          Nothing.
        """
        return (
            hasattr(obj, "args")
            and hasattr(obj, "kwargs")
            and (obj.__class__.__name__ == "ParamSpec")
        )

    @staticmethod
    def _is_union_like(tp: object) -> bool:
        """Return True if ``tp`` is a typing or PEP 604 union.

        Args:
          tp: Type expression to inspect.

        Returns:
          True if union-like, else False.

        Raises:
          Nothing.
        """
        origin: object | None = get_origin(tp)
        return origin is Union or isinstance(tp, UnionType)

    @staticmethod
    def _is_callable_origin(origin: object | None) -> bool:
        """Return True if origin corresponds to collections.abc.Callable.

        Args:
          origin: Value from typing.get_origin(...).

        Returns:
          True if it is the Callable origin, else False.

        Raises:
          Nothing.
        """
        return origin is AbcCallable

    @staticmethod
    def _is_concatenate(tp: object) -> bool:
        """Return True if ``tp`` is typing.Concatenate[...].

        Args:
          tp: Type expression to inspect.

        Returns:
          True if it is a Concatenate, else False.

        Raises:
          Nothing.
        """
        return get_origin(tp) is Concatenate

    # -------------------- core normalization --------------------

    @staticmethod
    def _norm(tp: object) -> object:
        """Normalize any annotation to canonical typing constructs.

        Args:
          tp: Any annotation or runtime type.

        Returns:
          A typing.* object where generics and unions are normalized.

        Raises:
          Nothing.
        """
        if TypingNormalize._is_typevar(tp):
            constraints: Tuple[object, ...] = getattr(tp, "__constraints__", ())
            bound: object | None = getattr(tp, "__bound__", None)
            if constraints:
                return TypingNormalize._to_union(*constraints)
            return Any if bound is None else TypingNormalize._norm(bound)

        if TypingNormalize._is_paramspec(tp):
            return Any

        if TypingNormalize._is_union_like(tp):
            return TypingNormalize._to_union(*get_args(tp))

        # Bare typing generics (e.g., List, Dict, Type) → defaults
        defaulted: object | None = TypingNormalize._plain_typing_to_defaults(tp)
        if defaulted is not None:
            return defaulted

        origin: object | None = get_origin(tp)

        if TypingNormalize._is_callable_origin(origin):
            params_ret: Tuple[object, ...] = get_args(tp)
            if len(params_ret) != 2:
                return Callable[..., Any]
            params: object = params_ret[0]
            ret: object = TypingNormalize._norm(params_ret[1])

            if isinstance(params, list):
                plist: List[object] = [TypingNormalize._norm(p) for p in params]
                return TypingNormalize._tsub("Callable", (plist, ret))

            if (
                params is Ellipsis
                or TypingNormalize._is_paramspec(params)
                or TypingNormalize._is_concatenate(params)
            ):
                return TypingNormalize._tsub("Callable", (Ellipsis, ret))

            return TypingNormalize._tsub("Callable", (Ellipsis, ret))

        if origin is not None:
            args_in: Tuple[object, ...] = get_args(tp)
            return TypingNormalize._from_origin(
                origin, tuple(TypingNormalize._norm(a) for a in args_in)
            )

        return TypingNormalize._plain_runtime_to_typing(tp)

    # -------------------- union machinery --------------------

    @staticmethod
    def _to_union(*parts: object) -> object:
        """Build typing.Union[...] from arbitrary union-like parts.

        Args:
          parts: Pieces that may include unions or plain types.

        Returns:
          A flattened typing.Union[...] with None first if present, or a
          single member type if only one remains.

        Raises:
          Nothing.
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

        if not uniq:
            return TypingNormalize._tsub("Union", ((),))

        if has_none:
            uniq = [none_t] + [x for x in uniq if x is not none_t]

        if len(uniq) == 1:
            return uniq[0]

        return TypingNormalize._tsub("Union", (tuple(uniq),))

    @staticmethod
    def _explode(items: Tuple[object, ...]) -> List[object]:
        """Flatten nested union-like structures.

        Args:
          items: Candidate types which may contain unions.

        Returns:
          A flat list of normalized, non-union parts.

        Raises:
          Nothing.
        """
        out: List[object] = []
        for it in items:
            itn: object = TypingNormalize._norm(it)
            if TypingNormalize._is_union_like(itn):
                out.extend(TypingNormalize._explode(get_args(itn)))
            else:
                out.append(itn)
        return out

    # -------- origins/builtins/ABCs/concrete → typing names -----

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

    @staticmethod
    def _from_origin(origin: object, args: Tuple[object, ...]) -> object:
        """Build a typing.* type from an origin and normalized args.

        Args:
          origin: The origin returned by typing.get_origin(...).
          args: The already normalized generic arguments.

        Returns:
          A typing.* object (e.g., typing.List[T]) built from the origin.

        Raises:
          Nothing.
        """
        name: str | None = TypingNormalize._ORIGIN_TO_TYPING.get(origin)
        if name is None:
            try:
                return origin[args]
            except Exception:
                return origin

        if name == "Tuple" and args and args[-1] is Ellipsis:
            fixed: Tuple[object, ...] = tuple(args[:-1]) + (Ellipsis,)
            return TypingNormalize._tsub("Tuple", fixed)

        return TypingNormalize._tsub(name, args)

    @staticmethod
    def _plain_runtime_to_typing(tp: object) -> object:
        """Map bare runtime builtins/ABCs to typing with Any defaults.

        Args:
          tp: A non-parameterized builtin or ABC or concrete collection.

        Returns:
          A typing.* type with default Any params, or the input if unknown.

        Raises:
          Nothing.
        """
        if tp is list:
            return TypingNormalize._tsub("List", (Any,))
        if tp is dict:
            return TypingNormalize._tsub("Dict", (Any, Any))
        if tp is set:
            return TypingNormalize._tsub("Set", (Any,))
        if tp is frozenset:
            return TypingNormalize._tsub("FrozenSet", (Any,))
        if tp is tuple:
            return TypingNormalize._tsub("Tuple", (Any, Ellipsis))
        if tp is type:
            return TypingNormalize._tsub("Type", (Any,))
        if tp is AbcCallable or tp is callable:
            return TypingNormalize._tsub("Callable", (Ellipsis, Any))

        name: str | None = TypingNormalize._ORIGIN_TO_TYPING.get(tp)
        if name is not None:
            return TypingNormalize._typing_defaults_by_name(name)

        # Not recognized; leave as-is
        return tp

    @staticmethod
    def _plain_typing_to_defaults(tp: object) -> object | None:
        """Return defaulted typing generics for bare typing.* names.

        Args:
          tp: A typing.* generic like List, Dict, Type, Mapping, etc.

        Returns:
          A parameterized typing.* type with Any defaults, or None if
          ``tp`` is not a bare typing generic.

        Raises:
          Nothing.
        """
        typing_map: Dict[object, str] = {
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
        name: str | None = typing_map.get(tp)
        return None if name is None else TypingNormalize._typing_defaults_by_name(name)

    @staticmethod
    def _typing_defaults_by_name(name: str) -> object:
        """Build parameterized typing.* defaults by standardized name.

        Args:
          name: Standardized typing name (e.g., 'List', 'Type').

        Returns:
          A parameterized typing.* type with Any defaults.

        Raises:
          Nothing.
        """
        if name == "List":
            return TypingNormalize._tsub("List", (Any,))
        if name == "Dict":
            return TypingNormalize._tsub("Dict", (Any, Any))
        if name == "Set":
            return TypingNormalize._tsub("Set", (Any,))
        if name == "FrozenSet":
            return TypingNormalize._tsub("FrozenSet", (Any,))
        if name == "Tuple":
            return TypingNormalize._tsub("Tuple", (Any, Ellipsis))
        if name == "Type":
            return TypingNormalize._tsub("Type", (Any,))
        if name == "Deque":
            return TypingNormalize._tsub("Deque", (Any,))
        if name == "DefaultDict":
            return TypingNormalize._tsub("DefaultDict", (Any, Any))
        if name == "OrderedDict":
            return TypingNormalize._tsub("OrderedDict", (Any, Any))
        if name == "Counter":
            return TypingNormalize._tsub("Counter", (Any,))
        if name == "ChainMap":
            return TypingNormalize._tsub("ChainMap", (Any,))
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
            return TypingNormalize._tsub(name, (Any,))
        if name in {"Coroutine", "Generator"}:
            return TypingNormalize._tsub(name, (Any, Any, Any))
        if name in {"MappingView", "KeysView", "ItemsView", "ValuesView"}:
            return getattr(__import__("typing"), name)
        if name == "Callable":
            return TypingNormalize._tsub("Callable", (Ellipsis, Any))
        if name == "Union":
            return TypingNormalize._tsub("Union", ((),))
        return getattr(__import__("typing"), name)

    # ------------- minimal typing[...] subscript builder -------------

    @staticmethod
    def _tsub(typing_name: str, args: object) -> object:
        """Build ``typing.<Name>[...]`` without ignores, casts, or eval.

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
            return Union[args]

        if typing_name == "Callable":
            if not isinstance(args, tuple) or len(args) != 2:
                raise ValueError("Callable expects (params, return).")
            params: object = args[0]
            ret: object = args[1]
            if params is Ellipsis:
                return Callable[..., ret]
            if isinstance(params, list):
                return Callable[params, ret]
            raise ValueError("Callable params must be list or Ellipsis.")

        typing_map: Dict[str, object] = {
            "List": List,
            "Dict": Dict,
            "Set": Set,
            "FrozenSet": FrozenSet,
            "Tuple": Tuple,
            "Type": Type,
            "Deque": Deque,
            "DefaultDict": DefaultDict,
            "OrderedDict": OrderedDict,
            "Counter": Counter,
            "ChainMap": ChainMap,
            "Mapping": Mapping,
            "MutableMapping": MutableMapping,
            "Sequence": Sequence,
            "MutableSequence": MutableSequence,
            "Iterable": Iterable,
            "Iterator": Iterator,
            "Collection": Collection,
            "AbstractSet": AbstractSet,
            "ByteString": ByteString,
            "Reversible": Reversible,
            "Sized": Sized,
            "Container": Container,
            "Hashable": Hashable,
            "Awaitable": Awaitable,
            "Coroutine": Coroutine,
            "AsyncIterable": AsyncIterable,
            "AsyncIterator": AsyncIterator,
            "Generator": Generator,
            "MappingView": MappingView,
            "KeysView": KeysView,
            "ItemsView": ItemsView,
            "ValuesView": ValuesView,
            "AsyncContextManager": AsyncContextManager,
            "Pattern": Pattern,
            "Match": Match,
        }

        target: object | None = typing_map.get(typing_name)
        if target is None:
            raise ValueError(f"Unknown typing target: {typing_name!r}")

        if isinstance(args, tuple):
            return target[args]

        raise ValueError("Generic expects a tuple of arguments.")


if __name__ == "__main__":

    def show(title: str, input_tp: object) -> None:
        """Print a normalized annotation demo line.

        Args:
          title: Short label for the case being demonstrated.
          input_tp: The input type/expression to normalize.

        Returns:
          Nothing. Prints to stdout.

        Raises:
          Nothing.
        """
        print(f"{title:34s} in : {input_tp!r}")
        print(f"{'':34s} out: {TypingNormalize(input_tp)!r}\n")

    # ---------------------- TypeVar cases -----------------------
    T: TypeVar = TypeVar("T", str, bytes)
    U: TypeVar = TypeVar("U", bound=BaseException)
    V: TypeVar = TypeVar("V")  # unconstrained → Any

    show("TypeVar constrained", T)
    show("TypeVar bound", U)
    show("TypeVar unconstrained", V)

    # ---------------------- ParamSpec / Concatenate -------------
    P: ParamSpec = ParamSpec("P")
    show("Callable[P,int]", Callable[P, int])
    show("Callable[Concatenate[int,P],str]", Callable[Concatenate[int, P], str])

    # ---------------------- Optional / '|' unions ----------------
    show("Optional[int]", Optional[int])
    show("PEP604 int|str|None", int | str | None)
    show("Nested Union flatten", Union[Union[int, str], Union[str, bytes]])

    # ---------------------- Builtins (PEP 585) -------------------
    show("list[int|str]", list[int | str])
    show("dict[str,bytes]", dict[str, bytes])
    show("set[bytes]", set[bytes])
    show("frozenset[int]", frozenset[int])
    show("tuple[int,str]", tuple[int, str])
    show("tuple[int,...]", tuple[int, ...])
    show("type[int]", type[int])
    show("callable[[int,str],bytes]", callable[[int, str], bytes])

    # Bare builtins -> typing with Any defaults
    show("list", list)
    show("dict", dict)
    show("tuple", tuple)
    show("type", type)
    show("callable", callable)

    # ---------------------- collections concrete -----------------
    show("collections.deque[int]", CollDeque[int])
    show("collections.defaultdict[str,int]", CollDefaultDict[str, int])
    show("collections.OrderedDict[str,int]", CollOrderedDict[str, int])
    show("collections.Counter[int]", CollCounter[int])
    show("collections.ChainMap[str,int]", CollChainMap[str, int])

    # Bare concrete -> defaults
    show("collections.deque", CollDeque)
    show("collections.defaultdict", CollDefaultDict)
    show("collections.OrderedDict", CollOrderedDict)
    show("collections.Counter", CollCounter)
    show("collections.ChainMap", CollChainMap)

    # ---------------------- collections.abc ----------------------
    show("abc Mapping[str,int]", AbcMapping[str, int])
    show("abc Sequence[int]", AbcSequence[int])
    show("abc Iterable[int]", AbcIterable[int])
    show("abc AsyncIterator[int]", AbcAsyncIterator[int])
    show("abc Generator[int,int,int]", AbcGenerator[int, int, int])

    # ---------------------- regex runtime ↔ typing ---------------
    show("re.Pattern[str]", RePattern[str])
    show("re.Match[str]", ReMatch[str])
    show("re.Pattern bare", RePattern)
    show("re.Match bare", ReMatch)

    # ---------------------- Bare typing generics -----------------
    show("typing.List", List)
    show("typing.Dict", Dict)
    show("typing.Set", Set)
    show("typing.FrozenSet", FrozenSet)
    show("typing.Tuple", Tuple)
    show("typing.Type", Type)
    show("typing.Deque", Deque)
    show("typing.DefaultDict", DefaultDict)
    show("typing.OrderedDict", OrderedDict)
    show("typing.Counter", Counter)
    show("typing.ChainMap", ChainMap)
    show("typing.Mapping", Mapping)
    show("typing.MutableMapping", MutableMapping)
    show("typing.Sequence", Sequence)
    show("typing.MutableSequence", MutableSequence)
    show("typing.Iterable", Iterable)
    show("typing.Iterator", Iterator)
    show("typing.Collection", Collection)
    show("typing.AbstractSet", AbstractSet)
    show("typing.ByteString", ByteString)
    show("typing.Reversible", Reversible)
    show("typing.Sized", Sized)
    show("typing.Container", Container)
    show("typing.Hashable", Hashable)
    show("typing.Awaitable", Awaitable)
    show("typing.Coroutine", Coroutine)
    show("typing.AsyncIterable", AsyncIterable)
    show("typing.AsyncIterator", AsyncIterator)
    show("typing.Generator", Generator)
    show("typing.AsyncContextManager", AsyncContextManager)
    show("typing.Pattern", Pattern)
    show("typing.Match", Match)
    show("typing.Callable", Callable)
    show("typing.Union", Union)

    # ---------------------- Nested generics ----------------------
    show(
        "dict[str|None, list[Optional[int|bytes]]]",
        dict[str | None, list[Optional[int | bytes]]],
    )
    show("List[Dict[str, List[int|str]]]", List[Dict[str, List[int | str]]])

    # ---------------------- Callable specifics -------------------
    show(
        "Callable[[list[int|str], Optional[bytes]], Optional[str]]",
        Callable[[list[int | str], Optional[bytes]], Optional[str]],
    )
    """
    TypeVar constrained                in : ~T
    Traceback (most recent call last):
      File "/home/runner/workspace/t.py", line 651, in <module>
        show("TypeVar constrained", T)
      File "/home/runner/workspace/t.py", line 644, in show
        print(f"{'':34s} out: {TypingNormalize(input_tp)!r}\n")
                               ^^^^^^^^^^^^^^^^^^^^^^^^^
      File "/home/runner/workspace/t.py", line 112, in __new__
        return cls._norm(tp)
               ^^^^^^^^^^^^^
      File "/home/runner/workspace/t.py", line 214, in _norm
        return TypingNormalize._to_union(*constraints)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      File "/home/runner/workspace/t.py", line 295, in _to_union
        return TypingNormalize._tsub("Union", (tuple(uniq), ))
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      File "/home/runner/workspace/t.py", line 566, in _tsub
        return Union[args]
               ~~~~~^^^^^^
      File "/nix/store/7d088dip86hlzri9sk0h78b63yfmx0a0-python3-3.11.13/lib/python3.11/typing.py", line 379, in inner
        return func(*args, **kwds)
               ^^^^^^^^^^^^^^^^^^^
      File "/nix/store/7d088dip86hlzri9sk0h78b63yfmx0a0-python3-3.11.13/lib/python3.11/typing.py", line 502, in __getitem__
        return self._getitem(self, parameters)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      File "/nix/store/7d088dip86hlzri9sk0h78b63yfmx0a0-python3-3.11.13/lib/python3.11/typing.py", line 715, in Union
        parameters = tuple(_type_check(p, msg) for p in parameters)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      File "/nix/store/7d088dip86hlzri9sk0h78b63yfmx0a0-python3-3.11.13/lib/python3.11/typing.py", line 715, in <genexpr>
        parameters = tuple(_type_check(p, msg) for p in parameters)
                           ^^^^^^^^^^^^^^^^^^^
      File "/nix/store/7d088dip86hlzri9sk0h78b63yfmx0a0-python3-3.11.13/lib/python3.11/typing.py", line 197, in _type_check
        raise TypeError(f"{msg} Got {arg!r:.100}.")
    TypeError: Union[arg, ...]: each arg must be a type. Got (<class 'str'>, <class 'bytes'>).
    """
