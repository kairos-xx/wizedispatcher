from typing import Dict

from wizedispatcher import dispatch

calls: Dict[str, int] = {"base": 0, "varpos": 0, "varkw": 0}


def f(a, b) -> str:
    calls["base"] += 1
    return f"base:{a}:{b}"


@dispatch.f(a=int, b=str)
def _(a, b, *args) -> str:
    calls["varpos"] += 1
    return f"varpos:{a}:{b}:{len(args)}"


@dispatch.f(a=int)
def _(a, b, **kwargs) -> str:
    calls["varkw"] += 1
    return f"varkw:{a}:{b}:{list(kwargs)}"


if __name__ == "__main__":
    print(f(1, "x"))  # varpos:1:x:0
    print(f(2, "y"))  # varpos:2:y:0 (cache hit for types)
    print(f(3, 4))  # varkw:3:4:[]
    print(f("a", "b"))  # base:a:b
    print("calls:", calls)
