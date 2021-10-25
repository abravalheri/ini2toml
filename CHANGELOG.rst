=========
Changelog
=========

Version 0.0.3
=============

- Add validation tests via :pypi:`validate-pyproject`.
- Move ``setuptools.scripts`` to ``setuptools.script-files`` to avoid confusion
  with the ``scripts`` field defined in :pep:`621`.
- Separate ``Translator`` and ``BaseTranslator`` classes.
  This allows API users to call ``BaseTranslator`` directly with explicit
  arguments and bypass the autodiscovery of drivers and plugins
  (therefore reducing the amount of dependencies and files necessary when
  *"vendorising"* ``ini2toml``).
- The type signature of ``BaseTranslator`` was made more flexible to allow
  returning a :class:`dict` representing the TOML instead of a string.
- Add a ``plain_builtins`` driver.
  The objective of this change is allowing the removal of the dependency on
  :pypi:`atoml` or :pypi:`tomli-w` when using ``ini2toml`` as API only.
- Improve the choice of ``InlineTable`` vs. ``Table`` for the generated TOML
  when using the ``full_toml`` adapter.
- Improve heuristic to remove superfluous empty tables in the generated TOML string.
- ``distutils.commands``-related sections in ``setup.cfg`` are now better
  recognised and transfered to the ``tool.distutils`` table in the generated
  TOML (previously they were placed under ``tool.setuptools.commands``).
  The normalisation of the command names using ``kebab-case`` is no longer
  performed.
- Prevent empty ``entry-points`` field to be kept in the TOML when separating
  ``scripts`` and ``gui-scripts``.
- ``version`` is now automatically added to ``dynamic`` if not provided.
- Fix ``find:`` directive to match :pypi:`validate-pyproject`.
  Previously ``{find = ""}`` was generated, which now is converted to ``{find = {}}``.
- Add new helpers to the ``transformations`` library: ``deprecated`` and ``pipe``.
- Add new test derived from :pypi:`setuptools`'s docs directly.

Version 0.0.2
=============

- Small improvements
- Documentation updates
- Fix virtualenv test example.

Version 0.0.1
=============

- Initial release with basic functionalities
