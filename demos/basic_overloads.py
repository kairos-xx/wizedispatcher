from wizedispatcher import dispatch


def greet(x) -> str:
    return "fallback"


@dispatch.greet(x=str)
def _(x) -> str:
    return f"hello {x}"


@dispatch.greet(int)
def _(x) -> str:
    return f"num {x}"


@dispatch.greet(x=bytes)
def _(x) -> str:
    return f"bytes {x!r}"


if __name__ == "__main__":
    print(greet("Ana"))  # hello Ana
    print(greet(7))  # num 7
    print(greet(b"abc"))  # bytes b'abc'
    print(greet(object()))  # fallback
