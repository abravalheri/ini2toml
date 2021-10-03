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
    Whitespace,
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
"""Simple data types with TOML correspondence"""

CoerceFn = Callable[[str], T]
"""Functions that know how to parser/coerce string values into different types"""

Transformation = Union[Callable[[str], Any], Callable[[M], M]]
"""There are 2 main types of transformation:
- The first one is a simple transformation that processes a string value (coming from an
  option in the original CFG/INI file) into a value with an equivalent TOML data type.
  For example: transforming ``"2"`` (string) into ``2`` (integer).
- The second one tries to preserve metadata (such as comments) from the original CFG/INI
  file. This kind of transformation processes a string value into an intermediary
  representation (e.g. :obj:`Commented`, :obj:`CommentedList`, obj:`CommentedKV`)
  that needs to be properly handled before adding to the TOML document.

In a higher level we can also consider an ensemble of transformations that transform an
entire table of the TOML document.
"""

_logger = logging.getLogger(__name__)


class Transformer:
    """A transformer is an object that can :meth:`apply` a transformation to a TOML
    object representation modifying it in a way that the result is an equally valid TOML
    object representation.

    Since transformations can result in intermediary forms (such as :obj:`Commented`,
    :obj:`CommentedKV` and :obj:`CommentedList`) in addition to data types supported by
    TOML, :obj:`Transformer` objects know how to internally :meth:`collapse` these
    intermediary forms into valid objects.

    Despite not originally intended to hold any state, :obj:`Transformer` is implemented
    as a class to allow polymorphism, since Python does not offer other strategies like
    parametric modules.

    A nice aspect of this choice is that different transformers can re-use the same
    transformations but with different outcomes. For example, a first transformer can
    remove all comments coming from the CFG/INI file, while a second can turn them into
    TOML comments.
    """

    def apply(self, container: M, field: str, fn: Transformation) -> M:
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
        container[field] = self.collapse(processed)
        return container

    def apply_nested(self, container: M, path: Sequence, fn: Transformation) -> M:
        *parent, last = path
        nested = get_nested(container, parent, None)
        if not nested:
            return container
        if not isinstance(nested, MutableMapping):
            msg = "Cannot apply transformations to "
            raise ValueError(msg + f"{nested} ({nested.__class__.__name__})")
        if last in nested:
            self.apply(nested, last, fn)
        return container

    def collapse(self, obj):
        """Convert ``obj`` as a result of a transformation function -
        that can be a built-in value (such as ``int``, ``bool``, etc) or an internal
        value representation that preserves comments (``Commented``, ``CommentedList``,
        ``CommentedKV``) - into a value that can be directly added to a container
        serving as basis for the TOML document.
        """
        return _collapse(obj)


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
        values = out._value
        L = len(values)
        for i, v in enumerate(out._value):
            # Workaround to remove trailing space
            if (
                isinstance(v, Whitespace)
                and i + 1 < L
                and isinstance(values[i + 1], Whitespace)
                and "\n" in values[i + 1].s
            ):
                v._s = v._s.strip()

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


def _no_trail_comment(msg: str):
    cmt = comment(msg)
    cmt.trivia.trail = ""
    return cmt
