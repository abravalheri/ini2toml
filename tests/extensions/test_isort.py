from textwrap import dedent

from cfg2toml.extensions import isort
from cfg2toml.translator import Translator


def test_isort():
    example = """\
    profile = black
    order_by_type = false
    src_paths=isort,test
    known_first_party = cfg2toml
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
    known_first_party = ["cfg2toml"]
    combine_as_imports = true
    default_section = "THIRDPARTY"
    include_trailing_comma = true
    line_length = 79
    multi_line_output = 5
    """
    translator = Translator(extensions=[isort.activate])
    for file, section in [(".isort.cfg", "settings"), ("setup.cfg", "isort")]:
        out = translator.translate(f"[{section}]\n{dedent(example)}", file)
        assert dedent(expected).strip() in out
