"""This module serves as a compatibility layer between API-compatible
style preserving TOML editing libraries (e.g. atoml and atoml).
It makes it easy to swap between implementations for testing (by means of search and
replace).
"""
from functools import singledispatch
from typing import Any

from tomli_w import dumps

from ..errors import InvalidTOMLKey
from ..types import Commented, CommentedKV, CommentedList, HiddenKey, IntermediateRepr

__all__ = [
    "dumps",
    "convert",
    "collapse",
]


def convert(irepr: IntermediateRepr) -> str:
    return dumps(collapse(irepr))


@singledispatch
def collapse(obj):
    # Catch all
    return obj


@collapse.register(Commented)
def _collapse_commented(obj: Commented) -> Any:
    return obj.value_or(None)


@collapse.register(CommentedList)
def _collapse_commented_list(obj: CommentedList) -> list:
    return obj.as_list()


@collapse.register(CommentedKV)
def _collapse_commented_kv(obj: CommentedKV) -> dict:
    return obj.as_dict()


@collapse.register(IntermediateRepr)
def _collapse_irepr(obj: IntermediateRepr) -> dict:
    return _convert_irepr_to_dict(obj, {})


@collapse.register(list)
def _collapse_list_repr(obj: list) -> list:
    return [collapse(e) for e in obj]


def _convert_irepr_to_dict(irepr: IntermediateRepr, out: dict) -> dict:
    for key, value in irepr.items():
        if isinstance(key, HiddenKey):
            continue
        elif isinstance(key, tuple):
            parent_key, *rest = key
            if not isinstance(parent_key, str):
                raise InvalidTOMLKey(key)
            p = out.setdefault(parent_key, {})
            nested_key = rest[0] if len(rest) == 1 else tuple(rest)
            _convert_irepr_to_dict(IntermediateRepr({nested_key: value}), p)
        elif isinstance(key, str):
            if isinstance(value, IntermediateRepr):
                _convert_irepr_to_dict(value, out.setdefault(key, {}))
            else:
                out[key] = collapse(value)
    return out
