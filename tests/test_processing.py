from functools import partial
from textwrap import dedent

import pytest

from cfg2toml import processing as lib
from cfg2toml.toml_adapter import dumps, loads


def test_coerce_bool():
    for value in ("true", "1", "yes", "on"):
        assert lib.coerce_bool(value) is True
        assert lib.coerce_bool(value.upper()) is True

    for value in ("false", "0", "no", "off", "none", "null", "nil"):
        assert lib.coerce_bool(value) is False
        assert lib.coerce_bool(value.upper()) is False

    with pytest.raises(ValueError):
        lib.coerce_bool("3")


def test_split_comment():
    example = "1 # comment"
    assert lib.split_comment(example) == lib.Commented("1", "comment")
    assert lib.split_comment(example, int) == lib.Commented(1, "comment")
    item = lib.split_comment(" # comment only")
    assert item.comment_only()


def test_split_list():
    example = "1, 2, 3 # comment"
    assert lib.split_list(example) == [lib.Commented(["1", "2", "3"], "comment")]
    example = "1, 2, 3 # comment"
    expected = [lib.Commented([1, 2, 3], "comment")]
    assert lib.split_list(example, coerce_fn=int) == expected
    example = "    1, 2, 3 # comment\n 4, 5, 6 # comment\n"
    expected = [
        lib.Commented([1, 2, 3], "comment"),
        lib.Commented([4, 5, 6], "comment"),
    ]
    assert lib.split_list(example, coerce_fn=int) == expected


def test_split_kv_pairs():
    example = "a=1, b=2, c=3 # comment"
    expected = [lib.Commented([("a", "1"), ("b", "2"), ("c", "3")], "comment")]
    assert lib.split_kv_pairs(example) == expected

    expected = [lib.Commented([("a", 1), ("b", 2), ("c", 3)], "comment")]
    assert lib.split_kv_pairs(example, coerce_fn=int) == expected

    example = "    a=1, b = 2, c =3 # comment\n d=4, e=5, f=6 # comment\n"
    expected = [
        lib.Commented([("a", 1), ("b", 2), ("c", 3)], "comment"),
        lib.Commented([("d", 4), ("e", 5), ("f", 6)], "comment"),
    ]
    assert lib.split_kv_pairs(example, coerce_fn=int) == expected


def test_apply():
    example = """\
    [table]
    option1 = "1"
    option2 = "value # comment"

    # commented single line compound value
    option3 = "1, 2, 3 # comment"
    option4 = "a=1, b=2, c=3 # comment"

    # commented multiline compound value
    option5 = "\\n   a=1 # comment\\n   b=2, c=3 # comment\\n"
    "option5.1" = "\\n   # header comment\\n   b=2, c=3 # comment\\n"
    option6 = "\\n   1\\n    2 # comment\\n    3\\n"
    option7 = "\\n   # comment\\n    1\\n    2\\n"

    # No subsplit dangling
    option8 = "\\n    1, 2\\n    3\\n"
    option9 = "\\n    1, 2\\n    3\\n"
    option10 = "\\n   a=1\\n   b=2, c=3\\n"
    """

    doc = loads(dedent(example))
    split_int = partial(lib.split_list, coerce_fn=int)
    split_kv_int = partial(lib.split_kv_pairs, coerce_fn=int)
    dangling_list_no_subsplit = partial(lib.split_list, subsplit_dangling=False)
    dangling_kv_no_subsplit = partial(lib.split_kv_pairs, subsplit_dangling=False)

    doc["table"] = lib.apply(doc["table"], "option1", int)
    expected = "option1 = 1"
    assert expected in dumps(doc)

    # assert len(_trailing_nl()) == 1

    doc["table"] = lib.apply(doc["table"], "option2", lib.split_comment)
    expected = 'option2 = "value" # comment'
    assert expected in dumps(doc)

    doc["table"] = lib.apply(doc["table"], "option3", split_int)
    expected = "option3 = [1, 2, 3] # comment"
    assert expected in dumps(doc)

    doc["table"] = lib.apply(doc["table"], "option4", split_kv_int)
    expected = "option4 = {a = 1, b = 2, c = 3} # comment"
    assert expected in dumps(doc)

    doc["table"] = lib.apply(doc["table"], "option5", split_kv_int)
    expected = """\
    [table.option5]
    a = 1 # comment
    b = 2
    c = 3 # comment
    """
    assert dedent(expected) in dumps(doc)

    doc["table"] = lib.apply(doc["table"], "option5.1", split_kv_int)
    expected = """\
    [table."option5.1"]
    # header comment
    b = 2
    c = 3 # comment
    """
    assert dedent(expected) in dumps(doc)

    doc["table"] = lib.apply(doc["table"], "option6", split_int)
    expected = """\
    option6 = [
        1,
        2, # comment,
        3,
    ]
    """
    # TODO: the comma after `comment` is a workaround remove when tomlkit is fixed
    assert dedent(expected) in dumps(doc)

    doc["table"] = lib.apply(doc["table"], "option7", split_int)
    expected = """\
    option7 = [
        # comment,
        1,
        2,
    ]
    """
    # TODO: the comma after `comment` is a workaround remove when tomlkit is fixed
    assert dedent(expected) in dumps(doc)

    doc["table"] = lib.apply(doc["table"], "option8", dangling_list_no_subsplit)
    expected = """\
    option8 = [
        "1, 2",
        "3",
    ]
    """
    # TODO: the comma after `comment` is a workaround remove when tomlkit is fixed
    assert dedent(expected) in dumps(doc)

    doc["table"] = lib.apply(doc["table"], "option9", split_int)
    expected = """\
    option9 = [
        1,
        2,
        3,
    ]
    """
    # TODO: the comma after `comment` is a workaround remove when tomlkit is fixed
    assert dedent(expected) in dumps(doc)

    doc["table"] = lib.apply(doc["table"], "option10", dangling_kv_no_subsplit)
    expected = """\
    [table.option10]
    a = "1"
    b = "2, c=3"
    """
    assert dedent(expected) in dumps(doc)
