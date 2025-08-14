from .core import WILDCARD, TypeMatch, WizeDispatcher, dispatch
from .typingnormalize import TypingNormalize
from .version import __version__

__all__ = [
    "WizeDispatcher",
    "TypeMatch",
    "dispatch",
    "WILDCARD",
    "TypingNormalize",
    "__version__",
]
