from textwrap import dedent

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
    [tool]
    [tool.pytest]
    [tool.pytest.ini_options]
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
    translator = Translator(plugins=[pytest.activate])
    out = translator.translate(dedent(example), "pytest.ini").strip()
    expected = dedent(expected).strip()
    print("expected=\n" + expected + "\n***")
    print("out=\n" + out)
    assert expected == out
