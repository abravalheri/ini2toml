import re
from itertools import chain
from pathlib import Path

import pytest
import tomli
from validate_pyproject.api import Validator

from ini2toml import cli
from ini2toml.drivers import configparser, full_toml, lite_toml
from ini2toml.translator import Translator


def examples():
    here = Path(".").resolve()
    parent = Path(__file__).parent / "examples"
    for folder in parent.glob("*/"):
        cfg = chain(folder.glob("*.cfg"), folder.glob("*.ini"))
        toml = folder.glob("*.toml")
        for orig in cfg:
            expected = orig.with_suffix(".toml")
            if expected.is_file():
                yield str(orig.relative_to(here)), str(expected.relative_to(here))
            else:
                try:
                    yield str(orig.relative_to(here)), str(next(toml).relative_to(here))
                except:  # noqa
                    print(f"Missing TOML file to compare to {orig}")
                    raise


@pytest.fixture(scope="module")
def validate():
    """Use ``validate-pyproject`` to validate the generated TOML"""
    return Validator()


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.mark.parametrize(("original", "expected"), list(examples()))
def test_examples_api(original, expected, validate):
    translator = Translator()
    available_profiles = list(translator.profiles.keys())
    profile = cli.guess_profile(None, original, available_profiles)
    out = translator.translate(Path(original).read_text(), profile)
    expected_text = Path(expected).read_text().strip()
    assert out == expected_text
    # Make sure they can be parsed
    dict_equivalent = tomli.loads(out)
    assert dict_equivalent == tomli.loads(expected_text)
    assert validate(remove_deprecated(dict_equivalent)) is not None


COMMENT_LINE = re.compile(r"^\s*#[^\n]*\n", re.M)
INLINE_COMMENT = re.compile(r'#\s[^\n"]*$', re.M)


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.mark.parametrize(("original", "expected"), list(examples()))
def test_examples_api_lite(original, expected, validate):
    opts = {"ini_loads_fn": configparser.parse, "toml_dumps_fn": lite_toml.convert}
    translator = Translator(**opts)
    available_profiles = list(translator.profiles.keys())
    profile = cli.guess_profile(None, original, available_profiles)
    # We cannot compare "flake8" sections (currently not handled)
    # (ConfigParser automatically strips comments, contrary to ConfigUpdater)
    orig = Path(original)
    out = remove_flake8_from_toml(translator.translate(orig.read_text(), profile))
    expected_text = remove_flake8_from_toml(Path(expected).read_text().strip())

    # At least the Python-equivalents should be the same when parsing
    dict_equivalent = tomli.loads(out)
    assert dict_equivalent == tomli.loads(expected_text)
    assert validate(remove_deprecated(dict_equivalent)) is not None

    without_comments = COMMENT_LINE.sub("", expected_text)
    without_comments = INLINE_COMMENT.sub("", without_comments)
    try:
        assert out == without_comments
    except AssertionError:
        # We can ignore some minor formatting differences, as long as the parsed
        # dict is the same
        pass


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.mark.parametrize(("original", "expected"), list(examples()))
def test_examples_cli(original, expected, capsys):
    cli.run([original])
    (out, err) = capsys.readouterr()
    expected_text = Path(expected).read_text().strip()
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


def remove_deprecated(dict_equivalent):
    setuptools = dict_equivalent.get("tool", {}).get("setuptools", {})
    # The usage of ``data-files`` is deprecated in setuptools and not supported by pip
    setuptools.pop("data-files", None)
    return dict_equivalent
