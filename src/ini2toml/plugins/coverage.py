# based on https://coverage.readthedocs.io/en/stable/config.html
from collections.abc import MutableMapping
from functools import partial
from typing import TypeVar

from ..transformations import coerce_scalar, split_list
from ..types import Transformation as T
from ..types import Translator

M = TypeVar("M", bound=MutableMapping)


def activate(translator: Translator):
    plugin = Coverage()
    profile = translator[".coveragerc"]

    fn = partial(plugin.process_values, prefix="")
    profile.intermediate_processors.append(fn)
    profile.help_text = plugin.__doc__ or ""

    for file in ("setup.cfg", "tox.ini"):
        translator[file].intermediate_processors.append(plugin.process_values)


class Coverage:
    """Convert settings to 'pyproject.toml' equivalent"""

    PREFIX = "coverage:"
    SECTIONS = ("run", "paths", "report", "html", "xml", "json")
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

    def process_values(self, doc: M, sections=SECTIONS, prefix=PREFIX) -> M:
        for name in sections:
            candidates = [
                doc.get(f"{prefix}{name}"),
                doc.get("tool", {}).get("coverage", {}).get(name),
                doc.get(("tool", "coverage"), {}).get(name),
                doc.get(("tool", "coverage", name)),
            ]
            for section in candidates:
                if section:
                    self.process_section(section)
        return doc

    def process_section(self, section: M):
        for field in section:
            fn: T = split_list if field in self.LIST_VALUES else coerce_scalar
            section[field] = fn(section[field])
