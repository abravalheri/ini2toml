from textwrap import dedent

import tomli

from ini2toml.drivers import full_toml, lite_toml
from ini2toml.plugins import coverage
from ini2toml.translator import Translator


def test_coverage():
    example = """\
    # .coveragerc to control coverage.py
    [run]
    branch = True
    source = ini2toml
    # omit = bad_file.py
    [paths]
    source =
        src/
        */site-packages/
    [report]
    # Regexes for lines to exclude from consideration
    exclude_lines =
        # Have to re-enable the standard pragma
        pragma: no cover
        # Don't complain about missing debug-only code
        def __repr__
        # Don't complain if tests don't hit defensive assertion code
        raise AssertionError
        raise NotImplementedError
        # Don't complain if non-runnable code isn't run
        if 0:
        if __name__ == .__main__.:
    """
    expected = """\
    # .coveragerc to control coverage.py

    [run]
    branch = true
    source = ["ini2toml"]
    # omit = bad_file.py

    [paths]
    source = [
        "src/", 
        "*/site-packages/", 
    ]

    [report]
    # Regexes for lines to exclude from consideration
    exclude_lines = [
        # Have to re-enable the standard pragma
        "pragma: no cover", 
        # Don't complain about missing debug-only code
        "def __repr__", 
        # Don't complain if tests don't hit defensive assertion code
        "raise AssertionError", 
        "raise NotImplementedError", 
        # Don't complain if non-runnable code isn't run
        "if 0:", 
        "if __name__ == .__main__.:", 
    ]
    """
    for convert in (full_toml.convert, lite_toml.convert):
        translator = Translator(plugins=[coverage.activate], toml_dumps_fn=convert)
        out = translator.translate(dedent(example), ".coveragerc").strip()
        expected = dedent(expected).strip()
        print("expected=\n" + expected + "\n***")
        print("out=\n" + out)
        try:
            assert expected == out
        except AssertionError:
            # At least the Python-equivalents when parsing should be the same
            assert tomli.loads(expected) == tomli.loads(out)
