from ini2toml.drivers import full_toml as lib
from ini2toml.types import Commented, CommentedKV, CommentedList, CommentKey
from ini2toml.types import IntermediateRepr as IR
from ini2toml.types import WhitespaceKey

example_toml = """\
[section1]
# comment
value = 42 # int value

[section2]
float-value = 1.5
boolean-value = false
"other value" = [
    1, 2, 3, # 1st line comment
    # 2nd line comment
]
other-boolean-value = true

# comment between options
string-value = "string" # comment
list-value = [true, false]

[section2."another value"]
a = 1
b = 2 # 1st line comment
c = 3
d = 4 # 2nd line comment

[section3]
[section3.nested]
x = "y"
z = "w" # nested
"""


example_parsed = IR(
    section1=IR({CommentKey(): "comment", "value": Commented(42, "int value")}),
    section2=IR(
        {
            "float-value": 1.5,
            "boolean-value": False,
            "other value": CommentedList(
                [
                    Commented([1, 2, 3], "1st line comment"),
                    Commented(comment="2nd line comment"),
                ]
            ),
            "other-boolean-value": True,
            WhitespaceKey(): "",
            CommentKey(): "comment between options",
            "another value": CommentedKV(
                [
                    Commented([("a", 1), ("b", 2)], "1st line comment"),
                    Commented([("c", 3), ("d", 4)], "2nd line comment"),
                ]
            ),
            "string-value": Commented("string", "comment"),
            "list-value": [True, False],
        }
    ),
    section3=IR(nested=IR(x="y", z=Commented("w", "nested"))),
)


def test_convert():
    assert lib.convert(example_parsed) == example_toml
