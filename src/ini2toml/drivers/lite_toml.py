"""This module serves as a compatibility layer between API-compatible
style preserving TOML editing libraries (e.g. atoml and atoml).
It makes it easy to swap between implementations for testing (by means of search and
replace).
"""
from functools import singledispatch
from typing import Any

from tomli_w import dumps

from ..errors import InvalidTOMLKey
from ..types import (
    Commented,
    CommentedKV,
    CommentedList,
    CommentKey,
    IntermediateRepr,
    ListRepr,
    WhitespaceKey,
)

__all__ = [
    "dumps",
    "convert",
    "convert_dict",
]


def convert(irepr: IntermediateRepr) -> str:
    return dumps(convert_dict(irepr))


def convert_dict(irepr: IntermediateRepr) -> dict:
    out: dict = {}
    _convert_dict(irepr, out)
    return out


def _convert_dict(irepr: IntermediateRepr, out: dict):
    for key, value in irepr.items():
        if isinstance(key, (WhitespaceKey, CommentKey)):
            continue
        elif isinstance(key, tuple):
            parent_key, *rest = key
            if not isinstance(parent_key, str):
                raise InvalidTOMLKey(key)
            p = out.setdefault(parent_key, {})
            _convert_dict(IntermediateRepr({rest: value}), p)  # type: ignore
        elif isinstance(key, str):
            if isinstance(value, IntermediateRepr):
                _convert_dict(value, out.setdefault(key, {}))
            else:
                out[key] = _collapse(value)


@singledispatch
def _collapse(obj):
    # Catch all
    return obj


@_collapse.register(Commented)
def _collapse_scalar(obj: Commented) -> Any:
    return obj.value_or(None)


@_collapse.register(CommentedList)
def _collapse_list(obj: CommentedList) -> list:
    return obj.as_list()


@_collapse.register(CommentedKV)
def _collapse_dict(obj: CommentedKV) -> dict:
    return obj.as_dict()


@_collapse.register(IntermediateRepr)
def _collapse_irepr(obj: IntermediateRepr):
    out = {}
    _convert_dict(obj, out)
    return out


@_collapse.register(ListRepr)
def _collapse_list_repr(obj: ListRepr) -> list:
    return [_collapse(e) for e in obj]
