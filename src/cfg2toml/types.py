import sys
from collections import UserList
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, List, Optional, Tuple, TypeVar, Union

from configupdater import ConfigUpdater

from .toml_adapter import TOMLDocument

if sys.version_info <= (3, 8):  # pragma: no cover
    # TODO: Import directly (no need for conditional) when `python_requires = >= 3.8`
    from typing_extensions import Protocol
else:  # pragma: no cover
    from typing import Protocol


T = TypeVar("T")
S = TypeVar("S")
M = TypeVar("M", bound=MutableMapping)

TextProcessor = Callable[[str], str]

# Specific, using ConfigUpdater and TOMLDocument objects
CFGProcessor_ = Callable[[ConfigUpdater], ConfigUpdater]
TOMLProcessor_ = Callable[[ConfigUpdater, TOMLDocument], TOMLDocument]

# Generic, using MutableMapping
CFGProcessorM = Callable[[M], M]
TOMLProcessorM = Callable[[Mapping, M], M]

CFGProcessor = Union[CFGProcessor_, CFGProcessorM]
TOMLProcessor = Union[TOMLProcessor_, TOMLProcessorM]


class Profile(Protocol):
    pre_processors: List[TextProcessor]
    cfg_processors: List[CFGProcessor]
    toml_processors: List[TOMLProcessor]
    post_processors: List[TextProcessor]
    cfg_parser_opts: dict
    toml_template: str


class Translator(Protocol):
    def __getitem__(self, profile_name: str) -> Profile:
        ...


Extension = Callable[[Translator], None]


# ---- Transformations and Intermediate representations ----


KV = Tuple[str, T]
Scalar = Union[int, float, bool, str]  # TODO: missing time and datetime
CoerceFn = Callable[[str], T]
Transformation = Union[Callable[[str], Any], Callable[[M], M]]

NotGiven = Enum("NotGiven", "NOT_GIVEN")
NOT_GIVEN = NotGiven.NOT_GIVEN

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


class CommentedKV(Generic[T], UserList):
    def __init__(self, data: List[Commented[List[KV[T]]]]):
        super().__init__(data)
        self.comment: Optional[str] = None  # TODO: remove this workaround
