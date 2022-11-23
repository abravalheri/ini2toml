=========
Changelog
=========

Version 0.11.3
==============

* Fix dependency problems by requiring ``pyproject-fmt>=0.4.0``

Version 0.11.2
==============

* Adapt to changes in ``pyproject-fmt`` 0.4.0

Version 0.11.1
==============

* Internal test fixes, minor CI and doc improvements
* Only list ``pyproject-fmt`` as an experimental dependency on Python 3.7+

Version 0.11
============

* ``setuptools`` plugin:
   * Add minimum version of ``setuptools`` implementing :pep:`621` to ``[build-system] requires``, :pr:`42`

Version 0.10
============

* ``setuptools`` plugin:
   * Separate the handling of ``license-files`` and PEP 621 metadata, #34
   * ``license`` and ``license-files`` are no longer added to ``tool.setuptools.dynamic``.
      Instead ``license-files`` is added directly to ``tool.setuptools``, and the ``license`` should be added as ``project.license.text``.

Version 0.9
===========

- Fixed missing terminating newline at the end of the generated file, :pr:`27`, :pr:`32`
- Added heuristic for appropriate string representation selection when
  serialising TOML, :pr:`28`
- [CI] Added GitHub Actions for automatic test and release of tags, :pr:`30`

Version 0.8
===========

- :pypi:`atoml` dependency replaced with :pypi:`tomlkit`, :issue:`23`
- ``setuptools`` plugin:
    - Now commas are stripped when splitting keywords for setuptools plugin, :issue:`24`

Version 0.7
===========

- Avoid problems with duplicated augmentation, :pr:`20`
- Make sure each plugin is activated only once, :pr:`21`
- Improve TOML formatting, :pr:`22`
- ``setuptools`` plugin:
   - Make ``build-system`` the first section in the created ``pyproject.toml``,
     :pr:`19`

Version 0.6.1
=============

- ``setuptools`` plugin:
   - Fix dependency splitter for single lines with env markers

Version 0.6
===========

- ``isort`` plugin:
   - Fixed wrong comparison of whitespace and comments with field names
- ``setuptools`` plugin:
   - Explicitly added the default license globs as considered by
     setuptools/wheels (previously the :pep:`621` guarantees about backfilling
     dynamic fields could not be respected).

Version 0.5.2
=============

- ``setuptools`` plugin:
   - Fixed bug that forced normalisation of option subsections
     even when the keys represent package names or file paths.
   - Fixed bug that prevented line continuations in the package requirements.
     ``setuptools`` seem to support this use case, and people use it to write
     markers in separated lines (possible with comments between them).
   - Fixed but that allowed an empty ``entry-points`` subtable to be left
     behind in the ``tool.setuptools`` table.
- Fixed bug that was replacing tables when a new subtable was being added
  and that new subtable could be written as an inline table

Version 0.5.1
=============

- ``setuptools`` plugin:
   - Fixed bug that was preventing ``entry-points`` to be automatically
     added to the ``project.dynamic`` array.

Version 0.5
===========

- ``setuptools`` plugin:
   - Added automatic "update" for deprecated ``tests-require`` key.
     This value associated with this option is now automatically transformed
     into a ``testing`` extras group in the ``optional-dependencies``.
   - Added automatic "expansion" of environment markers inside the extra key in
     optional-dependencies. According to :pep:`PEP 621 <621#dependencies-optional-dependencies>`
     (that points to the core metadata spec), the ``optional-dependencies`` keys
     must be valid Python identifiers (but ``setuptools`` historically seem to
     accept markers embedded with ``:`` after the extra name).
- Bumped the version of the :pypi:`atoml` dependency to 1.1.1.

Version 0.4
===========

- ``setuptools`` plugin:
   - **PROVISIONAL** - Added support for specifying ``license`` and ``license-files`` at the
     same time via ``dynamic`` (this is likely to be revised depending on :pep:`639`).
   - Added support for multiple files in ``long-description`` via ``dynamic``.

Version 0.3
===========

- Removed dependency on ``typing_extensions`` for Python <= 3.8
- Removed dependency on ``dataclasses`` for Python <= 3.6
- Removed dependency on ``importlib-metadata`` for Python <= 3.8,
  but only for minimal install
- ``setuptools`` plugin:
   - Added support for ``cmdclass``

Version 0.2
===========

- Improved support for writing inline dicts and inline AoTs in the generated TOML
- ``setuptools`` plugin:
   - Added ``data-files``  support (although this option is marked as deprecated).
   - Unified ``tool.setuptools.packages.find`` and ``tool.setuptools.packages.find-namespace``
     options by adding a new keyword ``namespaces``
   - ``tool.setuptools.packages.find.where`` is now associated with a list of directories
     (instead of a single value).
   - When not present in the original config file, ``include_package_data`` is
     explicitly added with the ``False`` value.
   - Fixed ``authors`` vs. ``maintainers`` mixing (now they are handled independently).
   - Added dynamic option for ``readme`` (e.g. when multiple license files are combined).
   - Reordered set of transformations (which includes making ``apply_value_processing`` the first one).
   - Improved directive handling.
   - Added deprecation warnings.

Version 0.1
===========

- Adopt ``atoml>=1.1.0`` as a dependency and stabilise the list conversion.

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
  recognised and transferred to the ``tool.distutils`` table in the generated
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
