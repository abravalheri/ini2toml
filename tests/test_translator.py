from textwrap import dedent

import pytest

from ini2toml.errors import UndefinedProfile
from ini2toml.plugins import profile_independent_tasks
from ini2toml.profile import Profile, ProfileAugmentation
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


simple_setupcfg = """\
[metadata]
summary = Automatically translates .cfg/.ini files into TOML
author_email = example@example
license-file = LICENSE.txt
long_description_content_type = text/x-rst; charset=UTF-8
home_page = https://github.com/abravalheri/ini2toml/
classifier = Development Status :: 4 - Beta
platform = any
"""


def test_reuse_object():
    """Make sure the same translator object can be reused multiple times"""
    profile = Profile("setup.cfg")
    augmentations = []
    for task in ("normalise_newlines", "remove_empty_table_headers"):
        fn = getattr(profile_independent_tasks, task)
        aug = ProfileAugmentation(
            profile_independent_tasks.post_process(fn), active_by_default=True
        )
        augmentations.append(aug)

    translator = Translator(
        profiles=[profile], plugins=(), profile_augmentations=augmentations
    )
    active_augmentations = {aug.name: True for aug in augmentations}
    for _ in range(5):
        out = translator.translate(simple_setupcfg, "setup.cfg", active_augmentations)
        assert len(out) > 0
    processors = [
        *profile.post_processors,
        *profile.intermediate_processors,
        *profile.pre_processors,
    ]
    deduplicated = {getattr(p, "__name__", ""): p for p in processors}
    # Make sure there is no duplication in the processors
    assert len(processors) == len(deduplicated)


def test_deduplicate_plugins():
    plugins = [
        profile_independent_tasks.activate,
        profile_independent_tasks.activate,
    ]
    translator = Translator(plugins=plugins)
    assert len(translator.plugins) == 1
