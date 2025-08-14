from wizedispatcher import dispatch


def shape_base(a, b) -> str:
    """Fallback returning base marker; used to test shape bias."""
    _ = (a, b)
    return "base"


# candidate with *args (penalty -2)
@dispatch.shape_base(a=int, b=str)
def _(a, b, *args) -> str:
    """Overload with var-positional; incurs small penalty."""
    _ = (a, b, args)
    return "varpos"


# candidate with **kwargs (penalty -1)
@dispatch.shape_base(a=int)
def _(a, b, **kwargs) -> str:
    """Overload with var-keyword; slight penalty vs varpos."""
    _ = (a, b, kwargs)
    return "varkw"


def test_shape_bias_overloads_selected_and_penalized_paths_executed() -> None:
    """Both candidates considered; more specific should win for b:str."""
    assert shape_base(1, "x") == "varpos"
    # For different b type, only **kwargs variant matches via decorators
    assert shape_base(1, 2) == "varkw"
