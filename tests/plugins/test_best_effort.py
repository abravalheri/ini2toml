from textwrap import dedent

import pytest

from ini2toml.drivers.full_toml import loads
from ini2toml.plugins import best_effort
from ini2toml.translator import Translator


@pytest.fixture
def translate():
    translator = Translator(plugins=[best_effort.activate])
    return lambda text: translator.translate(text, "best_effort")


@pytest.fixture
def ini2tomlobj(translate):
    return lambda text: loads(translate(text))


def test_best_effort(ini2tomlobj):
    example = """\
    [section]
    a = 1
    b = 0.42
    c = false
    d = on
    f =
        a
        b
    e =
        a=1
        b=2
    [nested.section]
    value = string
    """
    doc = ini2tomlobj(dedent(example))
    assert doc["section"]["a"] == 1
    assert doc["section"]["b"] == 0.42
    assert doc["section"]["c"] is False
    assert doc["section"]["d"] is True
    assert doc["section"]["f"] == ["a", "b"]
    assert doc["section"]["e"] == {"a": "1", "b": "2"}
    assert doc["nested"]["section"]["value"] == "string"
