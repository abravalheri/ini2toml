"""Reusable post-processing and type casting operations"""
from collections import UserList
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, List, Optional, Tuple, TypeVar, overload

CP = "#;"
"""Default Comment Prefixes"""

T = TypeVar("T")
KV = Tuple[str, T]
CoerceFn = Callable[[str], T]
Transformation = Callable[[str], Any]


@dataclass
class Commented(Generic[T]):
    value: Optional[T] = field(default_factory=lambda: None)
    comment: Optional[str] = field(default_factory=lambda: None)


class CommentedList(Generic[T], UserList):
    def __init__(self, data: List[Commented[List[T]]]):
        super().__init__(data)


class CommentedKV(Generic[T], UserList):
    def __init__(self, data: List[Commented[List[KV[T]]]]):
        super().__init__(data)


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

    if value.startswith(comment_prefixes):
        return Commented(None, _strip_comment(value, comment_prefixes))

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
