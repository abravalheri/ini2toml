import argparse
import logging
import sys
from contextlib import contextmanager
from itertools import chain
from pathlib import Path
from textwrap import dedent, wrap
from typing import List, Optional, Sequence

from .meta import __version__
from .translator import Translator
from .types import Profile

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


@critical_logging()
def parse_args(args: Sequence[str], profiles: Sequence[Profile]) -> argparse.Namespace:
    """Parse command line parameters

    Args:
      args: command line parameters as list of strings (for example  ``["--help"]``).

    Returns: command line parameters namespace
    """
    description = "Automatically converts .cfg/.ini files into TOML"
    parser = argparse.ArgumentParser(description=description, formatter_class=Formatter)
    parser.add_argument(
        "-V", "--version", action="version", version=f"{__package__} {__version__}"
    )
    parser.add_argument(
        dest="input_file",
        type=argparse.FileType("r"),
        help=".cfg/.ini file to be converted",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        default="-",
        type=argparse.FileType("w"),
        help="file where to write the converted TOML (`stdout` by default)",
    )
    parser.add_argument(
        "-p",
        "--profile",
        default=None,
        help=f"a translation profile name, that will instruct {__package__} how "
        "to perform the most appropriate conversion. Available profiles:\n"
        + _profiles_help_text(profiles),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        action="store_const",
        const=logging.INFO,
        help="set loglevel to INFO",
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        action="store_const",
        const=logging.DEBUG,
        help="set loglevel to DEBUG",
    )
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
    available_profiles = list(translator.profiles.keys())
    params = parse_args(args, list(translator.profiles.values()))
    setup_logging(params.loglevel)
    profile = _get_profile(params.profile, params.input_file.name, available_profiles)
    out = translator.translate(params.input_file.read(), profile)
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


def _format_profile_help(profile: Profile):
    text = " ".join(dedent(profile.help_text).splitlines()).strip()
    text = text.rstrip(".,;").strip()
    text = text[0].lower() + text[1:]
    return f"- {profile.name}: {text}."
