from cfg2toml import access as lib


def test_get_nested():
    nested = {"a": {"b": [0, 1], "c": {"d": "e"}}, "b": 1}
    assert lib.get_nested(nested, ("a", "b")) == [0, 1]
    assert lib.get_nested(nested, ("a", "c", "d")) == "e"
    assert lib.get_nested(nested, ("b",)) == 1


def test_set_nested():
    nested = {}
    lib.set_nested(nested, ("a", "b"), 0)
    lib.set_nested(nested, ("a", "c", "d"), "e")
    assert nested == {"a": {"b": 0, "c": {"d": "e"}}}

    nested = {"a": {"b": [0, 1]}}
    lib.set_nested(nested, ("a", "c"), 2)
    assert nested == {"a": {"b": [0, 1], "c": 2}}
    lib.set_nested(nested, ("d", "e"), 0)
    assert nested == {"a": {"b": [0, 1], "c": 2}, "d": {"e": 0}}


def test_pop_nested():
    nested = {"a": {"b": [0, 1], "c": {"d": "e"}}, "b": 1}
    assert lib.pop_nested(nested, ("a", "b")) == [0, 1]
    assert lib.pop_nested(nested, ("a", "c", "d")) == "e"
    assert lib.pop_nested(nested, ("b",)) == 1
    assert nested == {"a": {"c": {}}}
