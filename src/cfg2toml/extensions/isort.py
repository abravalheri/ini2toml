from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import Optional, Set, TypeVar

from ..processing import Transformer, coerce_scalar, kebab_case, split_list
from ..translator import Translator
from ..types import Profile

M = TypeVar("M", bound=MutableMapping)


def activate(translator: Translator, transformer: Optional[Transformer] = None):
    extension = ISort(transformer or Transformer())
    extension.attach_to(translator[".isort.cfg"], "settings")
    for file in ("setup.cfg", "tox.ini"):
        extension.attach_to(translator[file], "isort")


class ISort:
    def __init__(self, transformer: Transformer):
        self._tr = transformer

    def attach_to(self, profile: Profile, section_name: str = "isort"):
        profile.toml_processors.append(partial(self.process_values, section_name))

    def find_list_options(self, section: Mapping) -> Set[str]:
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

    def process_values(self, section_name: str, _orig: Mapping, doc: M) -> M:
        isort = doc.pop(section_name, doc.get("tool", {}).pop(section_name, {}))
        list_options = self.find_list_options(isort)
        for field in isort:
            if field in list_options:
                self._tr.apply(isort, field, split_list)
            else:
                self._tr.apply(isort, field, coerce_scalar)

        if isort:
            doc.setdefault("tool", {})["isort"] = isort
        return doc
