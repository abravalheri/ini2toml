import logging

import pytest

from ini2toml.plugins import profile_independent_tasks as tasks
from ini2toml.plugins.setuptools_pep621 import SetuptoolsPEP621, activate, isdirective
from ini2toml.translator import Translator


@pytest.fixture
def plugin():
    return SetuptoolsPEP621()


@pytest.fixture
def translator(plugin):
    return Translator(plugins=[activate])


@pytest.fixture
def parse(translator):
    return lambda text: translator.loads(text)


@pytest.fixture
def convert(translator):
    return lambda irepr: translator.dumps(irepr)


example_normalise_keys = """\
[metadata]
summary = Automatically translates .cfg/.ini files into TOML
author_email = example@example
license-file = LICENSE.txt
long_description_content_type = text/x-rst; charset=UTF-8
home_page = https://github.com/abravalheri/ini2toml/
classifier = Development Status :: 4 - Beta
platform = any
"""
expected_normalise_keys = """\
[metadata]
description = "Automatically translates .cfg/.ini files into TOML"
author-email = "example@example"
license-files = "LICENSE.txt"
long-description-content-type = "text/x-rst; charset=UTF-8"
url = "https://github.com/abravalheri/ini2toml/"
classifiers = "Development Status :: 4 - Beta"
platforms = "any"
"""


def test_normalise_keys(plugin, parse, convert):
    obj = parse(example_normalise_keys)
    obj = plugin.normalise_keys(obj)
    assert convert(obj) == expected_normalise_keys


# ----


example_convert_directives = """\
[metadata]
version = attr: mymodule.myfunc
classifiers = file: CLASSIFIERS.txt
description = file: README.txt

[options]
entry-points = file: ENTRYPOINTS.txt
packages = find_namespace:
"""
expected_convert_directives = """\
[metadata]
version = {attr = "mymodule.myfunc"}
classifiers = {file = "CLASSIFIERS.txt"}
description = {file = "README.txt"}

[options]
entry-points = {file = "ENTRYPOINTS.txt"}
packages = {find_namespace = ""}
"""


def test_convert_directives(plugin, parse, convert):
    doc = parse(example_convert_directives)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.convert_directives(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc) == expected_convert_directives


# ----


example_apply_value_processing = """\
[metadata]
version = 5.3  # comment
classifiers =
    Development Status :: 4 - Beta
    Programming Language :: Python
keywords = python, module
[options]
zip-safe = False  # comment
package-dir =
    *=src # TODO: tomlkit/atoml bug with empty keys
install-requires =
    importlib-metadata; python_version<"3.8"
    configupdater>=3,<=4
[options.entry-points]
# For example:
console-scripts =
    putup = pyscaffold.cli:run  # CLI exec
pyscaffold.cli =
    # comment
    fibonacci = ini2toml.skeleton:run # comment
    awesome = pyscaffoldext.awesome.extension:AwesomeExtension
"""
expected_apply_value_processing = """\
[metadata]
version = "5.3" # comment
classifiers = [
    "Development Status :: 4 - Beta",
    "Programming Language :: Python",
]
keywords = ["python", "module"]

[options]
zip-safe = false # comment
package-dir = {"*" = "src"} # TODO: tomlkit/atoml bug with empty keys
install-requires = [
    "importlib-metadata; python_version<\\"3.8\\"",
    "configupdater>=3,<=4",
]

["project:entry-points"]
# For example:

["project:entry-points"."pyscaffold.cli"]
# comment
fibonacci = "ini2toml.skeleton:run" # comment
awesome = "pyscaffoldext.awesome.extension:AwesomeExtension"

["project:scripts"]
putup = "pyscaffold.cli:run" # CLI exec
"""


