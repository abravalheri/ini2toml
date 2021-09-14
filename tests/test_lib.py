import pytest

from cfg2toml import lib


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
