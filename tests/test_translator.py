from textwrap import dedent

import pytest

from ini2toml.errors import UndefinedProfile
from ini2toml.translator import Translator


def test_simple_example():
    example = """\
    # comment

    [section1]
    option1 = value
    option2 = value # option comments are considered part of the value

    # comment
    [section2] # inline comment
    # comment
    option3 = value
    [section3]
    """
    # Obs: TOML always add a space before a new section
    expected = """\
    # comment

    [section1]
    option1 = "value"
    option2 = "value # option comments are considered part of the value"

    # comment

    [section2] # inline comment
    # comment
    option3 = "value"

    [section3]
    """
    translator = Translator(plugins=[])
    # ensure profile exists
    translator["simple"]
    out = translator.translate(dedent(example), "simple")
    print(out)
    assert out == dedent(expected)


def test_parser_opts():
    example = """\
    : comment

    [section1]
    option1 - value
    option2 - value : option comments are considered part of the value

    : comment
    [section2] : inline comment
    : comment
    option3 - value
    [section3]
    """
    # Obs: TOML always add a space before a new section
    expected = """\
    # comment

    [section1]
    option1 = "value"
    option2 = "value : option comments are considered part of the value"

    # comment

    [section2] # inline comment
    # comment
    option3 = "value"

    [section3]
    """

    parser_opts = {"comment_prefixes": (":",), "delimiters": ("-",)}
    translator = Translator(plugins=[], ini_parser_opts=parser_opts)
    # ensure profile exists
    translator["simple"]
    out = translator.translate(dedent(example), "simple")
    print(out)
    assert out == dedent(expected)


def test_undefined_profile():
    translator = Translator()
    with pytest.raises(UndefinedProfile):
        translator.translate("", "!!--UNDEFINED ??? PROFILE--!!")
