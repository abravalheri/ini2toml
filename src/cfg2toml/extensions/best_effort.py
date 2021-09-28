import re
from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import TypeVar

from ..processing import apply, set_nested, split_kv_pairs, split_list, split_scalar
from ..translator import Translator

M = TypeVar("M", bound=MutableMapping)

SECTION_SPLITTER = re.compile(r"\.|:|\\")
KEY_SEP = "="


def activate(translator: Translator):
    profile = translator["best_effort"]
    profile.toml_processors.append(process_values)


def process_values(_orig: Mapping, doc: M) -> M:
    doc_items = list(doc.items())
    for name, section in doc_items:
        options = list(section.items())
        # Convert option values:
        for field, value in options:
            apply_best_effort(section, field, value)

        # Separate nested sections
        if SECTION_SPLITTER.search(name):
            keys = SECTION_SPLITTER.split(name)
            doc.pop(name)
            set_nested(doc, keys, section)
        else:
            doc[name] = section

    return doc


split_dict = partial(split_kv_pairs, key_sep=KEY_SEP)


def apply_best_effort(container: M, field: str, value: str) -> M:
    lines = value.splitlines()
    if len(lines) > 1:
        if KEY_SEP in value:
            apply(container, field, split_dict)
        else:
            apply(container, field, split_list)
    else:
        apply(container, field, split_scalar)
    return container
