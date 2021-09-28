from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import Set, TypeVar

from ..processing import apply, coerce_scalar, kebab_case, split_list
from ..translator import Translator

M = TypeVar("M", bound=MutableMapping)


def activate(translator: Translator):
    profile = translator[".isort.cfg"]
    profile.toml_processors.append(partial(process_values, "settings"))
    for file in ("setup.cfg", "tox.ini"):
        profile = translator[file]
        profile.toml_processors.append(partial(process_values, "isort"))


def find_list_options(section: Mapping) -> Set[str]:
    # dicts = ["import_headings", "git_ignore", "know_other"]
    fields = {
        "force_to_top",
        "treat_comments_as_code",
        "no_lines_before",
        "forced_separate",
        "sections",
        "length_sort_sections",
        "sources",
        "constants",
        "classes",
        "variables",
        "namespace_packages",
        "add_imports",
        "remove_imports",
    }

    field_ends = ["skip", "glob", "paths", "exclusions", "extensions"]
    field_starts = ["known", "extra"]
    dynamic_fields = (
        field
        for field in section
        if any(field.startswith(s) for s in field_starts)
        or any(field.endswith(s) for s in field_ends)
    )
    fields = {*fields, *dynamic_fields}
    return {*fields, *map(kebab_case, fields)}


def process_values(section_name: str, _orig: Mapping, doc: M) -> M:
    isort = doc.pop(section_name, doc.get("tool", {}).pop(section_name, {}))
    list_options = find_list_options(isort)
    for field in isort:
        if field in list_options:
            apply(isort, field, split_list)
        else:
            apply(isort, field, coerce_scalar)

    if isort:
        doc.setdefault("tool", {})["isort"] = isort
    return doc
