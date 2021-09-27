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

# Specific, using ConfigUpdater and TOMLDocument objects
PreProcessorCFG = Callable[[ConfigUpdater], ConfigUpdater]
PostProcessorTOML = Callable[[ConfigUpdater, TOMLDocument], TOMLDocument]

# Generic, using MutableMapping
PreProcessorM = Callable[[M], M]
PostProcessorM = Callable[[Mapping, M], M]

PreProcessor = Union[PreProcessorCFG, PreProcessorM]
PostProcessor = Union[PostProcessorTOML, PostProcessorM]


class Profile(Protocol):
    pre_processors: List[PreProcessor]
    post_processors: List[PostProcessor]
    cfg_parser_opts: dict
    toml_template: str


class Translator(Protocol):
    def __getitem__(self, profile_name: str) -> Profile:
        ...


Extension = Callable[[Translator], None]
