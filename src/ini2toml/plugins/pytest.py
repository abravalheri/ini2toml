# https://docs.pytest.org/en/latest/reference/reference.html#configuration-options
# https://docs.pytest.org/en/latest/reference/customize.html#config-file-formats
from collections.abc import MutableMapping
from functools import partial
from typing import TypeVar

from ..transformations import coerce_scalar, split_list
from ..types import IntermediateRepr, Translator

R = TypeVar("R", bound=IntermediateRepr)

split_spaces = partial(split_list, sep=" ")
split_lines = partial(split_list, sep="\n")
# ^ most of the list values in pytest use whitespace separators,
#   but markers/filterwarnings are a special case.


def activate(translator: Translator):
    plugin = Pytest()
    for file in ("setup.cfg", "tox.ini", "pytest.ini"):
        translator[file].intermediate_processors.append(plugin.process_values)
    translator["pytest.ini"].help_text = plugin.__doc__ or ""


class Pytest:
    """Convert settings to 'pyproject.toml' ('ini_options' table)"""

    LINE_SEPARATED_LIST_VALUES = (
        "markers",
        "filterwarnings",
    )
    SPACE_LIST_VALUES = (
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
            if field in self.LINE_SEPARATED_LIST_VALUES:
                section[field] = split_lines(section[field])
            elif field in self.SPACE_LIST_VALUES:
                section[field] = split_spaces(section[field])
            else:
                section[field] = coerce_scalar(section[field])
