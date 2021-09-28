# https://mypy.readthedocs.io/en/stable/config_file.html
from collections.abc import Mapping, MutableMapping, MutableSequence
from functools import partial
from typing import List, TypeVar, cast

from ..processing import apply, coerce_scalar, split_list
from ..toml_adapter import aot
from ..translator import Translator

M = TypeVar("M", bound=MutableMapping)

LIST_VALUES = (
    "files",
    "always_false",
    "disable_error_code",
    "plugins",
)
DONT_TOUCH = ("python_version",)

list_comma = partial(split_list, sep=",")


def activate(translator: Translator):
    for file in ("setup.cfg", "mypy.ini", ".mypy.ini"):
        profile = translator[file]
        profile.toml_processors.append(process_values)


def process_values(orig: Mapping, doc: M) -> M:
    for section in [*doc, *doc.get("tool", {})]:
        if section.startswith("mypy-"):
            doc = process_overrides_section(orig, doc, section)
        elif section == "mypy":
            doc = process_section(orig, doc, section)
    return doc


def process_section(_orig: Mapping, doc: M, section_name: str) -> M:
    sec = doc.pop(section_name, doc.get("tool", {}).pop(section_name, {}))
    sec = process_options(sec)
    if not sec:
        return doc
    doc.setdefault("tool", {})["mypy"] = sec
    return doc


def process_overrides_section(_orig: Mapping, doc: M, section_name: str) -> M:
    modules = [n.replace("mypy-", "") for n in section_name.split(",")]
    sec = doc.pop(section_name, doc.get("tool", {}).pop(section_name, {}))
    sec = process_options(sec)
    sec = add_overrides_modules(sec, modules)
    if not sec:
        return doc
    mypy = doc.setdefault("tool", {}).setdefault("mypy", {})
    mypy.setdefault("overrides", create_overrides()).append(sec)
    return doc


def process_options(sec: M) -> M:
    for field in sec:
        if field in DONT_TOUCH:
            continue
        elif field in LIST_VALUES:
            apply(sec, field, split_list)
        else:
            apply(sec, field, coerce_scalar)
    return sec


def create_overrides() -> MutableSequence:
    return cast(MutableSequence, aot())


def add_overrides_modules(section: M, modules: List[str]) -> M:
    section["module"] = modules  # TODO: anyway of making this the first field?
    return section
