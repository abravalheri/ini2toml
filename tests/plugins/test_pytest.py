from textwrap import dedent

import pytest
import tomli

from ini2toml.drivers import full_toml, lite_toml
from ini2toml.plugins.pytest import activate
from ini2toml.translator import FullTranslator

EXAMPLES = {
    "simple": {
        "example": """\
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
            filterwarnings=
                error
                ignore:Please use `dok_matrix` from the `scipy\\.sparse` namespace, the `scipy\\.sparse\\.dok` namespace is deprecated.:DeprecationWarning
            """,  # noqa
        "expected": """\
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
            filterwarnings = [
                "error",
                'ignore:Please use `dok_matrix` from the `scipy\\.sparse` namespace, the `scipy\\.sparse\\.dok` namespace is deprecated.:DeprecationWarning',
            ]
            """,  # noqa
    },
    "multiline-addopts-empty-first": {
        "example": """\
            [pytest]
            addopts =
               -ra -q
               # comment
               --cov ini2toml
            """,
        "expected": '''\
            [pytest.ini_options]
            addopts = """
            -ra -q
            --cov ini2toml
            """
            ''',
    },
    "multiline-addopts-no-empty": {
        "example": """\
            [pytest]
            addopts = -ra -q
               # comment
               --cov ini2toml
            """,
        "expected": '''\
            [pytest.ini_options]
            addopts = """-ra -q
            --cov ini2toml
            """
            ''',
    },
}


@pytest.mark.parametrize("example_name", EXAMPLES.keys())
def test_pytest(example_name):
    example = EXAMPLES[example_name]["example"]
    expected = EXAMPLES[example_name]["expected"]

    for convert in (lite_toml.convert, full_toml.convert):
        translator = FullTranslator(plugins=[activate], toml_dumps_fn=convert)
        out = translator.translate(dedent(example), "pytest.ini").strip()
        expected = dedent(expected).strip()
        print("expected=\n" + expected + "\n***")
        print("out=\n" + out)
        try:
            assert expected in out
        except AssertionError:
            # At least the Python-equivalents when parsing should be the same
            assert tomli.loads(expected) == tomli.loads(out)
