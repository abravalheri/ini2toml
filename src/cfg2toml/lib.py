"""Reusable post-processing and type casting operations"""
from collections import UserList
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)

from tomlkit import array, comment, inline_table, table
from tomlkit.container import Container
from tomlkit.items import Array, InlineTable, Item, Table

NotGiven = Enum("NotGiven", "NOT_GIVEN")
NOT_GIVEN = NotGiven.NOT_GIVEN

CP = "#;"
"""Default Comment Prefixes"""

T = TypeVar("T")
S = TypeVar("S")
C = TypeVar("C", bound="Container")
KV = Tuple[str, T]
CoerceFn = Callable[[str], T]
Transformation = Callable[[str], Any]


@dataclass
class Commented(Generic[T]):
    value: Union[T, NotGiven] = field(default_factory=lambda: NOT_GIVEN)
    comment: Optional[str] = field(default_factory=lambda: None)

    def comment_only(self):
        return self.value is NOT_GIVEN

    def has_comment(self):
        return bool(self.comment)

    def value_or(self, fallback: S) -> Union[T, S]:
        return fallback if self.value is NOT_GIVEN else self.value

    def add_to_container(self, container: "Container", field: str):
        container[field] = self.value_or("")
        if self.has_comment():
            cast("Item", container[field]).comment(cast(str, self.comment))


class CommentedList(Generic[T], UserList):
    def __init__(self, data: List[Commented[List[T]]]):
        super().__init__(data)

    def add_to_container(self, container: "Container", field: str):
        out = array()
        multiline = len(self) > 1
        out.multiline(multiline)

        for item in self.data:
            values = item.value_or([])
            for value in values:
                out.append(value)
            if not item.has_comment():
                continue
            if not multiline:
                container[field] = out
                out.comment(item.comment)
                return
            if len(values) > 0:
                _add_comment_array_last_item(out, item.comment)
            else:
                _add_comment_array_entire_line(out, item.comment)

        container[field] = out


class CommentedKV(Generic[T], UserList):
    def __init__(self, data: List[Commented[List[KV[T]]]]):
        super().__init__(data)

    def add_to_container(self, container: "Container", field: str):
        multiline = len(self) > 1
        out: Union[Table, InlineTable] = table() if multiline else inline_table()

        for item in self.data:
            values = (v for v in item.value_or([cast(KV, ())]) if v)
            k: Optional[str] = None
            for value in values:
                k, v = value
                out[k] = v
            if not item.has_comment():
                continue
            if not multiline:
                container[field] = out
                out.comment(item.comment)
                return
            if k:
                out[k].comment(item.comment)
            else:
                out.append(None, comment(item.comment))

        container[field] = out


# ---- High level function ----


def apply(container: C, field: str, fn: Transformation) -> C:
    """Modify the TOML container by applying the transformation ``fn`` to the value
    stored under the ``field`` key.
    """
    x = fn(str(container[field]))
    if hasattr(x, "add_to_container"):
        x.add_to_container(container, field)
    else:
        container[field] = x
    return container


# ---- Value processors ----


def noop(x: T) -> T:
    return x


def coerce_bool(value: str) -> bool:
    value = value.lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off", "none", "null", "nil"):
        return False
    raise ValueError(f"{value!r} cannot be converted to boolean")


@overload
def split_comment(value: str, *, comment_prefixes=CP) -> Commented[str]:
    ...


@overload
def split_comment(
    value: str, coerce_fn: CoerceFn[T], comment_prefixes=CP
) -> Commented[T]:
    ...


def split_comment(value, coerce_fn=noop, comment_prefixes=CP):
    value = value.strip()
    prefixes = [p for p in comment_prefixes if p in value]

    # We just process inline comments for single line options
    if not prefixes or len(value.splitlines()) > 1:
        return Commented(coerce_fn(value))

    if any(value.startswith(p) for p in comment_prefixes):
        return Commented(NOT_GIVEN, _strip_comment(value, comment_prefixes))

    prefix = prefixes[0]  # We can only analyse one...
    value, cmt = _split_in_2(value, prefix)
    return Commented(coerce_fn(value.strip()), _strip_comment(cmt, comment_prefixes))


@overload
def split_list(
    value: str, sep: str = ",", *, subsplit_dangling=True, comment_prefixes=CP
) -> CommentedList[str]:
    ...


@overload
def split_list(
    value: str,
    sep: str = ",",
    *,
    coerce_fn: CoerceFn[T],
    subsplit_dangling=True,
    comment_prefixes=CP,
) -> CommentedList[T]:
    ...


