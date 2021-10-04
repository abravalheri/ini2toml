# https://mypy.readthedocs.io/en/stable/config_file.html
from collections.abc import Mapping, MutableMapping, MutableSequence
from functools import partial
from typing import List, Optional, TypeVar, cast

from ..processing import Transformer, coerce_scalar, split_list
from ..toml_adapter import aot
from ..translator import Translator
from ..types import Profile

M = TypeVar("M", bound=MutableMapping)

LIST_VALUES = (
    "files",
    "always_false",
    "disable_error_code",
    "plugins",
)
DONT_TOUCH = ("python_version",)

list_comma = partial(split_list, sep=",")


def activate(translator: Translator, transformer: Optional[Transformer] = None):
    extension = Mypy(transformer or Transformer())
    for file in ("setup.cfg", "mypy.ini", ".mypy.ini"):
        extension.attach_to(translator[file])

    translator["mypy.ini"].help_text = extension.__doc__ or ""


class Mypy:
    """Convert settings to 'pyproject.toml' equivalent"""

    def __init__(self, transformer: Transformer):
        self._tr = transformer

    def attach_to(self, profile: Profile):
        profile.toml_processors.append(self.process_values)

    def process_values(self, orig: Mapping, doc: M) -> M:
        for section in [*doc, *doc.get("tool", {})]:
            if section.startswith("mypy-"):
                doc = self.process_overrides_section(orig, doc, section)
            elif section == "mypy":
                doc = self.process_section(orig, doc, section)
        return doc

    def process_section(self, _orig: Mapping, doc: M, section_name: str) -> M:
        sec = doc.pop(section_name, doc.get("tool", {}).pop(section_name, {}))
        sec = self.process_options(sec)
        if not sec:
            return doc
        doc.setdefault("tool", {})["mypy"] = sec
        return doc

    def process_overrides_section(self, _orig: Mapping, doc: M, section_name: str) -> M:
        modules = [n.replace("mypy-", "") for n in section_name.split(",")]
        sec = doc.pop(section_name, doc.get("tool", {}).pop(section_name, {}))
        sec = self.process_options(sec)
        sec = self.add_overrides_modules(sec, modules)
        if not sec:
            return doc
        mypy = doc.setdefault("tool", {}).setdefault("mypy", {})
        mypy.setdefault("overrides", self.create_overrides()).append(sec)
        return doc

    def process_options(self, sec: M) -> M:
        for field in sec:
            if field in DONT_TOUCH:
                continue
            elif field in LIST_VALUES:
                self._tr.apply(sec, field, split_list)
            else:
                self._tr.apply(sec, field, coerce_scalar)
        return sec

    def create_overrides(self) -> MutableSequence:
        return cast(MutableSequence, aot())

    def add_overrides_modules(self, section: M, modules: List[str]) -> M:
        section["module"] = modules  # TODO: anyway of making this the first field?
        return section
