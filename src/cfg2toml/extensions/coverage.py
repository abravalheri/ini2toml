# based on https://coverage.readthedocs.io/en/coverage-5.5/config.html
from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import Sequence, TypeVar

from ..processing import apply, coerce_scalar, split_list
from ..translator import Translator

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


def activate(translator: Translator):
    profile = translator[".coveragerc"]
    profile.post_processors.append(partial(process_values, AFFECTED_SECTIONS))

    prefixed_sections = [f"{PREFIX}{s}" for s in AFFECTED_SECTIONS]
    for file in ("setup.cfg", "tox.ini"):
        profile = translator[file]
        profile.post_processors.append(partial(process_values, prefixed_sections))


def process_values(sections: Sequence[str], _orig: Mapping, doc: M) -> M:
    for section in sections:
        raw_section = section.replace(PREFIX.rstrip(":."), "").lstrip(":.")
        sec = doc.get("tool", {}).get("coverage", {}).pop(raw_section, {})
        sec = doc.pop(section, doc.get("tool", {}).pop(section, sec))
        for field in sec:
            if field in LIST_VALUES:
                apply(sec, field, split_list)
            else:
                apply(sec, field, coerce_scalar)

        if sec:
            name = section[len("coverage:") :] if "coverage:" in section else section
            doc.setdefault("tool", {}).setdefault("coverage", {})[name] = sec
    return doc
