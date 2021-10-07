from textwrap import dedent

from ini2toml.plugins import isort
from ini2toml.translator import Translator


def test_isort():
    example = """\
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
    expected = """\
    [tool.isort]
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
    translator = Translator(plugins=[isort.activate])
    expected = dedent(expected).strip()
    for file, section in [(".isort.cfg", "settings"), ("setup.cfg", "isort")]:
        out = translator.translate(f"[{section}]\n{dedent(example)}", file).strip()
        print("expected=\n" + expected + "\n***")
        print("out=\n" + out)
        assert expected in out
