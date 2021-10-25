=====================
Setuptools and PEP621
=====================

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

- Any field without an obvious equivalent in :pep:`621`, are stored in the
  ``[tool.setuptools]`` TOML table, regardless if it comes from the
  ``[metadata]`` or ``[options]`` sections in ``setup.cfg``.
- ``[options.*]`` sections in ``setup.cfg`` are translated to sub-tables of
  ``[tool.setuptools]`` in ``pyproject.toml``. For example::

    [options.package_data] => [tool.setuptools.package_data]

- Field and subtables in ``[tool.setuptools]`` have the ``_`` character
  replaced by ``-`` in their keys, to follow the conventions set in :pep:`517`
  and :pep:`621`.
- When not specified by :pep:`621`, fields in ``setup.cfg`` that contain
  directives (e.g. ``attr:`` or ``file:``) are transformed into a (potentially
  inline) TOML table, with the directive as a key. For example::

    'file: description.rst' => {file = "description.rst"}

- Instead of requiring a separated/dedicated section to specify parameters, the
  directives ``find:`` and ``find_namespace:`` just use a nested table. For example:

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
     [tool.setuptools.packages.find-namespace]
     where = "src",
     exclude = ["tests"]

- Fields set up to be dynamically resolved by :pypi:`setuptools` via directives, that
  only have an static equivalent in :pep:`621` (e.g. ``version = attr: module.attribute``
  or ``classifiers = file: classifiers.txt``), are listed as ``dynamic``
  under the ``[project]`` table. The configurations for how :pypi:`setuptools` fill
  those fields are stored under the ``[tool.setuptools.dynamic]`` table.
  For example:

  .. code-block:: ini

     # setup.cfg
     [metadata]
     version = attr: module.attribute
     classifiers = file: classifiers.txt

  .. code-block:: toml

     # pyproject.toml
     [project]
     dynamic = ["version", "classifiers"]

     [tool.setuptools.dynamic]
     version = { attr = "module.attribute" }
     classifiers = { file = "classifiers.txt" }


- The ``options.scripts`` field is renamed to ``script-files`` and resides
  inside the ``tool.setuptools`` table. This is done to avoid confusion with
  the ``project.scripts`` field defined by :pep:`621`.


Please notice these conventions are part of a proposal and will probably
change as soon as a pattern is established by the :pypi:`setuptools` project.
The implementation in ``ini2toml`` is flexible to quickly adapt to these
changes.


.. _TOML: https://toml.io/en/
.. _setuptools own configuration file: https://setuptools.pypa.io/en/latest/userguide/declarative_config.html
