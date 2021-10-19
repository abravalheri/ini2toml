"""This module serves as a compatibility layer between API-compatible
style preserving TOML editing libraries (e.g. atoml and atoml).
It makes it easy to swap between implementations for testing (by means of search and
replace).
"""
try:
    from tomli_w import dumps
except ImportError:  # pragma: no cover
    # Let's try another API-compatible popular library as a last hope
    from toml import dumps  # type: ignore

from ..types import IntermediateRepr
from . import plain_builtins

__all__ = [
    "convert",
]


def convert(irepr: IntermediateRepr) -> str:
    return dumps(plain_builtins.convert(irepr))
