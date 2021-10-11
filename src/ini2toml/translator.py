import logging
from functools import reduce
from types import MappingProxyType
from typing import Callable, Dict, List, Mapping, Optional, Sequence

from . import types  # Structural/Abstract types
from .errors import (
    AlreadyRegisteredAugmentation,
    InvalidAugmentationName,
    UndefinedProfile,
)
from .plugins import list_from_entry_points as list_all_plugins
from .profile import Profile, ProfileAugmentation
from .transformations import apply

EMPTY = MappingProxyType({})  # type: ignore


_logger = logging.getLogger(__name__)


class Translator:
    """Translator object that follows the public API defined in
    :class:`ini2toml.types.Translator`.
    """

    profiles: Dict[str, types.Profile]
    plugins: List[types.Plugin]

    def __init__(
        self,
        profiles: Optional[Sequence[types.Profile]] = None,
        plugins: Optional[List[types.Plugin]] = None,
        ini_parser_opts: Optional[dict] = None,
        profile_augmentations: Optional[Sequence[types.ProfileAugmentation]] = None,
        ini_loads_fn: Optional[Callable[[str, dict], types.IntermediateRepr]] = None,
        toml_dumps_fn: Optional[Callable[[types.IntermediateRepr], str]] = None,
    ):
        self.plugins = list_all_plugins() if plugins is None else plugins
        self.ini_parser_opts = ini_parser_opts or {}
        self.profiles = {p.name: p for p in (profiles or ())}
        augmentations = profile_augmentations or ()
        self.augmentations: Dict[str, types.ProfileAugmentation] = {
            (p.name or p.fn.__name__): p for p in augmentations
        }

        self._loads_fn = ini_loads_fn
        self._dumps_fn = toml_dumps_fn

        for activate in self.plugins:
            activate(self)

    def loads(self, text: str) -> types.IntermediateRepr:
        if self._loads_fn is None:
            try:
                from .drivers.configupdater import parse
            except ImportError:  # pragma: no cover
                from .drivers.configparser import parse  # type: ignore[no-redef]
            self._loads_fn = parse

        return self._loads_fn(text, self.ini_parser_opts)

    def dumps(self, irepr: types.IntermediateRepr) -> str:
        if self._dumps_fn is None:
            try:
                from .drivers.full_toml import convert
            except ImportError:  # pragma: no cover
                try:
                    from .drivers.lite_toml import convert  # type: ignore[no-redef]
                except ImportError:
                    msg = "Please install either `ini2toml[full]` or `ini2toml[lite]`"
                    _logger.warning(f"{msg}. `ini2toml` (alone) is not valid.")
                    raise
            self._dumps_fn = convert

        return self._dumps_fn(irepr)

    def __getitem__(self, profile_name: str) -> types.Profile:
        if profile_name not in self.profiles:
            profile = Profile(profile_name)
            if self.ini_parser_opts:
                profile = profile.replace(ini_parser_opts=self.ini_parser_opts)
            self.profiles[profile_name] = profile
        return self.profiles[profile_name]

    def augment_profiles(
        self,
        fn: types.ProfileAugmentationFn,
        active_by_default: bool = False,
        name: str = "",
        help_text: str = "",
    ):
        """Register a profile augmentation function to be called after the
        profile is selected and before the actual translation.
        """
        name = (name or fn.__name__).strip()
        InvalidAugmentationName.check(name)
        AlreadyRegisteredAugmentation.check(name, fn, self.augmentations)
        help_text = help_text or fn.__doc__ or ""
        obj = ProfileAugmentation(fn, active_by_default, name, help_text)
        self.augmentations[name] = obj

    def _add_augmentations(
        self, profile: types.Profile, explicit_activation: Mapping[str, bool] = EMPTY
    ) -> types.Profile:
        for aug in self.augmentations.values():
            if aug.is_active(explicit_activation.get(aug.name)):
                aug.fn(profile)
        return profile

    def translate(
        self,
        ini: str,
        profile_name: str,
        active_augmentations: Mapping[str, bool] = EMPTY,
    ) -> str:
        UndefinedProfile.check(profile_name, list(self.profiles.keys()))
        profile = self._add_augmentations(self[profile_name], active_augmentations)

        ini = reduce(apply, profile.pre_processors, ini)
        irepr = self.loads(ini)
        irepr = reduce(apply, profile.intermediate_processors, irepr)
        toml = self.dumps(irepr)
        return reduce(apply, profile.post_processors, toml)
