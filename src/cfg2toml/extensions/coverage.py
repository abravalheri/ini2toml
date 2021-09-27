# based on https://coverage.readthedocs.io/en/coverage-5.5/config.html
from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import Any, Sequence, TypeVar

from ..processing import (
    apply,
    create_item,
    is_false,
    is_true,
    split_comment,
    split_list,
)
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
        sec = doc.pop(section, doc.get("tool", {}).pop(section, {}))
        for field, value in sec.items():
            if field in LIST_VALUES:
                apply(sec, field, split_list)
                continue
            obj = split_comment(value)
            value_str = obj.value_or("").strip()
            if value_str.isdecimal():
                v: Any = int(value_str)
            elif is_true(value_str):
                v = True
            elif is_false(value_str):
                v = False
            else:
                v = value_str
            sec[field] = create_item(v, obj.comment)

        if sec:
            name = section[len("coverage:") :] if "coverage:" in section else section
            doc.setdefault("tool", {}).setdefault("coverage", {})[name] = sec
    return doc
