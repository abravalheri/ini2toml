======================
Setuptools and PEP 621
======================

In the Python software ecosystem packaging and distributing software have
historically been a difficult topic.
Nevertheless, the community has been served well by :pypi:`setuptools` as the *de facto*
standard for creating distributable Python software packages.

In recent years, however, other needs and opportunities fostered the emergence
of some alternatives.
During this packaging renaissance, :pep:`621` was proposed (and accepted)
to standardise package metadata/configuration done by developers, in a single
file format shared by all the packaging alternatives.
It makes use of a TOML_ file, ``pyproject.toml``, which is, unfortunately,
significantly different from `setuptools own configuration file`_,
``setup.cfg``, and therefore its adoption by :pypi:`setuptools` requires mapping
concepts between these two files.

:pep:`621` covers most of the information expected from a ``setup.cfg`` file,
but there are parameters specific to :pypi:`setuptools` without an obvious equivalent.
For the time being :pypi:`setuptools` documentation does not offer a clear way of
mapping those fields. As a result the (experimental) automatic translation
proposed by ``ini2toml`` takes the following assumptions:

- Any field without an obvious equivalent in :pep:`621` is stored in the
  ``[tool.setuptools]`` TOML table, regardless if it comes from the
  ``[metadata]`` or ``[options]`` sections in ``setup.cfg``.

- ``[options.*]`` sections in ``setup.cfg`` are translated to sub-tables of
  ``[tool.setuptools]`` in ``pyproject.toml``. For example::

    [options.package_data] => [tool.setuptools.package-data]

- Field and subtables in ``[tool.setuptools]`` have the ``_`` character
  replaced by ``-`` in their keys, to follow the conventions set in :pep:`517`
  and :pep:`621`.

- ``setup.cfg`` directives (e.g. fields starting with ``attr:`` or ``file:``)
  can be transformed into a (potentially inline) TOML table, for example::

    'file: description.rst' => {file = "description.rst"}

  Note, however, that these directives are not allowed to be used directly
  under the ``project`` table. Instead, ``ini2toml`` will rely on ``dynamic``,
  as explained below.
  Also note that for some fields (e.g. ``readme``), ``ini2toml``
  might try to automatically convert the directive into values accepted by
  :pep:`621` (for complex scenarios ``dynamic`` might still be used).

- Instead of requiring a separated/dedicated section to specify parameters, the
  directives ``find:`` and ``find_namespace:`` just use a nested table:
  ``tool.setuptools.packages.find``.
  Moreover, two quality of life improvements are added: the ``where`` option
  takes a list of strings (instead of a single directory) and the boolean
  ``namespaces`` option is added (``namespaces = true`` is equivalent to
  ``find_namespace:`` and ``namespaces = false`` is equivalent to ``find:``).
  For example:

  .. code-block:: ini

     # setup.cfg
     [options]
     package = find_namespace:
     [options.packages.find]
     where = src
     exclude =
        tests

  .. code-block:: toml

     # pyproject.toml
     [tool.setuptools.packages.find]
     where = ["src"]
     exclude = ["tests"]
     namespaces = true

- Fields set up to be dynamically resolved by :pypi:`setuptools` via directives, that
  cannot be directly represented by following :pep:`621` (or other complementary standards)
  (e.g. ``version = attr: module.attribute`` or ``classifiers = file: classifiers.txt``),
  are listed as ``dynamic`` under the ``[project]`` table.
  The configurations for how :pypi:`setuptools` fill those fields are stored
  under the ``[tool.setuptools.dynamic]`` table.  For example:

  .. code-block:: ini

     # setup.cfg
     [metadata]
     version = attr: module.attribute
     classifiers = file: classifiers.txt

     [options]
     entry_points = file: entry-points.txt

  .. code-block:: toml

     # pyproject.toml
     [project]
     dynamic = ["version", "classifiers", "entry-points", "scripts", "gui-scripts"]

     [tool.setuptools.dynamic]
     version = {attr = "module.attribute"}
     classifiers = {file = "classifiers.txt"}
     entry-points = {file = "entry-points.txt"}

  There is a special case for dynamic ``entry-points``, ``scripts`` and ``gui-scripts``:
  while these 3 fields should be listed under ``project.dynamic``, only
  ``tool.setuptools.dynamic.entry-point`` is allowed. ``scripts`` and
  ``gui-scripts`` should be directly derived from `entry-points file`_.

- The ``options.scripts`` field is renamed to ``script-files`` and resides
  inside the ``tool.setuptools`` table. This is done to avoid confusion with
  the ``project.scripts`` field defined by :pep:`621`.

- When not present in the original config file, ``include_package_data`` is
  explicitly added with the ``False`` value to the translated TOML.
  This does not change directly how the configuration is handled (given that
  currently the default value for this field is ``False``), but allows an
  eventual future change in the default value to ``True`` if the
  :pypi:`setuptools` maintainers decide so. This eventual change is mentioned
  by some members of the community as a nice quality of life improvement.

- The ``metadata.license_files`` field in ``setup.cfg`` is not translated to
  ``project.license.file`` in ``pyproject.toml``, even when a single file is
  given.  The reason behind this choice is that ``project.license.file`` is
  meant to be used in a different way than ``metadata.license_files`` when
  generating `core metadata`_ (the first is read and expanded into the
  ``License`` core metadata field, the second is added as a path - relative to
  the project root - as the ``License-file`` core metadata field). This might
  change in the future if :pep:`639` is accepted.  Meanwhile,
  ``metadata.license_files`` is translated to ``tool.setuptools.license-files``.


Please note these conventions are part of a proposal and will probably
change as soon as a pattern is established by the :pypi:`setuptools` project.
The implementation in ``ini2toml`` is flexible to quickly adapt to these
changes.


.. _TOML: https://toml.io/en/
.. _setuptools own configuration file: https://setuptools.pypa.io/en/latest/userguide/declarative_config.html
.. _entry-points file: https://packaging.python.org/en/latest/specifications/entry-points/
.. _core metadata: https://packaging.python.org/en/latest/specifications/core-metadata/
