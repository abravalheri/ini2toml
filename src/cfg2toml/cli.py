import argparse
import logging
import sys
from contextlib import contextmanager
from itertools import chain
from pathlib import Path
from textwrap import dedent, wrap
from typing import Dict, List, Optional, Sequence

from .meta import __version__
from .translator import Translator
from .types import Profile, ProfileAugmentation

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
    "verbose": dict(
        flags=("-v", "--verbose"),
        dest="loglevel",
        action="store_const",
        const=logging.INFO,
        help="set loglevel to INFO",
    ),
    "very_verbose": dict(
        flags=("-vv", "--very-verbose"),
        dest="loglevel",
        action="store_const",
        const=logging.DEBUG,
        help="set loglevel to DEBUG",
    ),
}


def __meta__(
    profiles: Sequence[Profile], augmentations: Sequence[ProfileAugmentation]
) -> Dict[str, dict]:
    """'Hyper parameters' to instruct :mod:`argparse` how to create the CLI"""
    meta = {k: v.copy() for k, v in META.items()}
    meta["profile"]["help"] += _profiles_help_text(profiles)
    for aug in augmentations:
        dest = aug.name
        if aug.active_by_default:
            pre_help = "<<disable>> "
            flag = f"--no-{dest.replace('_', '-')}"
            action = "store_false"
            state = "active"
        else:
            pre_help = ""
            flag = f"--{dest.replace('_', '-')}"
            action = "store_true"
            state = "disabled"
        help_text = pre_help + _flatten_str(aug.help_text) + f" ({state} by default)"
        meta[aug.name] = dict(flags=(flag,), dest=dest, action=action, help=help_text)
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
    return parser.parse_args(args)


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
    profile_names = list(translator.profiles.keys())
    profile_augmentations = list(translator.augmentations.values())
    params = parse_args(args, profiles, profile_augmentations)
    setup_logging(params.loglevel)
    profile = _get_profile(params.profile, params.input_file.name, profile_names)
    active_augmentations = {k: v for k, v in vars(params).items() if k not in META}
    active_augmentations.pop("input_file", None)
    active_augmentations.pop("profile", None)
    out = translator.translate(params.input_file.read(), profile, active_augmentations)
    params.output_file.write(out)


class Formatter(argparse.RawTextHelpFormatter):
    # Since the stdlib does not specify what is the signature we need to implement in
    # order to create our own formatter, we are left no choice other then overwrite a
    # "private" method considered to be an implementation detail.

    def _split_lines(self, text, width):
        return list(chain.from_iterable(wrap(x, width) for x in text.splitlines()))


def _get_profile(profile: Optional[str], file_name: str, available: List[str]) -> str:
    if profile:
        return profile

    options = [file_name, Path(file_name).name]
    for option in options:
        if option in available:
            _logger.info(f"Profile not explicitly set, {option!r} inferred.")
            return option
    _logger.warning(f"Profile not explicitly set, using {DEFAULT_PROFILE!r}.")
    return DEFAULT_PROFILE


def _profiles_help_text(profiles: Sequence[Profile]):
    visible = (p for p in profiles if p.help_text.strip())
    return "\n".join(_format_profile_help(p) for p in visible)


def _flatten_str(text):
    text = " ".join(x.strip() for x in dedent(text).splitlines()).strip()
    text = text.rstrip(".,;").strip()
    return (text[0].lower() + text[1:]).strip()


def _format_profile_help(profile: Profile):
    return f"- {profile.name}: {_flatten_str(profile.help_text)}."
