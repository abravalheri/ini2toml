from ini2toml.drivers import plain_builtins as lib
from ini2toml.types import Commented, CommentedKV, CommentedList, CommentKey
from ini2toml.types import IntermediateRepr as IR
from ini2toml.types import WhitespaceKey

example_output = {
    "section1": {"value": 42},
    "section2": {
        "float-value": 1.5,
        "boolean-value": False,
        "other value": [1, 2, 3],
        "other-boolean-value": True,
        "string-value": "string",
        "list-value": [True, False],
        "another value": {"a": 1, "b": 2, "c": 3, "d": 4},
    },
    "section3": {"nested": {"x": "y", "z": "w"}},
}


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
    assert lib.convert(example_parsed) == example_output
