# The code in this file is mostly borrowed/adapted from PyScaffold and was originally
# published under the MIT license.
# The original PyScaffold license can be found in 'tests/examples/pyscaffold'


import pytest

from ini2toml import plugins
from ini2toml.plugins import ENTRYPOINT_GROUP, EntryPoint, ErrorLoadingPlugin

EXISTING = (
    "setuptools_pep621",
    "best_effort",
    "isort",
    "coverage",
    "pytest",
    "mypy",
    "independent_tasks",
)


def test_load_from_entry_point__error():
    # This module does not exist, so Python will have some trouble loading it
    # EntryPoint(name, value, group)
    entry = "mypkg.SOOOOO___fake___:activate"
    fake = EntryPoint("fake", entry, ENTRYPOINT_GROUP)
    with pytest.raises(ErrorLoadingPlugin):
        plugins.load_from_entry_point(fake)


def test_iterate_entry_points():
    plugin_iter = plugins.iterate_entry_points()
    assert hasattr(plugin_iter, "__iter__")
    pluging_list = list(plugin_iter)
    assert all([isinstance(e, EntryPoint) for e in pluging_list])
    name_list = [e.name for e in pluging_list]
    for ext in EXISTING:
        assert ext in name_list


def test_list_from_entry_points():
    # Should return a list with all the plugins registered in the entrypoints
    pluging_list = plugins.list_from_entry_points()
    orig_len = len(pluging_list)
    assert all(callable(e) for e in pluging_list)
    plugin_names = " ".join(str(e.__module__) for e in pluging_list)
    for example in EXISTING:
        assert example in plugin_names

    # a filtering function can be passed to avoid loading plugins that are not needed
    pluging_list = plugins.list_from_entry_points(filtering=lambda e: e.name != "isort")
    plugin_names = " ".join(str(e.__module__) for e in pluging_list)
    assert len(pluging_list) == orig_len - 1
    assert "isort" not in plugin_names
