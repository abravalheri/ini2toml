from textwrap import dedent

import tomli

from ini2toml.drivers import full_toml, lite_toml
from ini2toml.plugins import pytest
from ini2toml.translator import Translator


def test_pytest():
    example = """\
    [pytest]
    minversion = 6.0
    addopts = -ra -q --cov ini2toml
    testpaths = tests
    python_files = test_*.py check_*.py example_*.py
    required_plugins = pytest-django>=3.0.0,<4.0.0 pytest-html pytest-xdist>=1.0.0
    norecursedirs =
        dist
        build
        .tox
    """
    expected = """\
    [pytest]
    [pytest.ini_options]
    minversion = "6.0"
    addopts = "-ra -q --cov ini2toml"
    testpaths = ["tests"]
    python_files = ["test_*.py", "check_*.py", "example_*.py"]
    required_plugins = ["pytest-django>=3.0.0,<4.0.0", "pytest-html", "pytest-xdist>=1.0.0"]
    norecursedirs = [
        "dist", 
        "build", 
        ".tox", 
    ]
    """  # noqa
    for convert in (lite_toml.convert, full_toml.convert):
        translator = Translator(plugins=[pytest.activate], toml_dumps_fn=convert)
        out = translator.translate(dedent(example), "pytest.ini").strip()
        expected = dedent(expected).strip()
        print("expected=\n" + expected + "\n***")
        print("out=\n" + out)
        try:
            assert expected in out
        except AssertionError:
            # At least the Python-equivalents when parsing should be the same
            assert tomli.loads(expected) == tomli.loads(out)