def test_move_entry_points_and_apply_value_processing(plugin, parse, convert):
    doc = parse(example_apply_value_processing)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.move_and_split_entrypoints(doc)
    doc = plugin.apply_value_processing(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    text = tasks.remove_trailing_spaces(convert(doc)).strip()
    assert text == expected_apply_value_processing.strip()


# ----

example_separate_subtables = """\
[options.packages.find]
where = src
[project:entry-points]
# For example:
[project:scripts]
django-admin = django.core.management:execute_from_command_line
"""

expected_separate_subtables = """\
[tool]
[tool.setuptools]
[tool.setuptools.packages]
[tool.setuptools.packages.find]
where = "src"

[project]
[project.entry-points]
# For example:

[project.scripts]
django-admin = "django.core.management:execute_from_command_line"
"""


def test_split_subtables(plugin, parse, convert):
    doc = parse(example_separate_subtables.strip())
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.split_subtables(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_separate_subtables.strip()


# ----

example_entrypoints_and_split_subtables = """\
[options.packages.find]
where = src
[options.entry-points]
# For example:
console-scripts =
    django-admin = django.core.management:execute_from_command_line
gui-scripts =
    project = my.module:function [extra-dep]
pyscaffold.cli =
    config = pyscaffold.extensions.config:Config
    interactive = pyscaffold.extensions.interactive:Interactive
"""

expected_entrypoints_and_split_subtables = """\
[tool]
[tool.setuptools]
[tool.setuptools.packages]
[tool.setuptools.packages.find]
where = "src"

[project]
[project.entry-points]
# For example:

[project.entry-points."pyscaffold.cli"]
config = "pyscaffold.extensions.config:Config"
interactive = "pyscaffold.extensions.interactive:Interactive"

[project.scripts]
django-admin = "django.core.management:execute_from_command_line"

[project.gui-scripts]
project = "my.module:function [extra-dep]"
"""


def test_entrypoints_and_split_subtables(plugin, parse, convert):
    doc = parse(example_entrypoints_and_split_subtables.strip())
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.move_and_split_entrypoints(doc)
    doc = plugin.apply_value_processing(doc)
    doc = plugin.split_subtables(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_entrypoints_and_split_subtables.strip()


# ----


example_fix_license = """\
[metadata]
license = MPL-2.0
license-files = LICENSE.txt
"""

expected_fix_license = """\
[metadata]
[metadata.license]
file = "LICENSE.txt"
"""


def test_merge_license_and_files(plugin, parse, convert):
    doc = parse(example_fix_license.strip())
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.merge_license_and_files(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_fix_license.strip()


# ----


example_fix_packages = """\
[options]
packages = find-namespace:
[options.packages.find]
where = src
exclude =
    tests
"""

expected_fix_packages = """\
[options]

["options.packages.find-namespace"]
where = "src"
exclude = ["tests"]
"""


def test_fix_packages(plugin, parse, convert):
    doc = parse(example_fix_packages.strip())
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.fix_packages(doc)
    doc = plugin.apply_value_processing(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_fix_packages.strip()


# ----


example_fix_setup_requires = """\
[options]
setup-requires =
    setuptools>=46.1.0
    setuptools_scm>=5
"""

expected_fix_setup_requires = """\
[build-system]
requires = [
    "setuptools>=46.1.0",
    "setuptools_scm>=5",
    "wheel",
]
build-backend = "setuptools.build_meta"
"""


def test_fix_setup_requires(plugin, parse, convert):
    doc = plugin.template()
    doc.update(parse(example_fix_setup_requires.strip()))
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.fix_setup_requires(doc)
    doc = plugin.apply_value_processing(doc)
    doc = plugin.move_setup_requires(doc)
    doc.pop("tool", None)
    doc.pop("options", None)
    doc.pop("metadata", None)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    text = tasks.remove_trailing_spaces(convert(doc)).strip()
    assert text == expected_fix_setup_requires.strip()


example_dynamic = """\
[metadata]
version = attr: django.__version__
classifiers = file: classifiers.txt
description = file: readme.txt

[options]
entry-points = file: entry-points.txt
"""

expected_dynamic = """\
[metadata]

dynamic = [
    "version",
    "classifiers",
    "description",
    "entry-points",
    "scripts",
    "gui-scripts",
]

["options.dynamic"]
version = {attr = "django.__version__"}
classifiers = {file = "classifiers.txt"}
description = {file = "readme.txt"}
entry-points = {file = "entry-points.txt"}
"""  # noqa


def test_isdirective(plugin, parse, convert):
    doc = parse(example_dynamic.strip())
    assert isdirective(doc["metadata"]["version"], ("attr",))
    assert isdirective(doc["metadata"]["classifiers"])
    assert isdirective(doc["metadata"]["description"], ("file",))
    assert isdirective(doc["options"]["entry-points"])
    assert not isdirective("")
    assert not isdirective("some value")


def test_fix_dynamic(plugin, parse, convert):
    doc = parse(example_dynamic.strip())
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.fix_dynamic(doc)
    doc.pop("tool", None)
    doc.pop("options", None)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_dynamic.strip()


# ----

expected_empty = """\
[project]
dynamic = ["version"]

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[tool]
[tool.setuptools]
"""


def test_empty(translator, plugin, parse, convert):
    doc = parse("")
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.normalise_keys(doc)
    doc = plugin.pep621_transform(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_empty.strip()

    # Same thing but with the higher level API:
    text = translator.translate("", profile_name="setup.cfg")
    assert text.strip() == expected_empty.strip()


# ----
example_data_files = """
[options]
data-files =
    a = b
"""

expected_data_files = """\
[project]
dynamic = ["version"]

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[tool]
[tool.setuptools]
data-files = {a = ["b"]}
"""


def test_data_files(translator, caplog):
    # Same thing but with the higher level API:
    with caplog.at_level(logging.DEBUG):
        text = translator.translate(example_data_files, profile_name="setup.cfg")
        assert text.strip() == expected_data_files.strip()

    assert "'data-files' is deprecated" in caplog.text
