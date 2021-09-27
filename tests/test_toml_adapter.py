from textwrap import dedent

import pytest

from cfg2toml.toml_adapter import comment, document, dumps, loads, table


class TestUnderstandTomlLib:
    """This is kind of a meta test to make sure the underlying library works
    as we expect.
    """

    def test_opening_comment_without_nl_after(self):
        doc = document()
        doc.add(comment("opening comment"))
        doc["value"] = 42
        out = dumps(doc)
        expected = """\
        # opening comment
        value = 42
        """
        assert out == dedent(expected)

    def test_table_adds_nl_before(self):
        doc = document()
        doc["value"] = 42
        doc["table"] = table()
        out = dumps(doc)
        expected = """\
        value = 42

        [table]
        """
        assert out == dedent(expected)

    def test_opening_comment_with_table(self):
        doc = document()
        doc.add(comment("opening comment"))
        doc["table"] = table()
        out = dumps(doc)
        expected = """\
        # opening comment

        [table]
        """
        assert out == dedent(expected)

    def test_empty_key(self):
        text = dumps({"": "src"})
        try:
            assert text.strip() == '"" = "src"'
            assert loads(text) == {"": "src"}
            pytest.fail("Error fixed in upstream library, please update the code")
        except Exception as ex:
            pytest.skip(f"Known error with upstream library: {ex}")

    def test_renaming_table(self):
        example = """\
        [x]
        a = 3 # comment
        """
        doc = loads(dedent(example))
        doc["y"] = doc.pop("x")
        try:
            assert "y" in doc
            text = dumps(doc)
            assert "[y]" in text
            assert "[x]" not in text
            pytest.fail("Error fixed in upstream library, please update the code")
        except Exception as ex:
            pytest.skip(f"Known error with upstream library: {ex}")

    def test_replacing_simple_item_with_table(self):
        example = """\
        [a]
        x = 1 # comment
        y = 2
        z = 3
        """
        doc = loads(dedent(example))
        doc["a"]["y"] = {"nested": 1}
        try:
            changeddoc = loads(dumps(doc))
            assert "x" in changeddoc["a"]
            assert "y" in changeddoc["a"]
            assert "nested" in changeddoc["a"]["y"]
            assert "z" in changeddoc["a"]
            pytest.fail("Error fixed in upstream library, please update the code")
        except Exception as ex:
            pytest.skip(f"Known error with upstream library: {ex}")

    def test_multiline_array_of_objects(self):
        example = """\
        [a]
        x = [
        ]
        y = 0
        """
        doc = loads(dedent(example))
        doc["a"]["x"].append({"name": "John Doe", "email": "john@doe.com"})
        text = dumps(doc)
        print(text)
        try:
            changeddoc = loads(text)
            assert changeddoc["a"]["x"][0]["name"] == "John Doe"
            assert changeddoc["a"]["x"][0]["email"] == "john@doe.com"
            assert changeddoc["a"]["y"] == 0
            pytest.fail("Error fixed in upstream library, please update the code")
        except Exception as ex:
            pytest.skip(f"Known error with upstream library: {ex}")
