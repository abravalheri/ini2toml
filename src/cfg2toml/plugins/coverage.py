# based on https://coverage.readthedocs.io/en/stable/config.html
from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import Optional, Sequence, TypeVar

from ..processing import Transformer, coerce_scalar, split_list
from ..types import Profile, Translator

M = TypeVar("M", bound=MutableMapping)

PREFIX = "coverage:"
AFFECTED_SECTIONS = ("run", "paths", "report", "html", "xml", "json")
LIST_VALUES = (
    "exclude_lines",
    "concurrency",
    "disable_warnings",
    "debug",
    "include",
    "omit",
    "plugins",
    "source",
    "source_pkgs",
    "partial_branches",
)


def activate(translator: Translator, transformer: Optional[Transformer] = None):
    plugin = Coverage(transformer or Transformer())
    profile = translator[".coveragerc"]
    plugin.attach_to(profile, prefix="")
    profile.help_text = plugin.__doc__ or ""

    for file in ("setup.cfg", "tox.ini"):
        plugin.attach_to(translator[file], prefix=PREFIX)


class Coverage:
    """Convert settings to 'pyproject.toml' equivalent"""

    def __init__(self, transformer: Transformer):
        self._tr = transformer

    def attach_to(self, profile: Profile, prefix=PREFIX):
        fn = partial(self.process_values, AFFECTED_SECTIONS, prefix)
        profile.toml_processors.append(fn)

    def process_values(
        self, sections: Sequence[str], prefix: str, _orig: Mapping, doc: M
    ) -> M:
        for section in sections:
            prefixed = f"{prefix}{section}"
            sec = doc.get("tool", {}).get("coverage", {}).pop(section, {})
            sec = doc.pop(section, doc.get("tool", {}).pop(prefixed, sec))
            for field in sec:
                if field in LIST_VALUES:
                    self._tr.apply(sec, field, split_list)
                else:
                    self._tr.apply(sec, field, coerce_scalar)

            if sec:
                doc.setdefault("tool", {}).setdefault("coverage", {})[section] = sec
        return doc
