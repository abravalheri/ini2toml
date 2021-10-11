from ini2toml.drivers import configparser as lib
from ini2toml.types import IntermediateRepr as IR

example_cfg = """\
[section1]
# comment
value = 42 # int value

[section2]
float-value = 1.5
boolean-value = false
other value =
    1, 2, 3, # 1st line comment
    # 2nd line comment
other-boolean-value = true

# comment between options
string-value = string # comment

[section2.another value]
a = 1
b = 2 # 1st line comment
c = 3
d = 4 # 2nd line comment
"""


example_parsed = IR(
    {
        "section1": IR(value="42 # int value"),
        "section2": IR(
            {
                "float-value": "1.5",
                "boolean-value": "false",
                "other value": "\n1, 2, 3, # 1st line comment",
                "other-boolean-value": "true",
                "string-value": "string # comment",
            }
        ),
        "section2.another value": IR(
            a="1", b="2 # 1st line comment", c="3", d="4 # 2nd line comment"
        ),
    }
)


def test_parse():
    assert lib.parse(example_cfg.strip(), {}) == example_parsed
