import argparse
import logging
import sys
from contextlib import contextmanager
from typing import List, Optional, Sequence

from cfg2toml.meta import __version__
from cfg2toml.translator import Translator

_logger = logging.getLogger(__package__)

DEFAULT_PROFILE = "best_effort"


def parse_args(args: Sequence[str], profiles: Sequence[str]) -> argparse.Namespace:
    """Parse command line parameters

    Args:
      args: command line parameters as list of strings (for example  ``["--help"]``).

    Returns: command line parameters namespace
    """
    description = "Automatically converts .cfg/.ini files into TOML"
    parser = argparse.ArgumentParser(description=description)
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
        "to perform the most appropriate conversion. Available profiles: "
        f"{', '.join(repr(p) for p in profiles)}.",
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
    try:
        return parser.parse_args(args)
    except Exception:
        if "-vv" in args or "--very-verbose" in args:
            setup_logging(logging.DEBUG)
        raise


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
    params = parse_args(args, available_profiles)
    setup_logging(params.loglevel)
    profile = _get_profile(params.profile, params.input_file.name, available_profiles)
    out = translator.translate(params.input_file.read(), profile)
    params.output_file.write(out)


def _get_profile(profile: Optional[str], file_name: str, available: List[str]) -> str:
    if profile:
        return profile

    if file_name in available:
        _logger.info(f"Profile not explicitly set, {file_name!r} inferred.")
        return file_name
    else:
        _logger.warning(f"Profile not explicitly set, using {DEFAULT_PROFILE!r}.")
        return DEFAULT_PROFILE
