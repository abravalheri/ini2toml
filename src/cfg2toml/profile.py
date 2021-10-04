from dataclasses import dataclass, field, replace
from typing import List, Optional

from .types import CFGProcessor, ProfileAugmentationFn, TextProcessor, TOMLProcessor


@dataclass
class Profile:
    """Profile object that follows the public API defined in
    :class:`cfg2toml.types.Profile`.
    """

    name: str
    help_text: str = ""
    pre_processors: List[TextProcessor] = field(default_factory=list)
    cfg_processors: List[CFGProcessor] = field(default_factory=list)
    toml_processors: List[TOMLProcessor] = field(default_factory=list)
    post_processors: List[TextProcessor] = field(default_factory=list)
    cfg_parser_opts: dict = field(default_factory=dict)
    toml_template: str = ""

    replace = replace


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
