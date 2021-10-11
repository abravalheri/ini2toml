import re
import sys
from itertools import chain
from pathlib import Path

import tomli

from ini2toml import cli
from ini2toml.drivers import configparser, full_toml, lite_toml
from ini2toml.translator import Translator


def examples():
    parent = Path(__file__).parent / "examples"
    for folder in parent.glob("*/"):
        cfg = chain(folder.glob("*.cfg"), folder.glob("*.ini"))
        toml = folder.glob("*.toml")
        for orig in cfg:
            expected = orig.with_suffix(".toml")
            if expected.is_file():
                yield orig, expected
            else:
                try:
                    yield orig, next(toml)
                except:  # noqa
                    print(f"Missing TOML file to compare to {orig}")
                    raise


def test_examples_api():
    translator = Translator()
    available_profiles = list(translator.profiles.keys())
    for orig, expected in examples():
        print(f"---------------------------- {orig} ----------------------------")
        profile = cli.guess_profile(None, str(orig), available_profiles)
        out = translator.translate(orig.read_text(), profile)
        expected_text = expected.read_text().strip()
        assert out == expected_text
        # Make sure they can be parsed
        assert tomli.loads(out) == tomli.loads(expected_text)


COMMENT_LINE = re.compile(r"^\s*#[^\n]*\n", re.M)
INLINE_COMMENT = re.compile(r'#\s[^\n"]*$', re.M)


def test_examples_api_lite():
    opts = {"ini_loads_fn": configparser.parse, "toml_dumps_fn": lite_toml.convert}
    translator = Translator(**opts)
    available_profiles = list(translator.profiles.keys())
    for orig, expected in examples():
        print(f"---------------------------- {orig} ----------------------------")
        profile = cli.guess_profile(None, str(orig), available_profiles)
        # We cannot compare "flake8" sections (currently not handled)
        # (ConfigParser automatically strips comments, contrary to ConfigUpdater)
        out = remove_flake8_from_toml(translator.translate(orig.read_text(), profile))
        expected_text = remove_flake8_from_toml(expected.read_text().strip())
        # At least the Python-equivalents should be the same when parsing
        assert tomli.loads(out) == tomli.loads(expected_text)
        without_comments = COMMENT_LINE.sub("", expected_text)
        without_comments = INLINE_COMMENT.sub("", without_comments)
        try:
            assert out == without_comments
        except AssertionError:
            # We can ignore some minor formatting differences, as long as the parsed
            # dict is the same
            pass


def test_examples_cli(capsys):
    for orig, expected in examples():
        print(f"---------------------- {orig} ----------------------", file=sys.stderr)
        cli.run([str(orig)])
        (out, err) = capsys.readouterr()
        expected_text = expected.read_text().strip()
        assert out == expected_text
        # Make sure they can be parsed
        assert tomli.loads(out) == tomli.loads(expected_text)


def remove_flake8_from_toml(text: str) -> str:
    # full_toml uses atoml that should not change any formatting, just remove the
    # parts we don't want
    doc = full_toml.loads(text)
    tool = doc.get("tool", {})
    for key in list(tool.keys()):  # eager to allow dictionary modifications
        if key.startswith("flake8"):
            tool.pop(key)
    return full_toml.dumps(doc)
