from textwrap import dedent

import tomli

from ini2toml.drivers import full_toml, lite_toml
from ini2toml.plugins import isort
from ini2toml.translator import Translator


def test_isort():
    example = """\
    [{section}]
    profile = black
    order_by_type = false
    src_paths=isort,test
    known_first_party = ini2toml
    combine_as_imports = true
    default_section = THIRDPARTY
    include_trailing_comma = true
    line_length = 79
    multi_line_output = 5
    """
    expected_template = """\
    [{section}]
    profile = "black"
    order_by_type = false
    src_paths = ["isort", "test"]
    known_first_party = ["ini2toml"]
    combine_as_imports = true
    default_section = "THIRDPARTY"
    include_trailing_comma = true
    line_length = 79
    multi_line_output = 5
    """
    for convert in (lite_toml.convert, full_toml.convert):
        translator = Translator(plugins=[isort.activate], toml_dumps_fn=convert)
        for file, section in [(".isort.cfg", "settings"), ("setup.cfg", "isort")]:
            expected = dedent(expected_template.format(section=section)).strip()
            out = translator.translate(dedent(example).format(section=section), file)
            print("expected=\n" + expected + "\n***")
            print("out=\n" + out)
            try:
                assert expected in out
            except AssertionError:
                # At least the Python-equivalents when parsing should be the same
                assert tomli.loads(expected) == tomli.loads(out)
