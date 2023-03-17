import logging

import pytest

from ini2toml.drivers import configparser, configupdater
from ini2toml.plugins import toml_incompatibilities as plugin
from ini2toml.translator import Translator

EXAMPLE_FLAKE8 = """
[flake8]
# Some sane defaults for the code style checker flake8
# black compatibility
max_line_length = 88
# E203 and W503 have edge cases handled by black
extend_ignore = E203, W503
exclude =
    src/pyscaffold/contrib
    .tox
    build
    dist
    .eggs
    docs/conf.py
"""

EXAMPLE_DEVPI = """
[devpi:upload]
# Options for the devpi: PyPI server and packaging tool
# VCS export must be deactivated since we are using setuptools-scm
no_vcs = 1
formats = bdist_wheel
"""

EXAMPLES = {
    "flake8": (".flake8", "flake8", EXAMPLE_FLAKE8),
    "flake8-setup.cfg": ("setup.cfg", "flake8", EXAMPLE_FLAKE8),
    "devpi-setup.cfg": ("setup.cfg", "devpi:upload", EXAMPLE_DEVPI),
}


@pytest.mark.parametrize("example", EXAMPLES.keys())
@pytest.mark.parametrize("convert", (configparser.parse, configupdater.parse))
def test_log_warnings(example, convert, caplog):
    """ini2toml should display a warning via the logging system"""
    profile, section, content = EXAMPLES[example]
    translator = Translator(plugins=[plugin.activate], ini_loads_fn=convert)
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        translator.translate(content, profile)
    expected = plugin._warning_text(profile, repr(section))
    assert expected in caplog.text
