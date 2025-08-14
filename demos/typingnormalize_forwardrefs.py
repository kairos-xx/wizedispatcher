"""TypingNormalize forward refs and strings demo.

This demo focuses on normalization within Type[...] where the argument is a
string or a ForwardRef. It also shows preservation of actual classes inside
Type[...] and Union[...] constructs.

Run
  python -m demos.typingnormalize_forwardrefs
"""

from __future__ import annotations

from typing import Type, Union

from wizedispatcher.typingnormalize import TypingNormalize


class User:
    """Simple sentinel class used for normalized reprs."""

    pass


def main() -> None:
    """Print normalized forms for Type[...] and unions with classes."""
    print("Type['int']:", repr(TypingNormalize(Type["int"])))  # type: ignore[valid-type]
    print("Type[User]:", repr(TypingNormalize(Type[User])))
    print(
        "Union[User,int]:",
        repr(TypingNormalize(Union[User, int])),
    )


if __name__ == "__main__":
    main()


