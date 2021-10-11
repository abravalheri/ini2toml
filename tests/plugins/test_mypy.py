from textwrap import dedent

import tomli

from ini2toml.drivers import full_toml, lite_toml
from ini2toml.plugins import mypy
from ini2toml.translator import Translator


def test_mypy():
    example = """\
    [mypy]
    python_version = 2.7
    warn_return_any = True
    warn_unused_configs = True
    plugins = mypy_django_plugin.main, returns.contrib.mypy.returns_plugin
    [mypy-mycode.foo.*]
    disallow_untyped_defs = True
    [mypy-mycode.bar]
    warn_return_any = False
    [mypy-somelibrary,some_other_library]
    ignore_missing_imports = True
    """
    expected = """\
    [mypy]
    python_version = "2.7"
    warn_return_any = true
    warn_unused_configs = true
    plugins = ["mypy_django_plugin.main", "returns.contrib.mypy.returns_plugin"]

    [[mypy.overrides]]
    module = ["mycode.foo.*"]
    disallow_untyped_defs = true

    [[mypy.overrides]]
    module = ["mycode.bar"]
    warn_return_any = false

    [[mypy.overrides]]
    module = ["somelibrary", "some_other_library"]
    ignore_missing_imports = true
    """
    for convert in (lite_toml.convert, full_toml.convert):
        translator = Translator(plugins=[mypy.activate], toml_dumps_fn=convert)
        out = translator.translate(dedent(example), "mypy.ini").strip()
        expected = dedent(expected).strip()
        print("expected=\n" + expected + "\n***")
        print("out=\n" + out)
        try:
            assert expected == out
        except AssertionError:
            # At least the Python-equivalents when parsing should be the same
            assert tomli.loads(expected) == tomli.loads(out)
