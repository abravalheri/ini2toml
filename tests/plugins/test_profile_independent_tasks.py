from inspect import cleandoc

from ini2toml.plugins.profile_independent_tasks import (
    normalise_newlines,
    remove_empty_table_headers,
)


def test_terminating_line():
    assert normalise_newlines("a") == "a\n"
    assert normalise_newlines("a\n") == "a\n"
    assert normalise_newlines("a\n\n") == "a\n"


def test_remove_empty_table_headers():
    text = """
    [tools]
    [tools.setuptools]

    [tools.setuptools.package]


    [tools.setuptools.package.find]
    where = "src"
    """
    expected = """
    [tools.setuptools.package.find]
    where = "src"
    """

    assert remove_empty_table_headers(cleandoc(text)) == cleandoc(expected)
