from wizedispatcher import dispatch


def shape_base(a, b) -> str:
    _ = (a, b)
    return "base"


# candidate with *args (penalty -2)
@dispatch.shape_base(a=int, b=str)
def _(a, b, *args) -> str:
    _ = (a, b, args)
    return "varpos"


# candidate with **kwargs (penalty -1)
@dispatch.shape_base(a=int)
def _(a, b, **kwargs) -> str:
    _ = (a, b, kwargs)
    return "varkw"


def test_shape_bias_overloads_selected_and_penalized_paths_executed() -> None:
    # This should hit both overloads as candidates; the more specific (with b:str) should win
    assert shape_base(1, "x") == "varpos"
    # For a different b type, only the **kwargs variant matches on decorators; it should be chosen
    assert shape_base(1, 2) == "varkw"
