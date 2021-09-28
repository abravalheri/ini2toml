# https://docs.pytest.org/en/latest/reference/reference.html#configuration-options
from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import TypeVar

from ..processing import apply, coerce_scalar, split_list
from ..translator import Translator

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


def activate(translator: Translator):
    for file in ("setup.cfg", "tox.ini", "pytest.ini"):
        profile = translator[file]
        profile.toml_processors.append(process_values)


def process_values(_orig: Mapping, doc: M) -> M:
    sec = doc.get("tool", {}).pop("pytest", {})
    sec = doc.pop("pytest", doc.pop("tool:pytest", sec))
    for field in sec:
        if field in DONT_TOUCH:
            continue
        if field == "markers":
            apply(sec, field, split_markers)
        elif field in LIST_VALUES:
            apply(sec, field, list_with_space)
        else:
            apply(sec, field, coerce_scalar)

    if sec:
        doc.setdefault("tool", {}).setdefault("pytest", {})["ini_options"] = sec
    return doc
