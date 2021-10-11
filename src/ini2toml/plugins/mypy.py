# https://mypy.readthedocs.io/en/stable/config_file.html
import string
from collections.abc import MutableMapping, MutableSequence
from functools import partial
from typing import List, TypeVar, cast

from ..transformations import coerce_scalar, split_list
from ..types import IntermediateRepr
from ..types import Transformation as T
from ..types import Translator

M = TypeVar("M", bound=MutableMapping)
R = TypeVar("R", bound=IntermediateRepr)

list_comma = partial(split_list, sep=",")


def activate(translator: Translator):
    plugin = Mypy()
    for file in ("setup.cfg", "mypy.ini", ".mypy.ini"):
        translator[file].intermediate_processors.append(plugin.process_values)

    translator["mypy.ini"].help_text = plugin.__doc__ or ""


class Mypy:
    """Convert settings to 'pyproject.toml' equivalent"""

    LIST_VALUES = (
        "files",
        "always_false",
        "disable_error_code",
        "plugins",
    )

    DONT_TOUCH = ("python_version",)

    def process_values(self, doc: M) -> M:
        for parent in (doc, doc.get("tool", {})):
            for key in list(parent.keys()):  # need to be eager: we will delete elements
                key_ = key[-1] if isinstance(key, tuple) else key
                if not isinstance(key_, str):
                    continue
                name = key_.strip('"' + string.whitespace)
                if name.startswith("mypy-"):
                    overrides = self.get_or_create_overrides(parent)
                    self.process_overrides(parent.pop(key), overrides, name)
                elif name == "mypy":
                    self.process_options(parent[key])
        return doc

    def process_overrides(self, section: R, overrides: MutableSequence, name: str) -> R:
        section = self.process_options(section)
        modules = [n.replace("mypy-", "") for n in name.split(",")]
        self.add_overrided_modules(section, name, modules)
        overrides.append(section)
        return section

    def process_options(self, section: M) -> M:
        for field in section:
            if field in self.DONT_TOUCH:
                continue
            fn: T = split_list if field in self.LIST_VALUES else coerce_scalar
            section[field] = fn(section[field])
        return section

    def get_or_create_overrides(self, parent: MutableMapping) -> MutableSequence:
        mypy = parent.setdefault("mypy", IntermediateRepr())
        return cast(MutableSequence, mypy.setdefault("overrides", []))

    def add_overrided_modules(self, section: R, name: str, modules: List[str]):
        if not isinstance(section, IntermediateRepr):
            raise ValueError(f"Expecting section {name} to be an IntermediateRepr")
        if "module" not in section:
            section.insert(0, "module", modules)
