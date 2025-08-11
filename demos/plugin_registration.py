from wizedispatcher import dispatch


# Consumer module API
def handle(event) -> str:
    _ = event
    return "default"


# Plugin A registers an overload
@dispatch.handle(event=dict)
def _(event) -> str:
    _ = event
    return f"dict:{sorted(event)}"


# Plugin B registers another overload
@dispatch.handle(event=list)
def _(event) -> str:
    _ = event
    return f"list:{len(event)}"


if __name__ == "__main__":
    print(handle({"a": 1, "b": 2}))  # dict:['a', 'b']
    print(handle([1, 2, 3]))  # list:3
    print(handle(object()))  # default
