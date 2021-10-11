# https://docs.pytest.org/en/latest/reference/reference.html#configuration-options
# https://docs.pytest.org/en/latest/reference/customize.html#config-file-formats
from collections.abc import MutableMapping
from functools import partial
from typing import TypeVar

from ..transformations import coerce_scalar, split_list
from ..types import IntermediateRepr, Translator

R = TypeVar("R", bound=IntermediateRepr)

list_with_space = partial(split_list, sep=" ")
split_markers = partial(split_list, sep="\n")
# ^ most of the list values in pytest use whitespace separators,
#   but markers are a special case, since they can define a help text


def activate(translator: Translator):
    plugin = Pytest()
    for file in ("setup.cfg", "tox.ini", "pytest.ini"):
        translator[file].intermediate_processors.append(plugin.process_values)
    translator["pytest.ini"].help_text = plugin.__doc__ or ""


class Pytest:
    """Convert settings to 'pyproject.toml' ('ini_options' table)"""

    LIST_VALUES = (
        "filterwarnings",
        "norecursedirs",
        "python_classes",
        "python_files",
        "python_functions",
        "required_plugins",
        "testpaths",
        "usefixtures",
    )

    DONT_TOUCH = ("minversion",)

    def process_values(self, doc: R) -> R:
        candidates = [
            (("pytest", "ini_options"), "pytest", doc),
            (("tool", "pytest", "ini_options"), "tool:pytest", doc),
            (("tool", "pytest", "ini_options"), ("tool", "pytest"), doc),
            (("pytest", "ini_options"), "pytest", doc.get("tool", {})),
        ]
        for new_key, old_key, parent in candidates:
            section = parent.get(old_key)
            if section:
                self.process_section(section)
                parent.rename(old_key, new_key)
        return doc

    def process_section(self, section: MutableMapping):
        for field in section:
            if field in self.DONT_TOUCH:
                continue
            if field == "markers":
                section[field] = split_markers(section[field])
            elif field in self.LIST_VALUES:
                section[field] = list_with_space(section[field])
            else:
                section[field] = coerce_scalar(section[field])
