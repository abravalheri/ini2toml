"""Profile-independent tasks implemented via *profile augmentation*."""
import re
from functools import wraps
from typing import Callable

from ..types import Profile, Translator

DUPLICATED_NEWLINES = re.compile(r"\n+", re.M)
TABLE_START = re.compile(r"^\[(.*)\]", re.M)
EMPTY_TABLES = re.compile(r"^\[(.*)\]\n+\[(\1\.(?:.*))\]", re.M)
MISSING_TERMINATING_LINE = re.compile(r"(?<!\n)\Z", re.M)
# ^ POSIX tools will not play nicely with text files without a terminating new line
# https://unix.stackexchange.com/questions/18743/whats-the-point-in-adding-a-new-line-to-the-end-of-a-file


def activate(translator: Translator):
    tasks = [
        normalise_newlines,
        remove_empty_table_headers,
        ensure_terminating_newlines,
    ]
    for task in tasks:
        translator.augment_profiles(post_process(task), active_by_default=True)


def post_process(fn: Callable[[str], str]):
    @wraps(fn)
    def _augmentation(profile: Profile):
        profile.post_processors.append(fn)

    return _augmentation


def normalise_newlines(text: str) -> str:
    """Make sure every table is preceded by an empty newline, but remove them elsewhere
    in the output TOML document.
    Also ensure a terminating newline is present for best POSIX tool compatibility.
    """
    text = DUPLICATED_NEWLINES.sub(r"\n", text)
    text = TABLE_START.sub(r"\n[\1]", text)
    return MISSING_TERMINATING_LINE.sub("\n", text)


def remove_empty_table_headers(text: str) -> str:
    """Remove empty TOML table headers"""
    prev_text = ""
    while text != prev_text:
        prev_text = text
        text = EMPTY_TABLES.sub(r"[\2]", text).strip()
    return text


def ensure_terminating_newlines(text: str) -> str:
    return text.strip() + "\n"
