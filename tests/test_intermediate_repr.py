import pytest

from ini2toml.intermediate_repr import Commented, CommentedKV
from ini2toml.intermediate_repr import IntermediateRepr as IR


class TestInteremediateRepr:
    def test_init(self):
        with pytest.raises(ValueError):
            # elements and order must have the same elements
            IR({"a": 1, "b": 2}, ["a", "c"])

    def test_eq(self):
        assert IR({"a": 1}, inline_comment="hello world") != IR({"a": 1})

    def test_rename(self):
        irepr = IR({"a": 1, "b": 2})
        with pytest.raises(KeyError):
            # Cannot rename to an existing key
            irepr.rename("a", "b")

        irepr.rename("a", "c")
        assert irepr == IR({"c": 1, "b": 2})

        with pytest.raises(KeyError):
            # Cannot rename to a missing key unless explicitly ignoring
            irepr.rename("a", "b")

        irepr.rename("a", "d", ignore_missing=True)
        assert irepr == IR({"c": 1, "b": 2})

    def test_insert(self):
        irepr = IR({"a": 1, "b": 2})
        with pytest.raises(KeyError):
            # Cannot insert an existing key
            irepr.insert(0, "a", 3)

    def test_copy(self):
        irepr = IR({"a": 1, "b": 2})
        other = irepr.copy()
        other["a"] = 3
        assert irepr != other
        assert other["a"] == 3
        assert irepr["a"] == 1


class TestCommentedKV:
    def test_find(self):
        v = CommentedKV([Commented([("a", 1), ("b", 2)]), Commented([("c", 3)])])
        assert v.find("a") == (0, 0)
        assert v.find("b") == (0, 1)
        assert v.find("c") == (1, 0)
        assert v.find("d") is None
