import sys
from pprint import pformat
from itertools import chain
from collections import UserList
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
from textwrap import indent
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    Dict,
    Sequence,
    Mapping,
    cast,
)

from configupdater import ConfigUpdater

if sys.version_info <= (3, 8):  # pragma: no cover
    # TODO: Import directly (no need for conditional) when `python_requires = >= 3.8`
    from typing_extensions import Protocol
else:  # pragma: no cover
    from typing import Protocol


T = TypeVar("T")
S = TypeVar("S")
M = TypeVar("M", bound=MutableMapping)
I = TypeVar("I", bound="IntermediateRepr")

TextProcessor = Callable[[str], str]
IntermediateProcessor = Callable[["IntermediateRepr"], "IntermediateRepr"]

EMPTY: Mapping = MappingProxyType({})


class CLIChoice(Protocol):
    name: str
    help_text: str


class Profile(Protocol):
    name: str
    help_text: str
    pre_processors: List[TextProcessor]
    intermediate_processors: List[IntermediateProcessor]
    post_processors: List[TextProcessor]


class ProfileAugmentation(Protocol):
    active_by_default: bool
    name: str
    help_text: str

    def fn(self, profile: Profile):
        ...

    def is_active(self, explicitly_active: Optional[bool] = None) -> bool:
        """``explicitly_active`` is a tree-state variable: ``True`` if the user
        explicitly asked for the augmentation, ``False`` if the user explicitly denied
        the augmentation, or ``None`` otherwise.
        """


class Translator(Protocol):
    def __getitem__(self, profile_name: str) -> Profile:
        """Create and register (and return) a translation :class:`Profile`
        (or return a previously registered one) (see :ref:`core-concepts`).
        """

    def augment_profiles(
        self,
        fn: "ProfileAugmentationFn",
        active_by_default: bool = False,
        name: str = "",
        help_text: str = "",
    ):
        """Register a profile augmentation function (see :ref:`core-concepts`).
        The keyword ``name`` and ``help_text`` can be used to customise the description
        featured in ``ini2toml``'s CLI, but when these arguments are not given (or empty
        strings), ``name`` is taken from ``fn.__name__`` and ``help_text`` is taken from
        ``fn.__doc__`` (docstring).
        """


Plugin = Callable[[Translator], None]
ProfileAugmentationFn = Callable[[Profile], None]


# ---- Transformations and Intermediate representations ----


KV = Tuple[str, T]
Scalar = Union[int, float, bool, str]  # TODO: missing time and datetime
CoerceFn = Callable[[str], T]
Transformation = Union[Callable[[str], Any], Callable[[M], M]]

NotGiven = Enum("NotGiven", "NOT_GIVEN")
NOT_GIVEN = NotGiven.NOT_GIVEN


@dataclass(frozen=True)
class _Key:
    _value: int = field(default_factory=lambda: uuid4().int)

    def __str__(self):
        return f"{self.__class__.__name__}()"

    __repr__ = __str__


class WhitespaceKey(_Key):
    pass


class CommentKey(_Key):
    pass


Key = Union[str, _Key, Tuple[Union[str, _Key], ...]]


class IntermediateRepr(MutableMapping):
    def __init__(
        self,
        elements: Mapping[Key, Any] = EMPTY,
        order: Sequence[Key] = (),
        inline_comment: str = "",
        **kwargs,
    ):
        el = chain(elements.items(), kwargs.items())
        self.elements: Dict[Key, Any] = {}
        self.order: List[Key] = []
        self.inline_comment = inline_comment
        self.elements.update(el)
        self.order.extend(order or self.elements.keys())
        elem_not_in_order = any(k not in self.order for k in self.elements)
        order_not_in_elem = any(k not in self.elements for k in self.order)
        if elem_not_in_order or order_not_in_elem:
            raise ValueError(f"{order} and {elements} need to have the same keys")

    def __repr__(self):
        inner = ",\n".join(
            indent(f"{k}={pformat(getattr(self, k))}", "    ")
            for k in ("elements", "order", "inline_comment")
        )
        return f"{self.__class__.__name__}(\n{inner}\n)"

    def __eq__(self, other):
        L = len(self)
        if not(
            isinstance(other, self.__class__)
            and self.inline_comment == other.inline_comment
            and len(other) == L
        ):
            return False
        self_ = [(str(k), v) for k, v in self.items()]
        other_ = [(str(k), v) for k, v in other.items()]
        return all(self_[i] == other_[i] for i in range(L))

    def rename(self, old_key: Key, new_key: Key, ignore_missing=False):
        if old_key == new_key:
            return self
        if new_key in self.order:
            raise ValueError(f"{new_key=} already exists")
        if old_key not in self.order and ignore_missing:
            return self
        i = self.order.index(old_key)
        self.order[i] = new_key
        self.elements[new_key] = self.elements.pop(old_key)
        return self

    def insert(self, i, key: Key, value: Any):
        if key in self.order:
            raise ValueError(f"{key=} already exists")
        self.order.insert(i, key)
        self.elements[key] = value

    def index(self, key: Key) -> int:
        return self.order.index(key)

    def append(self, key: Key, value: Any):
        self.insert(len(self.order), key, value)

    def copy(self: I) -> I:
        return self.__class__(self.elements.copy(), self.order[:], self.inline_comment)

    def replace_first_remove_others(
        self, existing_keys: Sequence[Key], new_key: Key, value: Any
    ):
        idx = [self.index(k) for k in existing_keys if k in self]
        if not idx:
            i = len(self)
        else:
            i = sorted(idx)[0]
            for key in existing_keys:
                self.pop(key, None)
        self.insert(i, new_key, value)
        return i

    def __getitem__(self, key: Key):
        return self.elements[key]

    def __setitem__(self, key: Key, value: Any):
        if key not in self.elements:
            self.order.append(key)
        self.elements[key] = value

    def __delitem__(self, key: Key):
        del self.elements[key]
        self.order.remove(key)

    def __iter__(self):
        return iter(self.order)

    def __len__(self):
        return len(self.order)


# These objects hold information about the processed values + comments
# in such a way that we can later convert them to TOML while still preserving
# the comments (if we want to).


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


class CommentedList(Generic[T], UserList):
    def __init__(self, data: List[Commented[List[T]]]):
        super().__init__(data)
        self.comment: Optional[str] = None  # TODO: remove this workaround

    def as_list(self) -> list:
        out = []
        for entry in self:
            values = entry.value_or([])
            for value in values:
                out.append(value)
        return out


class CommentedKV(Generic[T], UserList):
    def __init__(self, data: List[Commented[List[KV[T]]]]):
        super().__init__(data)
        self.comment: Optional[str] = None  # TODO: remove this workaround

    def find(self, key: str) -> Optional[Tuple[int, int]]:
        for i, row in enumerate(self):
            for j, item in enumerate(row.value_or([])):
                if item[0] == key:
                    return (i, j)
        return None

    def pop_key(self, key: str) -> Optional[T]:
        idx = self.find(key)
        if idx is None:
            return None
        i, j = idx
        row = self[i]
        value = row.value_or([])[j]
        del row[j]
        return value[1]

    def as_dict(self) -> dict:
        out = {}
        for entry in self:
            values = (v for v in entry.value_or([cast(KV, ())]) if v)
            for k, v in values:
                out[k] = v
        return out
