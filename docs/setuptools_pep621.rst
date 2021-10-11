=====================
Setuptools and PEP621
=====================

In the Python software ecosystem packaging and distributing software have
historically been a difficult topic.
Nevertheless, the community has been served well by setuptools_ as the *de facto*
standard for creating distributable Python software packages.

In recent years, however, other needs and opportunities fostered the emergence
of some alternatives.
During this packaging renaissance, `PEP 621`_ was proposed (and accepted)
to standardise package metadata/configuration done by developers, in a single
file format shared by all the packaging alternatives.
It makes use of a TOML_ file, ``pyproject.toml``, which is, unfortunately,
significantly different from `setuptools own configuration file`_,
``setup.cfg``, and therefore its adoption by setuptools_ requires mapping
concepts between these two files.

`PEP 621`_ covers most of the information expected from a ``setup.cfg`` file,
but there are parameters specific to setuptools_ without an obvious equivalent.
For the time being setuptools_ documentation does not offer a clear way of
mapping those fields. As a result the (experimental) automatic translation
proposed by ``ini2toml`` takes the following assumptions:

- Any field without an obvious equivalent in `PEP 621`_, are stored in the
  ``[tool.setuptools]`` TOML table, regardless if it comes from the
  ``[metadata]`` or ``[options]`` sections in ``setup.cfg``.
- ``[options.*]`` sections in ``setup.cfg`` are translated to sub-tables of
  ``[tool.setuptools]`` in ``pyproject.toml``. For example::

    [options.package_data] => [tool.setuptools.package_data]

- Field and subtables in ``[tool.setuptools]`` have the ``_`` character
  replaced by ``-`` in their keys, to follow the conventions set in `PEP 517`_
  and `PEP 621`_.
- When not specified by `PEP 621`_, fields in ``setup.cfg`` that contain
  directives (e.g. ``attr:`` or ``file:``) are transformed into a (potentially
  inline) TOML table, with the directive as a key. For example::

    'file: description.rst' => {file = "description.rst"}

- Instead of requiring a separated/dedicated section to specify parameters, the
  directives ``find:`` and ``find_namespace:`` just use a nested table. For example::

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

- Fields set up to be dynamically resolved by setuptools_ via directives, that
  only have an static equivalent in `PEP 621`_ (e.g. ``version = attr: module.attribute``
  or ``classifiers = file: classifiers.txt``), are listed as ``dynamic``
  under the ``[project]`` table. The configurations for how setuptools_ fill
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


Please notice these conventions are part of a proposal and will probably
change as soon as a pattern is established by the setuptools_ project.
The implementation in ``ini2toml`` is flexible to quickly adapt to these
changes.


.. _PEP 517: https://www.python.org/dev/peps/pep-0517/
.. _PEP 621: https://www.python.org/dev/peps/pep-0621/
.. _setuptools: https://setuptools.readthedocs.io/en/stable/
.. _TOML: https://toml.io/en/
.. _setuptools own configuration file: https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html
