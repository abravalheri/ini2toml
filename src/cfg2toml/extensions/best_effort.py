import re
from collections.abc import Mapping, MutableMapping
from functools import partial
from typing import Optional, TypeVar

from ..access import set_nested
from ..processing import Transformer, split_kv_pairs, split_list, split_scalar
from ..translator import Translator
from ..types import Profile

M = TypeVar("M", bound=MutableMapping)

SECTION_SPLITTER = re.compile(r"\.|:|\\")
KEY_SEP = "="


def activate(translator: Translator, transformer: Optional[Transformer] = None):
    profile = translator["best_effort"]
    extension = BestEffort(transformer or Transformer())
    extension.attach_to(profile)
    profile.help_text = extension.__doc__ or ""


class BestEffort:
    """Guess option value conversion based on the string format"""

    def __init__(
        self,
        transformer: Transformer,
        key_sep=KEY_SEP,
        section_splitter=SECTION_SPLITTER,
    ):
        self._tr = transformer
        self.key_sep = key_sep
        self.section_splitter = section_splitter
        self.split_dict = partial(split_kv_pairs, key_sep=KEY_SEP)

    def attach_to(self, profile: Profile):
        profile.toml_processors.append(self.process_values)

    def process_values(self, _orig: Mapping, doc: M) -> M:
        doc_items = list(doc.items())
        for name, section in doc_items:
            options = list(section.items())
            # Convert option values:
            for field, value in options:
                self.apply_best_effort(section, field, value)

            # Separate nested sections
            if self.section_splitter.search(name):
                keys = self.section_splitter.split(name)
                doc.pop(name)
                set_nested(doc, keys, section)
            else:
                doc[name] = section

        return doc

    def apply_best_effort(self, container: M, field: str, value: str) -> M:
        lines = value.splitlines()
        if len(lines) > 1:
            if self.key_sep in value:
                self._tr.apply(container, field, self.split_dict)
            else:
                self._tr.apply(container, field, split_list)
        else:
            self._tr.apply(container, field, split_scalar)
        return container
