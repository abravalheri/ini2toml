import logging
from inspect import cleandoc
from typing import List, TypeVar

from ..types import IntermediateRepr, Translator

R = TypeVar("R", bound=IntermediateRepr)

_logger = logging.getLogger(__package__)

_FLAKE8_SECTIONS = ["flake8", "flake8-rst", "flake8:local-plugins"]

_KNOWN_INCOMPATIBILITIES = {
    "setup.cfg": [*_FLAKE8_SECTIONS, "devpi:upload"],
    ".flake8": _FLAKE8_SECTIONS,
}


def activate(translator: Translator):
    for name, sections in _KNOWN_INCOMPATIBILITIES.items():
        fn = ReportIncompatibleSections(name, sections)
        translator[name].intermediate_processors.insert(0, fn)


class ReportIncompatibleSections:
    """Remove well-know incompatible sections."""

    def __init__(self, profile: str, sections: List[str]):
        self._profile = profile
        self._sections = sections

    def __call__(self, cfg: R) -> R:
        invalid = [section for section in self._sections if section in cfg]
        if invalid:
            sections = ", ".join(repr(x) for x in invalid)
            _logger.warning(_warning_text(self._profile, sections))
        return cfg


def _warning_text(profile: str, sections: str) -> str:
    msg = f"""
    Sections {sections} ({profile!r}) may be problematic.

    It might be the case TOML files are not supported by the relevant tools,
    or that 'ini2toml' just lacks a plugin for this kind of configuration.

    Please review the generated output and remove these sections if necessary.
    """
    return cleandoc(msg) + "\n"
