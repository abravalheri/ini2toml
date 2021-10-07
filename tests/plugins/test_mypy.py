from textwrap import dedent

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
    [tool]
    [tool.mypy]
    python_version = "2.7"
    warn_return_any = true
    warn_unused_configs = true
    plugins = ["mypy_django_plugin.main", "returns.contrib.mypy.returns_plugin"]

    [[tool.mypy.overrides]]
    disallow_untyped_defs = true
    module = ["mycode.foo.*"]

    [[tool.mypy.overrides]]
    warn_return_any = false
    module = ["mycode.bar"]

    [[tool.mypy.overrides]]
    ignore_missing_imports = true
    module = ["somelibrary", "some_other_library"]
    """
    translator = Translator(plugins=[mypy.activate])
    out = translator.translate(dedent(example), "mypy.ini").strip()
    expected = dedent(expected).strip()
    print("expected=\n" + expected + "\n***")
    print("out=\n" + out)
    assert expected == out
