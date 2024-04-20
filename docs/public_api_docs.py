import shutil
from pathlib import Path

TOC_TEMPLATE = """
Module Reference
================

The public API of ``ini2toml`` is mainly composed by ``ini2toml.api``.
Users may also find useful to import ``ini2toml.errors`` and
``ini2toml.types`` when handling exceptions or specifying type hints.

Plugin developers might try to use ``ini2toml.transformations``,
but they should take the stability of that module with a grain of salt...

.. toctree::
   :glob:
   :maxdepth: 2

   ini2toml.api
   ini2toml.errors
   ini2toml.types

.. toctree::
   :maxdepth: 1

   ini2toml.transformations

.. toctree::
   :caption: Plugins
   :glob:
   :maxdepth: 1

   plugins/*
"""

MODULE_TEMPLATE = """
``{name}``
~~{underline}~~

.. automodule:: {name}
   :members:{_members}
   :undoc-members:
   :show-inheritance:
"""


def gen_stubs(module_dir: str, output_dir: str):
    try_rmtree(output_dir)  # Always start fresh
    Path(output_dir, "plugins").mkdir(parents=True, exist_ok=True)
    for module in iter_public():
        text = module_template(module)
        Path(output_dir, f"{module}.rst").write_text(text, encoding="utf-8")
    for module in iter_plugins(module_dir):
        text = module_template(module, "activate")
        Path(output_dir, f"plugins/{module}.rst").write_text(text, encoding="utf-8")
    Path(output_dir, "modules.rst").write_text(TOC_TEMPLATE, encoding="utf-8")


def iter_public():
    lines = (x.strip() for x in TOC_TEMPLATE.splitlines())
    return (x for x in lines if x.startswith("ini2toml."))


def iter_plugins(module_dir: str):
    return (
        f'ini2toml.plugins.{path.with_suffix("").name}'
        for path in Path(module_dir, "plugins").iterdir()
        if path.is_file()
        and path.name not in {".", "..", "__init__.py"}
        and not path.name.startswith("_")
    )


def try_rmtree(target_dir: str):
    try:
        shutil.rmtree(target_dir)
    except FileNotFoundError:
        pass


def module_template(name: str, *members: str) -> str:
    underline = "~" * len(name)
    _members = (" " + ", ".join(members)) if members else ""
    return MODULE_TEMPLATE.format(name=name, underline=underline, _members=_members)
