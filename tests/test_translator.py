from textwrap import dedent

import pytest

from cfg2toml.toml_adapter import comment, document, dumps, table
from cfg2toml.translator import Translator, UndefinedProfile


class TestUnderstandTomlLib:
    def test_opening_comment_without_nl_after(self):
        doc = document()
        doc.add(comment("opening comment"))
        doc["value"] = 42
        out = dumps(doc)
        expected = """\
        # opening comment
        value = 42
        """
        assert out == dedent(expected)

    def test_table_adds_nl_before(self):
        doc = document()
        doc["value"] = 42
        doc["table"] = table()
        out = dumps(doc)
        expected = """\
        value = 42

        [table]
        """
        assert out == dedent(expected)

    def test_opening_comment_with_table(self):
        doc = document()
        doc.add(comment("opening comment"))
        doc["table"] = table()
        out = dumps(doc)
        expected = """\
        # opening comment

        [table]
        """
        assert out == dedent(expected)


def test_simple_example():
    example = """\
    # comment

    [section1]
    option1 = value
    option2 = value # with comment

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
    option2 = "value" # with comment

    # comment

    [section2] # inline comment
    # comment
    option3 = "value"

    [section3]
    """
    translator = Translator(extensions=[])
    # ensure profile exists
    translator["simple"]
    out = translator.translate(dedent(example), "simple")
    print(out)
    assert out == dedent(expected).strip()


def test_parser_opts():
    example = """\
    : comment

    [section1]
    option1 - value
    option2 - value : with comment

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
    option2 = "value" # with comment

    # comment

    [section2] # inline comment
    # comment
    option3 = "value"

    [section3]
    """

    parser_opts = {"comment_prefixes": (":"), "delimiters": ("-")}
    translator = Translator(extensions=[], cfg_parser_opts=parser_opts)
    # ensure profile exists
    translator["simple"]
    out = translator.translate(dedent(example), "simple")
    print(out)
    assert out == dedent(expected).strip()


def test_undefined_profile():
    translator = Translator()
    with pytest.raises(UndefinedProfile):
        translator.translate("", "!!--UNDEFINED ??? PROFILE--!!")
