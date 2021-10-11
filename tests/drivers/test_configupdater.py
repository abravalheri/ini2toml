from ini2toml.drivers import configupdater as lib
from ini2toml.types import CommentKey
from ini2toml.types import IntermediateRepr as IR
from ini2toml.types import WhitespaceKey

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
        "section1": IR(
            {CommentKey(): "comment", "value": "42 # int value", WhitespaceKey(): "\n"}
        ),
        "section2": IR(
            {
                "float-value": "1.5",
                "boolean-value": "false",
                "other value": "\n1, 2, 3, # 1st line comment\n# 2nd line comment",
                "other-boolean-value": "true",
                WhitespaceKey(): "\n",
                CommentKey(): "comment between options",
                "string-value": "string # comment",
                WhitespaceKey(): "\n",
            }
        ),
        "section2.another value": IR(
            a="1", b="2 # 1st line comment", c="3", d="4 # 2nd line comment"
        ),
    }
)


def test_parse():
    assert lib.parse(example_cfg.strip(), {}) == example_parsed