@overload
def split_list(
    value: str,
    sep: str,
    coerce_fn: CoerceFn[T],
    subsplit_dangling=True,
    comment_prefixes=CP,
) -> CommentedList[T]:
    ...


def split_list(
    value, sep=",", coerce_fn=noop, subsplit_dangling=True, comment_prefixes=CP
):
    """Value encoded as a (potentially) dangling list values separated by ``sep``.

    This function will first try to split the value by lines (dangling list) using
    :func:`str.splitlines`. Then, if ``subsplit_dangling=True``, it will split each line
    using ``sep``. As a result a list of items is obtained.
    For each item in this list ``coerce_fn`` is applied.
    """
    comment_prefixes = comment_prefixes.replace(sep, "")

    values = value.strip().splitlines()
    if not subsplit_dangling and len(values) > 0:
        sep += "\n"  # force a pattern that cannot be found in a split line

    def _split(line: str) -> list:
        return [coerce_fn(v.strip()) for v in line.split(sep) if v]

    return CommentedList([split_comment(v, _split, comment_prefixes) for v in values])


@overload
def split_kv_pairs(
    value: str,
    key_sep: str = "=",
    *,
    pair_sep=",",
    subsplit_dangling=True,
    comment_prefixes=CP,
) -> CommentedKV[str]:
    ...


@overload
def split_kv_pairs(
    value: str,
    key_sep: str = "=",
    *,
    coerce_fn: CoerceFn[T],
    pair_sep=",",
    subsplit_dangling=True,
    comment_prefixes=CP,
) -> CommentedKV[T]:
    ...


@overload
def split_kv_pairs(
    value: str,
    key_sep: str,
    coerce_fn: CoerceFn[T],
    pair_sep=",",
    subsplit_dangling=True,
    comment_prefixes=CP,
) -> CommentedKV[T]:
    ...


def split_kv_pairs(
    value,
    key_sep="=",
    coerce_fn=noop,
    pair_sep=",",
    subsplit_dangling=True,
    comment_prefixes=CP,
):
    """Value encoded as a (potentially) dangling list of key-value pairs.

    This function will first try to split the value by lines (dangling list) using
    :func:`str.splitlines`. Then, if ``subsplit_dangling=True``, it will split each line
    using ``pair_sep``. As a result a list of key-value pairs is obtained.
    For each item in this list, the key is separated from the value by ``key_sep``.
    ``coerce_fn`` is used to convert the value in each pair.
    """
    comment_prefixes = comment_prefixes.replace(key_sep, "")
    comment_prefixes = comment_prefixes.replace(pair_sep, "")

    values = value.strip().splitlines()
    if not subsplit_dangling and len(values) > 0:
        pair_sep += "\n"  # force a pattern that cannot be found in a split line

    def _split_kv(line: str) -> List[KV]:
        pairs = (
            item.split(key_sep, maxsplit=1)
            for item in line.strip().split(pair_sep)
            if key_sep in item
        )
        return [(k.strip(), coerce_fn(v.strip())) for k, v in pairs]

    return CommentedKV([split_comment(v, _split_kv, comment_prefixes) for v in values])


# ---- Private Helpers ----


def _split_in_2(v: str, sep: str) -> Tuple[str, Optional[str]]:
    items = iter(v.split(sep, maxsplit=1))
    first = next(items)
    second = next(items, None)
    return first, second


def _strip_comment(msg: Optional[str], prefixes: str = CP) -> Optional[str]:
    if not msg:
        return None
    return msg.strip().lstrip(prefixes).strip()


def _add_comment_array_last_item(toml_array: Array, cmt: str):
    # Workaround for bug in tomlkit, it should be: toml_array[-1].comment(cmt)
    # TODO: Remove when tomlkit fixes it
    last = toml_array[-1]
    last.comment(cmt)
    trivia = last.trivia
    # begin workaround -->
    _before_patch = last.as_string
    last.as_string = lambda: _before_patch() + "," + trivia.comment_ws + trivia.comment


def _add_comment_array_entire_line(toml_array: Array, cmt_msg: str):
    # Workaround for bug in tomlkit, it should be: toml_array.append(comment(cmt))
    # TODO: Remove when tomlkit fixes it
    cmt = comment(cmt_msg)
    cmt.trivia.trail = ""
    cmt.__dict__["value"] = cmt.as_string()
    toml_array.append(cmt)
