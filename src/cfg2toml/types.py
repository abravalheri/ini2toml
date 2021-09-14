import sys
from typing import Callable, List

from configupdater import ConfigUpdater
from tomlkit.toml_document import TOMLDocument

if sys.version_info <= (3, 8):  # pragma: no cover
    # TODO: Import directly (no need for conditional) when `python_requires = >= 3.8`
    from typing_extensions import Protocol
else:  # pragma: no cover
    from typing import Protocol


PreProcessor = Callable[[ConfigUpdater], ConfigUpdater]
PostProcessor = Callable[[ConfigUpdater, TOMLDocument], TOMLDocument]


class Profile(Protocol):
    pre_processors: List[PreProcessor]
    post_processors: List[PostProcessor]
    cfg_parser_opts: dict


class Translator(Protocol):
    def __getitem__(self, profile_name: str) -> Profile:
        ...


Extension = Callable[[Translator], None]
