import logging
from typing import Mapping, Optional, Sequence

from . import types  # Structural/Abstract types
from .base_translator import EMPTY, BaseTranslator
from .plugins import list_from_entry_points as list_all_plugins

_logger = logging.getLogger(__name__)


class Translator(BaseTranslator[str]):
    """``Translator`` is the main public Python API exposed by the ``ini2toml``,
    to convert strings represeting ``.ini/.cfg`` files into the ``TOML`` syntax.

    It follows the public API defined in :class:`ini2toml.types.Translator`, and is very
    similar to :class:`~ini2toml.base_translator.BaseTranslator`.
    The main difference is that ``Translator`` will try to automatically figure out the
    values for ``plugins``, ``ini_loads_fn`` and ``toml_dumps_fn`` when they are not
    passed, based on the installed Python packages (and available `entry-points`_),
    while ``BaseTranslator`` requires the user to explicitly set these parameters.

    For most of the users ``Translator`` is recommended over ``BaseTranslator``.

    See :class:`~ini2toml.base_translator.BaseTranslator` for a description of the
    instantiation parameters.

    .. _entry-points: https://packaging.python.org/specifications/entry-points/
    """

    def __init__(
        self,
        plugins: Optional[Sequence[types.Plugin]] = None,
        profiles: Sequence[types.Profile] = (),
        profile_augmentations: Sequence[types.ProfileAugmentation] = (),
        ini_parser_opts: Mapping = EMPTY,
        ini_loads_fn: Optional[types.IniLoadsFn] = None,
        toml_dumps_fn: Optional[types.TomlDumpsFn] = None,
    ):
        super().__init__(
            ini_loads_fn=ini_loads_fn or _discover_ini_loads_fn(),
            toml_dumps_fn=toml_dumps_fn or _discover_toml_dumps_fn(),
            plugins=list_all_plugins() if plugins is None else plugins,
            ini_parser_opts=ini_parser_opts,
            profiles=profiles,
            profile_augmentations=profile_augmentations,
        )


def _discover_ini_loads_fn() -> types.IniLoadsFn:
    try:
        from .drivers.configupdater import parse
    except ImportError:  # pragma: no cover
        from .drivers.configparser import parse  # type: ignore[no-redef]

    return parse


def _discover_toml_dumps_fn() -> types.TomlDumpsFn:
    try:
        from .drivers.full_toml import convert
    except ImportError:  # pragma: no cover
        try:
            from .drivers.lite_toml import convert  # type: ignore[no-redef]
        except ImportError:
            msg = "Please install either `ini2toml[full]` or `ini2toml[lite]`"
            _logger.warning(f"{msg}. `ini2toml` (alone) is not valid.")
            raise

    return convert
