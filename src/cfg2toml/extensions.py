# The code in this module is mostly borrowed/adapted from PyScaffold and was originally
# published under the MIT license

import sys
from typing import Callable, Iterable, List, Optional, cast

from .meta import __version__
from .types import Extension

if sys.version_info[:2] >= (3, 8):  # pragma: no cover
    # TODO: Import directly (no need for conditional) when `python_requires = >= 3.8`
    from importlib.metadata import EntryPoint, entry_points
else:  # pragma: no cover
    from importlib_metadata import EntryPoint, entry_points


ENTRYPOINT_GROUP = "cfg2toml.processing"


def iterate_entry_points(group=ENTRYPOINT_GROUP) -> Iterable[EntryPoint]:
    """Produces a generator yielding an EntryPoint object for each extension registered
    via `setuptools`_ entry point mechanism.

    This method can be used in conjunction with :obj:`load_from_entry_point` to filter
    the extensions before actually loading them.


    .. _setuptools: https://setuptools.readthedocs.io/en/latest/userguide/entry_point.html
    """  # noqa
    entries = entry_points()
    if hasattr(entries, "select"):
        # The select method was introduced in importlib_metadata 3.9 (and Python 3.10)
        # and the previous dict interface was declared deprecated
        entries_ = entries.select(group=group)  # type: ignore
    else:
        # TODO: Once Python 3.10 becomes the oldest version supported, this fallback and
        #       conditional statement can be removed.
        entries_ = (extension for extension in entries.get(group, []))
    return sorted(entries_, key=lambda e: e.name)


def load_from_entry_point(entry_point: EntryPoint) -> Extension:
    """Carefully load the extension, raising a meaningful message in case of errors"""
    try:
        return entry_point.load()(entry_point.name)
    except Exception as ex:
        raise ErrorLoadingExtension(entry_point=entry_point) from ex


def list_from_entry_points(
    group: str = ENTRYPOINT_GROUP,
    filtering: Callable[[EntryPoint], bool] = lambda _: True,
) -> List[Extension]:
    """Produces a list of extension objects for each extension registered
    via `setuptools`_ entry point mechanism.

    Args:
        group: name of the setuptools' entry_point group where extensions is being
            registered
        filtering: function returning a boolean deciding if the entry point should be
            loaded and included (or not) in the final list. A ``True`` return means the
            extension should be included.

    .. _setuptools: https://setuptools.readthedocs.io/en/latest/userguide/entry_point.html
    """  # noqa
    return [
        load_from_entry_point(e) for e in iterate_entry_points(group) if filtering(e)
    ]


class ErrorLoadingExtension(RuntimeError):
    """There was an error loading '{extension}'.
    Please make sure you have installed a version of the extension that is compatible
    with {package} {version}. You can also try uninstalling it.
    """

    def __init__(self, extension: str = "", entry_point: Optional[EntryPoint] = None):
        if entry_point and not extension:
            extension = getattr(entry_point, "module", entry_point.name)

        if extension.endswith(".extension"):
            extension = extension[: -len(".extension")]
        extension = extension.replace(f"{__package__}.", f"{__package__}ext-")

        sub = dict(package=__package__, version=__version__, extension=extension)
        super().__init__(cast(str, self.__doc__).format(*sub))
