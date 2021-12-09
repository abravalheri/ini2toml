import pytest

from ini2toml.plugins.setuptools_pep621 import Directive, SetuptoolsPEP621, activate
from ini2toml.translator import Translator


@pytest.fixture
def plugin():
    return SetuptoolsPEP621()


@pytest.fixture
def translator(plugin):
    return Translator(plugins=[activate], ini_parser_opts=dict(delimiters=("=", ": ")))


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
    with pytest.warns(DeprecationWarning):
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
classifiers = {file = ["CLASSIFIERS.txt"]}
description = {file = ["README.txt"]}

[options]
entry-points = {file = ["ENTRYPOINTS.txt"]}
packages = {find_namespace = ""}
"""


def test_convert_directives(plugin, parse, convert):
    doc = parse(example_convert_directives)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.apply_value_processing(doc)
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
cmdclass =
    customcmd = custom_build.CustomCmd
    other = custom_build.OtherCmd  # Some command
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

[options.cmdclass]
customcmd = "custom_build.CustomCmd"
other = "custom_build.OtherCmd" # Some command

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
    doc = plugin.apply_value_processing(doc)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.move_and_split_entrypoints(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    text = convert(doc).strip()
    assert text == expected_apply_value_processing.strip()


# ----

example_split_subtables = """\
[options.packages.find]
where = src
[project:entry-points]
# For example:
[project:scripts]
django-admin = django.core.management:execute_from_command_line
"""

expected_split_subtables = """\
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
    doc = parse(example_split_subtables.strip())
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.split_subtables(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_split_subtables.strip()


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
    doc = plugin.apply_value_processing(doc)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.move_and_split_entrypoints(doc)
    doc = plugin.split_subtables(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_entrypoints_and_split_subtables.strip()


# ----


example_handle_license_files = """\
[metadata]
license-files = LICENSE.txt
"""

expected_handle_license_files = """\
[metadata]
[metadata.license]
file = "LICENSE.txt"
"""


def test_handle_license_files(plugin, parse, convert):
    doc = parse(example_handle_license_files.strip())
    doc = plugin.apply_value_processing(doc)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.handle_license_and_files(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_handle_license_files.strip()


example_handle_multiple_license_files = """\
[metadata]
license-files = LICENSE.txt, NOTICE.txt
"""

expected_handle_multiple_license_files = """\
[metadata]
dynamic = ["license"]

["options.dynamic"]
license-files = ["LICENSE.txt", "NOTICE.txt"]
"""


def test_handle_multiple_license_files(plugin, parse, convert):
    doc = parse(example_handle_multiple_license_files.strip())
    doc = plugin.apply_value_processing(doc)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.handle_license_and_files(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_handle_multiple_license_files.strip()


example_handle_license = """\
[metadata]
license = MPL-2.0
"""

expected_handle_license = """\
[metadata]
[metadata.license]
text = "MPL-2.0"
"""


def test_handle_license(plugin, parse, convert):
    doc = parse(example_handle_license.strip())
    doc = plugin.apply_value_processing(doc)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.handle_license_and_files(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_handle_license.strip()


example_handle_license_and_files = """\
[metadata]
license = MPL-2.0
license-files = LICENSE.txt
"""

expected_handle_license_and_files = """\
[metadata]
dynamic = ["license"]

["options.dynamic"]
license = "MPL-2.0"
license-files = ["LICENSE.txt"]
"""


def test_handle_license_and_files(plugin, parse, convert):
    doc = parse(example_handle_license_and_files.strip())
    doc = plugin.apply_value_processing(doc)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.handle_license_and_files(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_handle_license_and_files.strip()


# ----


example_handle_packages_find = """\
[options]
packages = find_namespace:
[options.packages.find]
where = src
exclude =
    tests
"""

expected_handle_packages_find = """\
[options]

["options.packages.find"]
where = ["src"]
exclude = ["tests"]
namespaces = true
"""


def test_handle_packages_find(plugin, parse, convert):
    doc = parse(example_handle_packages_find.strip())
    doc = plugin.apply_value_processing(doc)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.handle_packages_find(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    assert convert(doc).strip() == expected_handle_packages_find.strip()


# ----

example_fix_extras_require = """\
[options.extras-require]
pyarrow:python_version>'3.4' =
    pyarray>=1.0.0,<2.0dev; os_name=='posix'
    colorama; os_name=='nt'
"""

expected_fix_extras_require = """\
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

["project:optional-dependencies"]
pyarrow = [
    "pyarray>=1.0.0,<2.0dev; os_name=='posix' and python_version>'3.4'",
    "colorama; os_name=='nt' and python_version>'3.4'",
]
"""


def test_fix_extras_require(plugin, parse, convert):
    doc = plugin.template()
    doc.update(parse(example_fix_extras_require.strip()))
    doc = plugin.apply_value_processing(doc)
    doc = plugin.move_options_missing_in_pep621(doc)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.fix_extras_require(doc)
    doc.pop("tool", None)
    doc.pop("options", None)
    doc.pop("metadata", None)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    text = convert(doc).strip()
    assert text == expected_fix_extras_require.strip()


# ----


example_move_setup_requires = """\
[options]
setup-requires =
    setuptools>=46.1.0
    setuptools_scm>=5
"""

expected_move_setup_requires = """\
[build-system]
requires = [
    "wheel",
    "setuptools>=46.1.0",
    "setuptools_scm>=5",
]
build-backend = "setuptools.build_meta"
"""


def test_move_setup_requires(plugin, parse, convert):
    doc = plugin.template()
    doc.update(parse(example_move_setup_requires.strip()))
    doc = plugin.apply_value_processing(doc)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    with pytest.warns(DeprecationWarning, match="'setup_requires' is deprecated"):
        doc = plugin.move_setup_requires(doc)
    doc.pop("tool", None)
    doc.pop("options", None)
    doc.pop("metadata", None)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    print(doc)
    text = convert(doc).strip()
    assert text == expected_move_setup_requires.strip()


# ----


example_move_tests_require1 = """\
[options]
tests-require =
    pytest
    pytest-cov
"""

expected_move_tests_require1 = """\
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

["project:optional-dependencies"]
testing = [
    "pytest",
    "pytest-cov",
]
"""

example_move_tests_require2 = """\
[options]
tests-require =
    pytest
    pytest-cov

[options.extras-require]
testing =
    pytest>=6.2.5
"""

expected_move_tests_require2 = """\
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

["project:optional-dependencies"]
testing = [
    "pytest>=6.2.5",
    "pytest-cov",
]
"""


def test_move_tests_require(plugin, parse, convert):
    for example, expected in [
        (example_move_tests_require1, expected_move_tests_require1),
        (example_move_tests_require2, expected_move_tests_require2),
    ]:
        doc = plugin.template()
        doc.update(parse(example.strip()))
        doc = plugin.apply_value_processing(doc)
        doc = plugin.move_options_missing_in_pep621(doc)
        print(doc)
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        with pytest.warns(DeprecationWarning, match="'tests_require' is deprecated"):
            doc = plugin.move_tests_require(doc)
        doc.pop("tool", None)
        doc.pop("options", None)
        doc.pop("metadata", None)
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        print(doc)
        text = convert(doc).strip()
        assert text == expected.strip()


# ----


example_dynamic = """\
[metadata]
version = attr: django.__version__
classifiers = file: classifiers.txt
description = file: readme.txt
long-description = file: readme.txt, desc.txt
long-description-content-type: plain/text

[options]
entry-points = file: entry-points.txt
"""

expected_dynamic = """\
[metadata]

dynamic = [
    "readme",
    "version",
    "classifiers",
    "description",
    "entry-points",
    "scripts",
    "gui-scripts",
]

["options.dynamic"]
readme = {file = ["readme.txt", "desc.txt"], content-type = "plain/text"}
version = {attr = "django.__version__"}
classifiers = {file = ["classifiers.txt"]}
description = {file = ["readme.txt"]}
entry-points = {file = ["entry-points.txt"]}
"""  # noqa


def test_directives(plugin, parse, convert):
    doc = parse(example_dynamic.strip())
    doc = plugin.apply_value_processing(doc)
    assert isinstance(doc["metadata"]["version"], Directive)
    assert doc["metadata"]["version"].kind == "attr"

    assert isinstance(doc["metadata"]["classifiers"], Directive)

    assert isinstance(doc["metadata"]["description"], Directive)
    assert doc["metadata"]["description"].kind == "file"

    assert isinstance(doc["options"]["entry-points"], Directive)


def test_handle_dynamic(plugin, parse, convert):
    doc = parse(example_dynamic.strip())
    doc = plugin.apply_value_processing(doc)
    doc = plugin.merge_and_rename_long_description_and_content_type(doc)
    print(doc)
    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    doc = plugin.handle_dynamic(doc)
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
include-package-data = false
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
include-package-data = false
"""


def test_data_files(translator):
    # Same thing but with the higher level API:
    with pytest.warns(DeprecationWarning, match="'data-files' is deprecated"):
        text = translator.translate(example_data_files, profile_name="setup.cfg")
        assert text.strip() == expected_data_files.strip()
