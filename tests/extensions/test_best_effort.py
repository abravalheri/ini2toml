from textwrap import dedent

import pytest

from cfg2toml.extensions import best_effort
from cfg2toml.toml_adapter import loads
from cfg2toml.translator import Translator


@pytest.fixture
def translate():
    translator = Translator(extensions=[best_effort.activate])
    return lambda text: translator.translate(text, "best_effort")


@pytest.fixture
def cfg2tomlobj(translate):
    return lambda text: loads(translate(text))


def test_best_effort(cfg2tomlobj):
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
    doc = cfg2tomlobj(dedent(example))
    assert doc["section"]["a"] == 1
    assert doc["section"]["b"] == 0.42
    assert doc["section"]["c"] is False
    assert doc["section"]["d"] is True
    assert doc["section"]["f"] == ["a", "b"]
    assert doc["section"]["e"] == {"a": "1", "b": "2"}
    assert doc["nested"]["section"]["value"] == "string"
