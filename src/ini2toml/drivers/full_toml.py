"""This module serves as a compatibility layer between API-compatible
style preserving TOML editing libraries (e.g. atoml and atoml).
It makes it easy to swap between implementations for testing (by means of search and
replace).
"""
from functools import singledispatch
from typing import Optional, Union, cast

from atoml import (
    aot,
    array,
    comment,
    document,
    dumps,
    inline_table,
    item,
    loads,
    nl,
    table,
)
from atoml.items import AoT, Array, InlineTable, Item, Table, Whitespace
from atoml.toml_document import TOMLDocument

from ..types import (
    KV,
    Commented,
    CommentedKV,
    CommentedList,
    CommentKey,
    IntermediateRepr,
    ListRepr,
    WhitespaceKey,
)

__all__ = ["dumps", "loads", "convert", "convert_toml"]


def convert(irepr: IntermediateRepr) -> str:
    return dumps(convert_toml(irepr))


def convert_toml(irepr: IntermediateRepr) -> TOMLDocument:
    out = document()
    _convert_toml(irepr, out)
    return out


def _convert_toml(
    irepr: IntermediateRepr, out: Union[TOMLDocument, Table, InlineTable]
):
    if irepr.inline_comment and isinstance(out, Item):
        out.comment(irepr.inline_comment)
    for key, value in irepr.items():
        if isinstance(key, WhitespaceKey):
            out.append(None, nl())  # TODO: use `add` when InlineTable allow it
        elif isinstance(key, CommentKey):
            out.append(None, comment(value))
        elif isinstance(key, tuple):
            parent_key, *rest = key
            if not isinstance(parent_key, str):
                raise InvalidTOMLKey(key)
            p = out.setdefault(parent_key, {})
            nested_key = rest[0] if len(rest) == 1 else tuple(rest)
            _convert_toml(IntermediateRepr({nested_key: value}), p)
        elif isinstance(key, str):
            if isinstance(value, IntermediateRepr):
                _convert_toml(value, out.setdefault(key, {}))
            else:
                out[key] = _collapse(value)


def create_item(value, comment):
    obj = item(value)
    if comment is not None:
        obj.comment(comment)
    return obj


@singledispatch
def _collapse(obj):
    # Catch all
    return obj


@_collapse.register(Commented)
def _collapse_scalar(obj: Commented) -> Item:
    return create_item(obj.value_or(None), obj.comment)


@_collapse.register(CommentedList)
def _collapse_list(obj: CommentedList) -> Array:
    out = array()
    out.multiline(False)  # Let's manually control the whitespace
    multiline = len(obj) > 1

    for entry in obj.data:
        values = entry.value_or([])
        if multiline:
            cast(list, out).append(Whitespace("\n" + 4 * " "))
        for value in values:
            cast(list, out).append(value)
        if entry.has_comment():
            if multiline:
                cast(list, out).append(_no_trail_comment(entry.comment))
            else:
                cast(Item, out).comment(entry.comment)
    if multiline:
        cast(list, out).append(Whitespace("\n"))

    return out


@_collapse.register(CommentedKV)
def _collapse_dict(obj: CommentedKV) -> Union[Table, InlineTable]:
    multiline = len(obj) > 1
    out: Union[Table, InlineTable] = table() if multiline else inline_table()

    for entry in obj.data:
        values = (v for v in entry.value_or([cast(KV, ())]) if v)
        k: Optional[str] = None
        for value in values:
            k, v = value
            out[k] = v
        if not entry.has_comment():
            continue
        if not multiline:
            out.comment(entry.comment)
            obj.comment = entry.comment
            return out
        if k:
            out[k].comment(entry.comment)
        else:
            out.append(None, comment(entry.comment))
    return out


@_collapse.register(IntermediateRepr)
def _collapse_irepr(obj: IntermediateRepr):
    # guess a good repr
    rough_repr = repr(obj).replace(obj.__class__.__name__, "").strip()
    out = table() if len(rough_repr) > 120 or "\n" in rough_repr else inline_table()
    _convert_toml(obj, out)
    return out


@_collapse.register(ListRepr)
def _collapse_list_repr(obj: ListRepr) -> Union[AoT, Array]:
    is_aot, max_len, has_nl, num_elem = obj.classify()
    # Just some heuristics which kind of array we are going to use
    if is_aot:
        out = aot()
    else:
        out = array()
        if has_nl or max_len > 80 or (max_len > 10 and num_elem > 6):
            out.multiline(True)
    for elem in obj:
        out.append(_collapse(elem))
    return out


def _no_trail_comment(msg: str):
    cmt = comment(msg)
    cmt.trivia.trail = ""
    return cmt


class InvalidTOMLKey(ValueError):
    """{key!r} is not a valid key in the intermediate TOML representation"""

    def __init__(self, key):
        msg = self.__doc__.format(key=key)
        super().__init__(msg)
