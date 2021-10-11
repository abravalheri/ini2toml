# https://pycqa.github.io/isort/docs/configuration/config_files
from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import Set, TypeVar

from ..transformations import coerce_scalar, kebab_case, split_list
from ..types import Transformation as T
from ..types import Translator

M = TypeVar("M", bound=MutableMapping)


def activate(translator: Translator):
    plugin = ISort()
    profile = translator[".isort.cfg"]
    fn = partial(plugin.process_values, section_name="settings")
    profile.intermediate_processors.append(fn)
    profile.help_text = plugin.__doc__ or ""

    for file in ("setup.cfg", "tox.ini"):
        translator[file].intermediate_processors.append(plugin.process_values)


class ISort:
    """Convert settings to 'pyproject.toml' equivalent"""

    FIELDS = {
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

    FIELD_ENDS = ["skip", "glob", "paths", "exclusions", "plugins"]
    FIELD_STARTS = ["known", "extra"]

    # dicts? ["import_headings", "git_ignore", "know_other"]

    def find_list_options(self, section: Mapping) -> Set[str]:
        dynamic_fields = (
            field
            for field in section
            if any(field.startswith(s) for s in self.FIELD_STARTS)
            or any(field.endswith(s) for s in self.FIELD_ENDS)
        )
        fields = {*self.FIELDS, *dynamic_fields}
        return {*fields, *map(kebab_case, fields)}

    def process_values(self, doc: M, section_name="isort") -> M:
        candidates = [
            doc.get(section_name),
            doc.get(("tool", section_name)),
            doc.get("tool", {}).get(section_name),
        ]
        for section in candidates:
            if section:
                self.process_section(section)
        return doc

    def process_section(self, section: M):
        list_options = self.find_list_options(section)
        for field in section:
            fn: T = split_list if field in list_options else coerce_scalar
            section[field] = fn(section[field])
