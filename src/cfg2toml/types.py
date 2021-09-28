import sys
from collections.abc import Mapping, MutableMapping
from typing import Callable, List, TypeVar, Union

from configupdater import ConfigUpdater

from .toml_adapter import TOMLDocument

if sys.version_info <= (3, 8):  # pragma: no cover
    # TODO: Import directly (no need for conditional) when `python_requires = >= 3.8`
    from typing_extensions import Protocol
else:  # pragma: no cover
    from typing import Protocol


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
