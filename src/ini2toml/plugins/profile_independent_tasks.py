"""Profile-independent tasks implemented via *profile augmentation*."""
import re
from functools import wraps
from typing import Callable

from ..types import Profile, Translator

NEWLINES = re.compile(r"\n+", re.M)
TABLE_START = re.compile(r"^\[(.*)\]", re.M)
EMPTY_TABLES = re.compile(r"^\[(.*)\]\n+\[(\1\.(?:.*))\]", re.M)
TRAILING_SPACES = re.compile(r"[ \t]+$", re.M)


def activate(translator: Translator):
    tasks = [remove_trailing_spaces, normalise_newlines, remove_empty_table_headers]
    for task in tasks:
        translator.augment_profiles(post_process(task), active_by_default=True)


def post_process(fn: Callable[[str], str]):
    @wraps(fn)
    def _augmentation(profile: Profile):
        profile.post_processors.append(fn)

    return _augmentation


def remove_trailing_spaces(text: str) -> str:
    """Remove trailing spaces"""
    return TRAILING_SPACES.sub("", text)


def normalise_newlines(text: str) -> str:
    """Make sure every table is preceded by an empty newline, but remove them elsewhere
    in the output TOML document.
    """
    text = NEWLINES.sub(r"\n", text)
    return TABLE_START.sub(r"\n[\1]", text)


def remove_empty_table_headers(text: str) -> str:
    """Remove empty TOML table headers"""
    return EMPTY_TABLES.sub(r"[\2]", text).strip()
