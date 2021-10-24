"""This module serves as a compatibility layer between API-compatible
style preserving TOML editing libraries (e.g. atoml and atoml).
It makes it easy to swap between implementations for testing (by means of search and
replace).
"""
from collections.abc import Mapping, MutableSequence, Sequence
from functools import singledispatch
from typing import Iterable, Optional, Tuple, TypeVar, Union, cast

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

from ..errors import InvalidTOMLKey
from ..types import (
    KV,
    Commented,
    CommentedKV,
    CommentedList,
    CommentKey,
    IntermediateRepr,
    WhitespaceKey,
)

__all__ = [
    "dumps",
    "loads",
    "convert",
    "collapse",
]

T = TypeVar("T", bound=Union[TOMLDocument, Table, InlineTable])

MAX_INLINE_TABLE_LEN = 60
INLINE_TABLE_LONG_ELEM = 10
MAX_INLINE_TABLE_LONG_ELEM = 5
LONG = 120


def convert(irepr: IntermediateRepr) -> str:
    return dumps(collapse(irepr, root=True))


@singledispatch
def collapse(obj, root=False):
    # Catch all
    return obj


@collapse.register(Commented)
def _collapse_commented(obj: Commented, root=False) -> Item:
    return create_item(obj.value_or(None), obj.comment)


@collapse.register(CommentedList)
def _collapse_commented_list(obj: CommentedList, root=False) -> Array:
    out = array()
    out.multiline(False)  # Let's manually control the whitespace
    multiline = len(obj) > 1

    for entry in obj.data:
        values = entry.value_or([])
        if multiline:
            cast(list, out).append(Whitespace("\n" + 4 * " "))
        for value in values:
            cast(list, out).append(collapse(value))
        if entry.has_comment():
            if multiline:
                cast(list, out).append(_no_trail_comment(entry.comment))
            else:
                cast(Item, out).comment(entry.comment)
    if multiline:
        cast(list, out).append(Whitespace("\n"))

    return out


@collapse.register(CommentedKV)
def _collapse_commented_kv(obj: CommentedKV, root=False) -> Union[Table, InlineTable]:
    multiline = len(obj) > 1
    out: Union[Table, InlineTable] = table() if multiline else inline_table()

    for entry in obj.data:
        values = (v for v in entry.value_or([cast(KV, ())]) if v)
        k: Optional[str] = None  # if the for loop is empty, k = None
        for value in values:
            k, v = value
            out[cast(str, k)] = collapse(v)
        if not entry.has_comment():
            continue
        if not multiline:
            cast(Item, out).comment(entry.comment)
            obj.comment = entry.comment
            return out
        if k:
            out[k].comment(entry.comment)
        else:
            out.append(None, comment(entry.comment))  # type: ignore[arg-type]
    return out


@collapse.register(IntermediateRepr)
def _collapse_irepr(obj: IntermediateRepr, root=False):
    # guess a good repr
    if root:
        return _convert_irepr_to_toml(obj, document())
    rough_repr = repr(obj).replace(obj.__class__.__name__, "").strip()
    out = table() if len(rough_repr) > LONG or "\n" in rough_repr else inline_table()
    return _convert_irepr_to_toml(obj, cast(Union[Table, InlineTable], out))


@collapse.register(dict)
def _collapse_dict(obj: dict, root=False) -> Union[Table, InlineTable]:
    if not obj:
        return inline_table()
    out: Union[Table, InlineTable] = (
        table()
        if any(v and isinstance(v, (list, dict)) for v in obj.values())
        or len(repr(obj)) > LONG  # simple heuristic
        else inline_table()
    )
    for key, value in obj.items():
        out.append(key, collapse(value))
    return out


@collapse.register(list)
def _collapse_list(obj: list, root=False) -> Union[AoT, Array]:
    is_aot, max_len, has_nl, num_elem = classify_list(obj)
    # Just some heuristics which kind of array we are going to use
    if is_aot:
        return create_aot(collapse(e) for e in obj)

    out = array()
    cast(MutableSequence, out).extend(collapse(e) for e in obj)
    if (
        has_nl
        or max_len > MAX_INLINE_TABLE_LEN
        or (max_len > INLINE_TABLE_LONG_ELEM and num_elem > MAX_INLINE_TABLE_LONG_ELEM)
    ):
        out.multiline(True)
    return out


def _convert_irepr_to_toml(irepr: IntermediateRepr, out: T) -> T:
    if irepr.inline_comment and isinstance(out, Item):
        out.comment(irepr.inline_comment)
    for key, value in irepr.items():
        # TODO: prefer `add` once atoml's InlineTable supports it
        if isinstance(key, WhitespaceKey):
            out.append(None, nl())  # type: ignore[arg-type]
        elif isinstance(key, CommentKey):
            out.append(None, comment(value))  # type: ignore[arg-type]
        elif isinstance(key, tuple):
            parent_key, *rest = key
            if not isinstance(parent_key, str):
                raise InvalidTOMLKey(key)
            if len(rest) == 1:
                nested_key = rest[0]
                collapsed_value = collapse(value)
                collapsed_str = f"{nested_key} = {dumps(collapsed_value)}"
                # Force inline table for the simplest cases
                if (
                    not isinstance(collapsed_value, (Table, AoT))
                    and len(collapsed_str) < LONG
                    and "\n" not in collapsed_str.strip()
                ):
                    child = inline_table()
                    child[nested_key] = collapsed_value
                    out[parent_key] = child
                    continue
            else:
                nested_key = tuple(rest)
            p = out.setdefault(parent_key, {})
            if not isinstance(p, (Table, InlineTable)):
                msg = f"Value for `{parent_key}` expected to be a table, found {p!r}"
                raise ValueError(msg)
            _convert_irepr_to_toml(IntermediateRepr({nested_key: value}), p)
        elif isinstance(key, (int, str)):
            if isinstance(value, IntermediateRepr):
                _convert_irepr_to_toml(value, out.setdefault(str(key), {}))
            else:
                out[str(key)] = collapse(value)
    return out


# --- Helpers ---


def create_item(value, comment):
    obj = item(value)
    if comment is not None:
        obj.comment(comment)
    return obj


def create_table(m: Mapping) -> Table:
    if isinstance(m, Table):
        return m
    t = table()
    for k, v in m.items():
        t.add(k, v)
    return t


def create_aot(elements: Iterable[Mapping]) -> AoT:
    if isinstance(elements, AoT):
        return elements
    out = aot()
    cast(MutableSequence, out).extend(create_table(t) for t in elements)
    return out


def classify_list(seq: Sequence) -> Tuple[bool, int, bool, int]:
    """Expensive method that helps to choose what is the best TOML representation
    for a Python list.

    The return value is composed by 4 values, in order:
    - aot(bool): ``True`` if all elements are dict-like objects
    - max_len(int): Rough (and definitely not precise) estimative of the number of
      chars the TOML representation for the largest element would be.
    - has_nl(bool): if any TOML representation for the elements has a ``\\n`` char.
    - num_elements(int): number of elements in the list.
    """
    is_aot = True
    has_nl = False
    max_len = 0
    for elem in seq:
        is_aot = is_aot and isinstance(elem, Mapping)
        elem_repr = repr(elem)
        max_len = max(max_len, len(elem_repr))
        has_nl = has_nl or "\n" in elem_repr

    return is_aot, max_len, has_nl, len(seq)


def _no_trail_comment(msg: str):
    cmt = comment(str(msg))
    cmt.trivia.trail = ""
    return cmt
