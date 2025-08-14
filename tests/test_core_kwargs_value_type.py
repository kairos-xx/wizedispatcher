from inspect import Parameter, Signature
from typing import Dict, List

from wizedispatcher.core import TypeMatch


def test_kwargs_value_type_from_varkw_mapping() -> None:
    """Extract value type from **kwargs Mapping annotation."""

    def f(**kw: Dict[str, int]): ...

    # Extract the annotation from the function signature
    params: List[Parameter] = list(
        Signature.from_callable(f).parameters.values()
    )
    varkw: Parameter = next(
        p for p in params if p.kind == Parameter.VAR_KEYWORD
    )
    # Should return the value type (second arg), i.e., int
    assert TypeMatch._kwargs_value_type_from_varkw(varkw.annotation) is int
