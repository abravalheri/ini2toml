import warnings
from inspect import cleandoc
from typing import List, TypeVar

from ..types import IntermediateRepr, Translator

R = TypeVar("R", bound=IntermediateRepr)


_FLAKE8_SECTIONS = ["flake8", "flake8:local-plugins"]

_KNOWN_INCOMPATIBILITIES = {
    "setup.cfg": ["flake8", "flake8:local-plugins", "devpi:upload"],
    ".flake8": _FLAKE8_SECTIONS,
}


def activate(translator: Translator):
    for name, sections in _KNOWN_INCOMPATIBILITIES.items():
        fn = StripSections(name, sections)
        translator[name].intermediate_processors.insert(0, fn)


class StripSections:
    """Remove well-know incompatible sections."""

    def __init__(self, profile: str, sections: List[str]):
        self._profile = profile
        self._sections = sections

    def __call__(self, cfg: R) -> R:
        invalid = [section for section in self._sections if section in cfg]
        if invalid:
            sections = ", ".join(repr(x) for x in invalid)
            ConfigurationNotSupported.emit(self._profile, sections)
        for section in invalid:
            del cfg[section]
        return cfg


class ConfigurationNotSupported(UserWarning):
    """
    Ignoring sections {sections} ({profile!r}).

    It might be the case TOML files are not supported by the relevant tools,
    or that 'ini2toml' just lacks a plugin for this kind of configuration.
    """

    @classmethod
    def emit(cls, profile, sections):
        msg = cleandoc(cls.__doc__.format(profile=profile, sections=sections))
        warnings.warn(msg, cls, stacklevel=6)
