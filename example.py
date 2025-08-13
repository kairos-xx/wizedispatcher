from collections.abc import Callable
from inspect import stack
from typing import Any
from wizedispatcher import dispatch


def get_name() -> str:
    return stack()[1].function


class Test:

    def method(self, x, y: Callable) -> str:
        """
        [fallback] x=Any, y=Callable
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @dispatch.method
    def method_dispatch01(self, x: int, y: int) -> str:
        """
        [dispatch decorator] x=int, y=int
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @dispatch.method
    def method_dispatch02(self, x: str, y: str) -> str:
        """
        [dispatch decorator] x=str, y=str
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @dispatch.method(x=float)
    def method_dispatch03(self, y: float) -> str:
        """
        [dispatch decorator] x=float + 
        [dispatch method] y=float
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @dispatch.method(bool, bool)
    def method_dispatch04(self) -> str:
        """
        [dispatch decorator - positional arguments] x=bool, y=bool
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @dispatch.method(Callable)
    def method_dispatch05(self) -> str:
        """
        [dispatch decorator - positional arguments] x=Callable + 
        [fallback] y=Callable
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @classmethod
    def class_method(cls, x, y) -> str:
        """
        [fallback]  x=Any, y=Any
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @dispatch.class_method
    @classmethod
    def class_method_dispatch01(cls, x: int, y: int) -> str:
        """
        [dispatch decorator before 'classmethod' decorator]
        [dispatch method] x=int, y=int
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @classmethod
    @dispatch.class_method
    def class_method_dispatch02(cls, x: str, y: str) -> str:
        """
        [dispatch decorator after 'classmethod' decorator]
        [dispatch method] x=str, y=str
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @staticmethod
    def static_method(x, y) -> str:
        """
        [fallback]  x=Any, y=Any
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @dispatch.static_method
    @staticmethod
    def static_method_dispatch01(x: int, y: int) -> str:
        """
        [dispatch decorator before 'staticmethod' decorator]
        [dispatch method] x=int, y=int
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")

    @staticmethod
    @dispatch.static_method
    def static_method_dispatch02(x: str, y: str) -> str:
        """
        [dispatch decorator after 'staticmethod' decorator]
        [dispatch method] x=str, y=str
        """
        return (f"Called from: {get_name()} "
                f"with x={x} and y={y}")


def function(x, y="default", **kwargs) -> str:
    """
    [fallback] x=Any, y=str, **kwargs=Dict[str, Any]
    """
    return (f"Called from: {get_name()} "
            f"with x={x} and y={y}")


@dispatch.function
def function_dispatch01(x: int, *args) -> str:
    """
    [dispatch function] x=int, *args=Tuple[Any, ...] +
    [fallback] **kwargs=Dict[str, Any]
    """
    return (f"Called from: {get_name()} "
            f"with x={x} and y={y}")


@dispatch.function
def function_dispatch02(x: float, **kwargs) -> str:
    """
    [dispatch function] x=float, **kwargs=Dict[str, Any] +
    [fallback] y=Any
    """
    return (f"Called from: {get_name()} "
            f"with x={x} and y={y}")


@dispatch.function
def function_dispatch03(x: float, y: float) -> str:
    """
    [dispatch function] x=float, y=float +
    [fallback] **kwargs=Dict[str, Any]
    """
    return (f"Called from: {get_name()} "
            f"with x={x} and y={y}")


t: Test = Test()
print(t.method(1, 2))  # method_dispatch01
print(t.method("a", "b"))  # method_dispatch02
print(t.method(1.0, 2.0))  # method_dispatch03
print(t.method(True, False))  # method_dispatch04
print(t.method(function, function))  # method_dispatch05
print(Test.class_method(1, 2))  # class_method_dispatch01
print(Test.class_method("a", "b"))  # class_method_dispatch02
print(Test.static_method(1, 2))  # static_method_dispatch01
print(Test.static_method("a", "b"))  # static_method_dispatch02
print(function(1))  # function_dispatch01
print(function(1.0, z=9))  # function_dispatch02
print(function(1.0, y=2.0))  # function_dispatch03
"""
missing cases:
"""


def missing(x, *args, **kwargs) -> str:
    """
    [fallback] x=Any, *args=Tuple[Any, ...], **kwargs=Dict[str, Any]
    """
    return (f"Called from: {get_name()} "
            f"with x={x} "
            f"and args={args} and kwargs={kwargs}")

@dispatch.missing
def missing_dispatch01(x: int, y: int) -> str:
    """
    [dispatch function] x=int, y=int +
    [fallback] *args=Tuple[Any, ...], **kwargs=Dict[str, Any]
    """
    return (f"Called from: {get_name()} "
            f"with x={x} and y={y} "
            f"and args={args} and kwargs={kwargs}")

@dispatch.missing
def missing_dispatch02(x: int, *args) -> str:
    """
    [dispatch function] x=int, *args=Tuple[Any, ...] +
    [fallback] **kwargs=Dict[str, Any]
    """
    return (f"Called from: {get_name()} "
            f"with x={x} " 
            f"and args={args} and kwargs={kwargs}")

"""
both these 2 prints fail with the same error:
"""
print(missing(1, 2))
print(missing(x=1, y=2))
"""
Traceback (most recent call last):
  File "/home/runner/workspace/example.py", line 193, in <module>
    print(missing(1, 2))
          ^^^^^^^^^^^^^
  File "/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages/wizedispatcher/core.py", line 1092, in <lambda>
    lambda *a, **k: regmap[target_name]._dispatch(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages/wizedispatcher/core.py", line 803, in _dispatch
    return self._invoke(chosen, bound)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages/wizedispatcher/core.py", line 696, in _invoke
    return func(**dict(bound.arguments))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages/wizedispatcher/core.py", line 661, in adapter
    return func(
           ^^^^^
TypeError: missing_dispatch01() missing 1 required positional argument: 'y'
"""