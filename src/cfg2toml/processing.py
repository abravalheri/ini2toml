"""Reusable post-processing and type casting operations"""
import logging
from collections import UserList
from collections.abc import MutableMapping, Sequence
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

from tomlkit import array, comment, inline_table, item, table
from tomlkit.items import Array, InlineTable, Item, Table

NotGiven = Enum("NotGiven", "NOT_GIVEN")
NOT_GIVEN = NotGiven.NOT_GIVEN

CP = "#;"
"""Default Comment Prefixes"""

T = TypeVar("T")
S = TypeVar("S")
M = TypeVar("M", bound="MutableMapping")
KV = Tuple[str, T]
CoerceFn = Callable[[str], T]
Transformation = Union[Callable[[str], Any], Callable[[M], M]]

_logger = logging.getLogger(__name__)


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

    def as_toml_obj(self, default_value="") -> Item:
        obj = item(self.value_or(default_value))
        if self.comment is not None:
            obj.comment(self.comment)
        return obj


class CommentedList(Generic[T], UserList):
    def __init__(self, data: List[Commented[List[T]]]):
        super().__init__(data)
        self.comment: Optional[str] = None  # TODO: remove this workaround

    def as_toml_obj(self) -> Array:
        out = array()
        multiline = len(self) > 1
        out.multiline(multiline)

        for entry in self.data:
            values = entry.value_or([])
            for value in values:
                out.append(value)
            if not entry.has_comment():
                continue
            if not multiline:
                self.comment = entry.comment
                out.comment(entry.comment)
                return out
            if len(values) > 0:
                _add_comment_array_last_item(out, entry.comment)
            else:
                _add_comment_array_entire_line(out, entry.comment)

        return out


class CommentedKV(Generic[T], UserList):
    def __init__(self, data: List[Commented[List[KV[T]]]]):
        super().__init__(data)
        self.comment: Optional[str] = None  # TODO: remove this workaround

    def as_toml_obj(self) -> Union[Table, InlineTable]:
        multiline = len(self) > 1
        out: Union[Table, InlineTable] = table() if multiline else inline_table()

        for entry in self.data:
            values = (v for v in entry.value_or([cast(KV, ())]) if v)
            k: Optional[str] = None
            for value in values:
                k, v = value
                out[k] = v  # type: ignore
            if not entry.has_comment():
                continue
            if not multiline:
                out.comment(entry.comment)  # type: ignore
                self.comment = entry.comment
                return out
            if k:
                out[k].comment(entry.comment)
            else:
                out.append(None, comment(entry.comment))  # type: ignore
        return out


# ---- High level function ----


def apply(container: M, field: str, fn: Transformation) -> M:
    """Modify the TOML container by applying the transformation ``fn`` to the value
    stored under the ``field`` key.
    """
    value = container[field]
    try:
        processed = fn(value)
    except Exception:
        msg = f"Impossible to transform: {value} <{value.__class__.__name__}>"
        _logger.warning(msg)
        _logger.debug("Please check the following details", exc_info=True)
        return container
    return _add_to_container(container, field, processed)


def apply_nested(container: M, path: Sequence, fn: Transformation) -> M:
    *parent, last = path
    nested = get_nested(container, parent, None)
    if not nested:
        return container
    if not isinstance(nested, MutableMapping):
        msg = f"Cannot apply transformations to {nested} ({nested.__class__.__name__})"
        raise ValueError(msg)
    if last in nested:
        apply(nested, last, fn)
    return container


def apply_group(container: M, path: Sequence, fn: Transformation) -> M:
    """Similar to apply_nested, but apply ``fn`` to all the elements of a group"""
    group = get_nested(container, path, None)
    if isinstance(group, MutableMapping):
        for key in list(group.keys()):
            apply(group, key, fn)
    elif isinstance(group, Sequence):
        values = [v.as_toml_obj() if hasattr(v, "as_toml_obj") else v for v in group]
        set_nested(container, path, values)
    elif group:
        msg = f"Cannot apply transformations to {group} ({group.__class__.__name__})"
        raise ValueError(msg)
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
    if not isinstance(value, str):
        return value
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
    if not isinstance(value, str):
        return value
    comment_prefixes = comment_prefixes.replace(sep, "")

    values = value.strip().splitlines()
    if not subsplit_dangling and len(values) > 1:
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
    if not subsplit_dangling and len(values) > 1:
        pair_sep += "\n"  # force a pattern that cannot be found in a split line

    def _split_kv(line: str) -> List[KV]:
        pairs = (
            item.split(key_sep, maxsplit=1)
            for item in line.strip().split(pair_sep)
            if key_sep in item
        )
        return [(k.strip(), coerce_fn(v.strip())) for k, v in pairs]

    return CommentedKV([split_comment(v, _split_kv, comment_prefixes) for v in values])


# ---- Access Helpers ----


def get_nested(m, keys, default=None):
    """Nested version of Mapping.get"""
    value = m
    for k in keys:
        try:
            value = value[k]
        except (KeyError, IndexError):
            return default
    return value


def pop_nested(m, keys, default=None):
    """Nested version of Mapping.get"""
    *path, last = keys
    parent = get_nested(m, path, NOT_GIVEN)
    if parent is NOT_GIVEN:
        return default
    if isinstance(parent, MutableMapping):
        return parent.pop(last, default)
    if len(parent) > last:
        return parent.pop(last)
    return default


def set_nested(m, keys, value):
    last = keys[-1]
    parent = [] if isinstance(last, int) else {}
    parent = setdefault(m, keys[:-1], parent)
    parent = get_nested(m, keys[:-1], parent)
    try:
        parent[last] = value
    except IndexError:
        parent.append(value)
    if hasattr(value, "display_name"):
        # Temporary workaround for tomlkit#144 and atoml#24
        j = next((i for i, k in enumerate(keys) if isinstance(k, int)), 0)
        value.display_name = ".".join(keys[j:])
    return m


def setdefault(m, keys, default=None):
    """Nested version of MutableMapping.get"""
    if len(keys) < 1:
        return m
    if len(keys) == 1:
        return _setdefault(m, keys[0], default)
    value = m
    for (k, nxt) in zip(keys[:-1], keys[1:]):
        value = _setdefault(value, k, [] if isinstance(nxt, int) else {})
    return _setdefault(value, nxt, default)


# ---- Private Helpers ----


def _setdefault(container, key, default):
    # Also "works" for lists
    if hasattr(container, "setdefault"):
        return container.setdefault(key, default)
    try:
        return container[key]
    except IndexError:
        container.append(default)
    return default


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


def _add_to_container(container: M, field: str, value: Any) -> M:
    # Add a value to a TOML container
    if not hasattr(value, "as_toml_obj"):
        container[field] = value
        return container

    obj: Item = value.as_toml_obj()
    container[field] = obj
    if (
        hasattr(value, "comment")
        and value.comment is not None
        and hasattr(obj, "comment")
    ):
        # BUG: we should not need to repeat the comment
        obj.comment(value.comment)
    return container
