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
from tomlkit.items import Item

LONG_VALUE = 60

# ---- Useful types ----

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
        container[field] = out

        for item in self.data:
            values = item.value_or([])
            for value in values:
                out.append(value)
            if not item.has_comment():
                continue
            if not multiline:
                cast("Item", out).comment(item.comment)
                continue
            # TODO: tomlkit have problems to add comments to Array items
            if len(values) > 0:
                last = out[-1]
                last.comment(item.comment)
                # this is the workaround:
                _before_patch = last.as_string

                def _workaroud():
                    trivia = last.trivia
                    return _before_patch() + "," + trivia.comment_ws + trivia.comment

                last.as_string = _workaroud
            else:
                cmt = comment(item.comment)
                cmt.trivia.trail = ""  # workaround
                cmt.__dict__["value"] = cmt.as_string()  # workaround
                out.append(cmt)


class CommentedKV(Generic[T], UserList):
    def __init__(self, data: List[Commented[List[KV[T]]]]):
        super().__init__(data)

    def add_to_container(self, container: "Container", field: str):
        multiline = len(self) > 1
        out = table() if multiline else inline_table()
        container[field] = out

        for item in self.data:
            values = item.value_or([cast(KV, ())])
            k: Optional[str] = None
            for value in values:
                if value:
                    k, v = value
                    out.append(k, v)  # type: ignore
            if multiline and k:
                out[k].comment(item.comment)
            else:
                cast("Item", out).comment(item.comment)


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
    value: str, sep: str = ",", *, comment_prefixes=CP
) -> CommentedList[str]:
    ...


@overload
def split_list(
    value: str, sep: str = ",", *, coerce_fn: CoerceFn[T], comment_prefixes=CP
) -> CommentedList[T]:
    ...


@overload
def split_list(
    value: str, sep: str, coerce_fn: CoerceFn[T], comment_prefixes=CP
) -> CommentedList[T]:
    ...


def split_list(value, sep=",", coerce_fn=noop, comment_prefixes=CP):
    """Value encoded as a (potentially) dangling list values separated by ``sep``"""
    comment_prefixes = comment_prefixes.replace(sep, "")

    def _split(line: str) -> list:
        return [coerce_fn(v.strip()) for v in line.split(sep)]

    values = value.strip().splitlines()
    return CommentedList([split_comment(v, _split, comment_prefixes) for v in values])


@overload
def split_kv_pairs(
    value: str, sep: str = "=", *, item_sep=",", comment_prefixes=CP
) -> CommentedKV[str]:
    ...


@overload
def split_kv_pairs(
    value: str,
    sep: str = "=",
    *,
    coerce_fn: CoerceFn[T],
    item_sep=",",
    comment_prefixes=CP,
) -> CommentedKV[T]:
    ...


@overload
def split_kv_pairs(
    value: str, sep: str, coerce_fn: CoerceFn[T], item_sep=",", comment_prefixes=CP
) -> CommentedKV[T]:
    ...


def split_kv_pairs(value, sep="=", coerce_fn=noop, item_sep=",", comment_prefixes=CP):
    """Value encoded as a (potentially) dangling list of key-value pairs.
    The key is separated from the values by ``sep``, and each key-value is separated
    from each other by ``item_sep`` or a new line.
    """
    comment_prefixes = comment_prefixes.replace(sep, "")
    comment_prefixes = comment_prefixes.replace(item_sep, "")

    def _split_kv(line: str) -> List[KV]:
        pairs = (item.split(sep) for item in line.strip().split(item_sep))
        return [(k.strip(), coerce_fn(v.strip())) for k, v in pairs]

    values = value.strip().splitlines()
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
