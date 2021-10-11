import argparse
import logging
import sys
from contextlib import contextmanager
from itertools import chain
from os import pathsep
from pathlib import Path
from textwrap import dedent, wrap
from typing import Dict, List, Optional, Sequence

from . import __version__
from .translator import Translator
from .types import CLIChoice, Profile, ProfileAugmentation

_logger = logging.getLogger(__package__)

DEFAULT_PROFILE = "best_effort"


@contextmanager
def critical_logging():
    """Make sure the logging level is set even before parsing the CLI args"""
    try:
        yield
    except Exception:
        if "-vv" in sys.argv or "--very-verbose" in sys.argv:
            setup_logging(logging.DEBUG)
        raise


META: Dict[str, dict] = {
    "version": dict(
        flags=("-V", "--version"),
        action="version",
        version=f"{__package__} {__version__}",
    ),
    "input_file": dict(
        dest="input_file",
        type=argparse.FileType("r"),
        help=".cfg/.ini file to be converted",
    ),
    "output_file": dict(
        flags=("-o", "--output-file"),
        default="-",
        type=argparse.FileType("w"),
        help="file where to write the converted TOML (`stdout` by default)",
    ),
    "profile": dict(
        flags=("-p", "--profile"),
        default=None,
        help=f"a translation profile name, that will instruct {__package__} how "
        "to perform the most appropriate conversion. Available profiles:\n",
    ),
    "enable": dict(
        flags=("-E", "--enable"),
        nargs="+",
        dest="enable",
        metavar="TRANSFORMATION",
        help="enable one or more of the following processing options (optional):\n",
    ),
    "disable": dict(
        flags=("-D", "--disable"),
        nargs="+",
        dest="disable",
        default=(),
        metavar="TRANSFORMATION",
        help="disable one or more of the following processing options "
        "(active by default):\n",
    ),
    "verbose": dict(
        flags=("-v", "--verbose"),
        dest="loglevel",
        action="store_const",
        const=logging.INFO,
        help="set logging level to INFO",
    ),
    "very_verbose": dict(
        flags=("-vv", "--very-verbose"),
        dest="loglevel",
        action="store_const",
        const=logging.DEBUG,
        help="set logging level to DEBUG",
    ),
}


def __meta__(
    profiles: Sequence[Profile], augmentations: Sequence[ProfileAugmentation]
) -> Dict[str, dict]:
    """'Hyper parameters' to instruct :mod:`argparse` how to create the CLI"""
    meta = {k: v.copy() for k, v in META.items()}
    meta["profile"]["help"] += _choices_help(profiles, lambda x: x.help_text.strip())

    enable: List[ProfileAugmentation] = []
    disable: List[ProfileAugmentation] = []
    for aug in sorted(augmentations, key=lambda x: x.name):
        target = disable if aug.active_by_default else enable
        target.append(aug)

    for key, value in {"enable": enable, "disable": disable}.items():
        meta[key]["choices"] = [aug.name for aug in value]
        meta[key]["help"] += _choices_help(value)
        if not value:
            meta.pop(key, None)

    return meta


@critical_logging()
def parse_args(
    args: Sequence[str],
    profiles: Sequence[Profile],
    augmentations: Sequence[ProfileAugmentation],
) -> argparse.Namespace:
    """Parse command line parameters

    Args:
      args: command line parameters as list of strings (for example  ``["--help"]``).

    Returns: command line parameters namespace
    """
    description = "Automatically converts .cfg/.ini files into TOML"
    parser = argparse.ArgumentParser(description=description, formatter_class=Formatter)
    for opts in __meta__(profiles, augmentations).values():
        parser.add_argument(*opts.pop("flags", ()), **opts)
    parser.set_defaults(loglevel=logging.WARNING)
    params = parser.parse_args(args)
    profile_names = [p.name for p in profiles]
    profile = guess_profile(params.profile, params.input_file.name, profile_names)
    params.profile = profile
    opts = vars(params)
    active_augmentations = {k: True for k in (opts.get("enable") or ())}
    active_augmentations.update({k: False for k in (opts.get("disable") or ())})
    params.active_augmentations = active_augmentations
    return params


def setup_logging(loglevel: int):
    """Setup basic logging

    Args:
      loglevel: minimum loglevel for emitting messages
    """
    logformat = "[%(levelname)s] %(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stderr, format=logformat)


@contextmanager
def exceptisons2exit():
    try:
        yield
    except Exception as ex:
        _logger.error(f"{ex.__class__.__name__}: {ex}")
        _logger.debug("Please check the following information:", exc_info=True)
        raise SystemExit(1)


@exceptisons2exit()
def run(args: Sequence[str] = ()):
    """Wrapper allowing :obj:`Translator` to be called in a CLI fashion.

    Instead of returning the value from :func:`Translator.translate`, it prints the
    result to the given ``output_file`` or ``stdout``.

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--verbose", "setup.cfg"]``).
    """
    args = args or sys.argv[1:]
    translator = Translator()
    profiles = list(translator.profiles.values())
    profile_augmentations = list(translator.augmentations.values())
    params = parse_args(args, profiles, profile_augmentations)
    setup_logging(params.loglevel)
    out = translator.translate(
        params.input_file.read(), params.profile, params.active_augmentations
    )
    params.output_file.write(out)


class Formatter(argparse.RawTextHelpFormatter):
    # Since the stdlib does not specify what is the signature we need to implement in
    # order to create our own formatter, we are left no choice other then overwrite a
    # "private" method considered to be an implementation detail.

    def _split_lines(self, text, width):
        return list(chain.from_iterable(wrap(x, width) for x in text.splitlines()))


def guess_profile(profile: Optional[str], file_name: str, available: List[str]) -> str:
    if profile:
        return profile

    name = Path(file_name).name
    if name in available:
        # Optimize for the easy case
        _logger.info(f"Profile not explicitly set, {name!r} inferred.")
        return name

    fname = file_name.replace(pathsep, "/")
    for name in available:
        if fname.endswith(name):
            _logger.info(f"Profile not explicitly set, {name!r} inferred.")
            return name

    _logger.warning(f"Profile not explicitly set, using {DEFAULT_PROFILE!r}.")
    return DEFAULT_PROFILE


def _choices_help(choices: Sequence[CLIChoice], filt=lambda _: True) -> str:
    """``filt``: predicate function, only choices for which ``filt(c)`` is ``True`` will
    be included in the help text.
    """
    return "\n".join(_format_choice_help(c) for c in choices if filt(c))


def _flatten_str(text: str) -> str:
    if not text:
        return text
    text = " ".join(x.strip() for x in dedent(text).splitlines()).strip()
    text = text.rstrip(".,;").strip()
    return (text[0].lower() + text[1:]).strip()


def _format_choice_help(choice: CLIChoice) -> str:
    return f'- "{choice.name}": {_flatten_str(choice.help_text)}.'
