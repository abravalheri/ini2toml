import re
from collections.abc import Mapping, MutableMapping
from typing import Any, TypeVar

from ..processing import (
    apply,
    create_item,
    is_false,
    is_true,
    set_nested,
    split_comment,
    split_kv_pairs,
    split_list,
)
from ..translator import Translator

M = TypeVar("M", bound=MutableMapping)

SECTION_SPLITTER = re.compile(r"\.|:")


def activate(translator: Translator):
    profile = translator["best_effort"]
    profile.post_processors.append(post_process)


def post_process(_orig: Mapping, doc: M) -> M:
    doc_items = list(doc.items())
    for name, section in doc_items:
        options = list(section.items())
        # Convert option values:
        for field, value in options:
            if "\n" in value or "\r" in value:
                if "=" in value:
                    apply(section, field, split_kv_pairs)
                else:
                    apply(section, field, split_list)
                continue

            obj = split_comment(value)
            value_str = obj.value_or("").strip()
            if value_str.isdecimal():
                v: Any = int(value_str)
            elif value_str.replace(".", "").isdecimal() and value_str.count(".") <= 1:
                v = float(value_str)
            elif is_true(value_str):
                v = True
            elif is_false(value_str):
                v = False
            else:
                v = value_str
            section[field] = create_item(v, obj.comment)

        # Separate nested sections
        if SECTION_SPLITTER.search(name):
            keys = SECTION_SPLITTER.split(name)
            doc.pop(name)
            set_nested(doc, keys, section)
        else:
            doc[name] = section

    return doc
