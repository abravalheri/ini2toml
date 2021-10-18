from dataclasses import dataclass, field
from dataclasses import replace as _replace
from typing import List, Optional, TypeVar

from .types import IntermediateProcessor, ProfileAugmentationFn, TextProcessor

P = TypeVar("P", bound="Profile")


@dataclass
class Profile:
    """Profile object that follows the public API defined in
    :class:`ini2toml.types.Profile`.
    """

    name: str
    help_text: str = ""
    pre_processors: List[TextProcessor] = field(default_factory=list)
    intermediate_processors: List[IntermediateProcessor] = field(default_factory=list)
    post_processors: List[TextProcessor] = field(default_factory=list)
    ini_parser_opts: Optional[dict] = None

    def replace(self: P, **changes) -> P:
        """See :func:`dataclasses.replace`"""
        return _replace(self, **changes)


@dataclass
class ProfileAugmentation:
    fn: ProfileAugmentationFn
    active_by_default: bool = False
    name: str = ""
    help_text: str = ""

    def is_active(self, explicitly_active: Optional[bool] = None) -> bool:
        """``explicitly_active`` is a tree-state variable: ``True`` if the user
        explicitly asked for the augmentation, ``False`` if the user explicitly denied
        the augmentation, or ``None`` otherwise.
        """
        activation = explicitly_active
        return activation is True or (activation is None and self.active_by_default)
