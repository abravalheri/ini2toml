# https://docs.pytest.org/en/latest/reference/reference.html#configuration-options
# https://docs.pytest.org/en/latest/reference/customize.html#config-file-formats
from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import Optional, TypeVar

from ..processing import Transformer, coerce_scalar, split_list
from ..translator import Translator
from ..types import Profile

M = TypeVar("M", bound=MutableMapping)

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

list_with_space = partial(split_list, sep=" ")
split_markers = partial(split_list, sep="\n")
# ^ most of the list values in pytest use whitespace sepators,
#   but markers are a special case, since they can define a help text


def activate(translator: Translator, transformer: Optional[Transformer] = None):
    extension = Pytest(transformer or Transformer())
    for file in ("setup.cfg", "tox.ini", "pytest.ini"):
        extension.attach_to(translator[file])
    translator["pytest.ini"].help_text = extension.__doc__ or ""


class Pytest:
    """Convert settings to 'pyproject.toml' ('ini_options' table)"""

    def __init__(self, trasformer: Transformer):
        self._tr = trasformer

    def attach_to(self, profile: Profile):
        profile.toml_processors.append(self.process_values)

    def process_values(self, _orig: Mapping, doc: M) -> M:
        sec = doc.get("tool", {}).pop("pytest", {})
        sec = doc.pop("pytest", doc.pop("tool:pytest", sec))
        for field in sec:
            if field in DONT_TOUCH:
                continue
            if field == "markers":
                self._tr.apply(sec, field, split_markers)
            elif field in LIST_VALUES:
                self._tr.apply(sec, field, list_with_space)
            else:
                self._tr.apply(sec, field, coerce_scalar)

        if sec:
            doc.setdefault("tool", {}).setdefault("pytest", {})["ini_options"] = sec
        return doc
