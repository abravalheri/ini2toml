"""Reusable post-processing and type casting operations"""
import logging
from collections.abc import MutableMapping, Sequence
from functools import singledispatch
from typing import Any, Callable, List, Optional, Tuple, TypeVar, Union, cast, overload

from .access import get_nested
from .toml_adapter import (
    Array,
    InlineTable,
    Item,
    Table,
    array,
    comment,
    inline_table,
    item,
    table,
)
from .types import NOT_GIVEN, Commented, CommentedKV, CommentedList

CP = "#;"
"""Default Comment Prefixes"""

T = TypeVar("T")
S = TypeVar("S")
M = TypeVar("M", bound="MutableMapping")
KV = Tuple[str, T]
Scalar = Union[int, float, bool, str]  # TODO: missing time and datetime
CoerceFn = Callable[[str], T]
Transformation = Union[Callable[[str], Any], Callable[[M], M]]

_logger = logging.getLogger(__name__)


# ---- "Appliers" ----
# These functions are able to use transformations to modify the TOML object
# Internally, they know how to convert intermediate representations (Commented,
# CommentedKV, CommentedList, ...) into TOML values.


def collapse(obj):
    """Convert ``obj`` as a result of a transformation function -
    that can be a built-in value (such as ``int``, ``bool``, etc) or an internal value
    representation that preserves comments (``Commented``, ``CommentedList``,
    ``CommentedKV``) - into a value that can be directly added to a container serving as
    basis for the TOML document.
    """
    return _collapse(obj)


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


# ---- Simple value processors ----
# These functions return plain objects, that can be directly added to the TOML document


def noop(x: T) -> T:
    return x


def is_true(value: str) -> bool:
    value = value.lower()
    return value in ("true", "1", "yes", "on")


def is_false(value: str) -> bool:
    value = value.lower()
    return value in ("false", "0", "no", "off", "none", "null", "nil")


def is_float(value: str) -> bool:
    cleaned = value.lower().lstrip("+-").replace(".", "").replace("_", "")
    return cleaned.isdecimal() and value.count(".") <= 1 or cleaned in ("inf", "nan")


def coerce_bool(value: str) -> bool:
    if is_true(value):
        return True
    if is_false(value):
        return False
    raise ValueError(f"{value!r} cannot be converted to boolean")


def coerce_scalar(value: str) -> Scalar:
    value = value.strip()
    if value.isdecimal():
        return int(value)
    if is_float(value):
        return float(value)
    if is_true(value):
        return True
    elif is_false(value):
        return False
    # Do we need this? Or is there a better way? How about time objects
    # > try:
    # >     return datetime.fromisoformat(value)
    # > except ValueError:
    # >     pass
    return value


def kebab_case(field: str) -> str:
    return field.lower().replace("_", "-")


# ---- Complex value processors ----
# These functions return an intermediate representation of the value,
# that need `apply` to be added to a container


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


def split_scalar(value: str, *, comment_prefixes=CP) -> Commented[Scalar]:
    return split_comment(value, coerce_scalar, comment_prefixes)


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


# ---- Public Helpers ----


def create_item(value, comment):
    obj = item(value)
    if comment is not None:
        obj.comment(comment)
    return obj


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
    cast(list, toml_array).append(cmt)


def _add_to_container(container: M, field: str, value: Any) -> M:
    # Add a value to a TOML container
    obj = collapse(value)
    container[field] = obj
    if (
        hasattr(value, "comment")
        and isinstance(value.comment, str)
        and value.comment
        and hasattr(obj, "comment")
    ):
        # BUG: we should not need to repeat the comment
        obj.comment(value.comment)

    return container


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
    multiline = len(obj) > 1
    out.multiline(multiline)

    for entry in obj.data:
        values = entry.value_or([])
        for value in values:
            cast(list, out).append(value)
        if not entry.has_comment():
            continue
        if not multiline:
            obj.comment = entry.comment
            cast(Item, out).comment(entry.comment)
            return out
        if len(values) > 0:
            _add_comment_array_last_item(out, entry.comment)
        else:
            _add_comment_array_entire_line(out, entry.comment)

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
            out[k] = v  # type: ignore
        if not entry.has_comment():
            continue
        if not multiline:
            out.comment(entry.comment)  # type: ignore
            obj.comment = entry.comment
            return out
        if k:
            out[k].comment(entry.comment)
        else:
            out.append(None, comment(entry.comment))  # type: ignore
    return out
