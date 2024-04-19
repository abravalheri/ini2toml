.. These are examples of badges you might want to add to your README:
   please update the URLs accordingly

    .. image:: https://img.shields.io/conda/vn/conda-forge/ini2toml.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/ini2toml
    .. image:: https://pepy.tech/badge/ini2toml/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/ini2toml
    .. image:: https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter
        :alt: Twitter
        :target: https://twitter.com/ini2toml

.. image:: https://api.cirrus-ci.com/github/abravalheri/ini2toml.svg?branch=main
    :alt: Built Status
    :target: https://cirrus-ci.com/github/abravalheri/ini2toml
.. image:: https://readthedocs.org/projects/ini2toml/badge/?version=latest
    :alt: ReadTheDocs
    :target: https://ini2toml.readthedocs.io
.. image:: https://img.shields.io/coveralls/github/abravalheri/ini2toml/main.svg
    :alt: Coveralls
    :target: https://coveralls.io/r/abravalheri/ini2toml
.. image:: https://img.shields.io/pypi/v/ini2toml.svg
    :alt: PyPI-Server
    :target: https://pypi.org/project/ini2toml/
.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

|

========
ini2toml
========


    Automatically translates |ini_cfg|_ files into TOML_

.. important:: This project is **experimental** and under active development
   Issue reports and contributions are very welcome.


Description
===========

The original purpose of this project is to help migrating ``setup.cfg`` files
to `PEP 621`_, but by extension it can also be used to convert any compatible |ini_cfg|_
file to TOML_.

Please notice, the provided |ini_cfg|_ files should follow the same syntax
supported by Python's |ConfigParser|_ library (here referred to as INI syntax)
and more specifically abide by |ConfigUpdater|_ restrictions (e.g., no
interpolation or repeated fields).


Usage
=====

``ini2toml`` comes in two flavours: *"lite"* and *"full"*. The "lite"
flavour will create a TOML document that does not contain any of the comments
from the original |ini_cfg| file. On the other hand, the "full" flavour
will make an extra effort to translate these comments into a TOML-equivalent
(please notice sometimes this translation is not perfect, so it is always good
to check the TOML document afterwards).

To get started, you need to install the package, which can be easily done
using |pipx|_:

.. code-block:: bash

    $ pipx install 'ini2toml[lite]'
    # OR
    $ pipx install 'ini2toml[full]'

Now you can use ``ini2toml`` as a command line tool:

.. code-block:: bash

    # in you terminal
    $ ini2toml --help
    $ ini2toml path/to/ini/or/cfg/file

You can also use ``ini2toml`` in your Python scripts or projects:

.. code-block:: python

    # in your python code
    from ini2toml.api import Translator

    profile_name = "setup.cfg"
    toml_str = Translator().translate(original_contents_str, profile_name)

To do so, don't forget to add it to your `virtual environment`_ or specify it as a
`project dependency`_.

Note that the class ``Translator`` will try to guess which flavour to use based
on the available installed dependencies. If you need something more
deterministic, consider using ``LiteTranslator`` and ``FullTranslator``,
or explicitly specifying the ``ini_loads_fn`` and ``toml_dumps_fn`` keyword
arguments in the constructor.

More details about ``ini2toml`` and its Python API can be found in `our docs`_.


Limitations
===========

``ini2toml`` will try its best to create good quality translations from
``.ini/.cfg`` into ``.toml`` files. However the tool comes with a set of
well known limitations:

* Although ``ini2toml`` attempts to keep the same order/sequence as the original
  information was written, sometimes that is not compatible with the TOML
  syntax, and things end up moving around a bit.

* ``ini2toml`` uses `ConfigParser`_ + `tomli-w`_ for implementing the *"lite"* flavour
  and `ConfigUpdater`_ + `tomlkit`_ for implementing the *"full"* flavour.
  Therefore it inherits the limitations from those libraries (please check
  their documentation for more information).

  * `ConfigUpdater`_, in particular, will have trouble to parse
     interpolations and the related escaping sequence (``%%``)
     (in this respect, it behaves more similarly to ``RawConfigParser`` than ``ConfigParser``).

* ``ini2toml`` *expects the input to be valid* and will not perform extensive
  checks on the provided document. If something in the output is not working as you would
  expect, it might be a good idea to check the input.

* ``.ini/.cfg`` files are used in a plethora of use cases and it is impossible
  to cover all of them in a single code base. Even when considering
  ``setup.cfg``, there are many packages that define different sections in the
  document in addition to the basic definition by ``setuptools``.
  Because of that ``ini2toml``, adopts a "best-effort" approach, that might not
  correspond to what you expect. If that is the case please consider
  contributing or creating your own `plugin`_.

* The translation procedure analyse only the given input. If the original
  ``.ini/.cfg`` file contains references to other files, or behaves differently
  depending on the existence/presence of other files and directories, the
  translation will not take that into consideration.

Therefore it is recommended to double check the output and fix any
problems before using the ``.toml`` files in production.


Can ``ini2toml`` also translate ``setup.py`` into ``pyproject.toml``?
=====================================================================

Working with ``.py`` files is not in the scope of the ``ini2toml`` project,
and therefore this feature is not implemented.

However, you can probably find some tools on PyPI to translate from
``setup.py`` into ``setup.cfg``, like `setup-py-upgrade`_ and
`setuptools-py2cfg`_ [#untested]_.

Once you have ``setup.cfg``, you can use ``ini2toml`` [#setuppy]_.

.. [#untested] Such tools are neither maintained by this project,
   nor tested for integration by ``ini2toml``.
   It is best to try some of them out and find the one that works for you.
   Manual corrections might be needed.

.. [#setuppy] Please note that ``setup.py`` is a very dynamic
   format and that not everything can be represented in ``setup.cfg`` or
   ``pyproject.toml``. Indeed, the `setuptools' docs`_ explicitly say that
   ``setup.py`` can be used in tandem with ``pyproject.toml``: ideally all the
   declarative metadata goes to ``pyproject.toml``, but you can keep the
   dynamic bits in ``setup.py``.
   Remember: ``setup.py`` is a perfectly valid and non deprecated configuration file;
   what is deprecated is running it as a CLI tool, i.e. ``python setup.py ...`.


.. _pyscaffold-notes:

.. tip::
   If you consider contributing to this project, have a look on our
   `contribution guides`_.

Note
====

This project was initially created in the context of PyScaffold, with the
purpose of helping migrating existing projects to `PEP 621`_-style
configuration when it is made available on ``setuptools``.
For details and usage information on PyScaffold see https://pyscaffold.org/.


.. |ini_cfg| replace:: ``.ini/.cfg``
.. |ConfigParser| replace:: ``ConfigParser``
.. |ConfigUpdater| replace:: ``ConfigUpdater``
.. |pipx| replace:: ``pipx``

.. _ConfigParser: https://docs.python.org/3/library/configparser.html
.. _ConfigUpdater: https://github.com/pyscaffold/configupdater
.. _contribution guides: https://ini2toml.readthedocs.io/en/latest/contributing.html
.. _ini_cfg: https://docs.python.org/3/library/configparser.html#supported-ini-file-structure
.. _our docs: https://ini2toml.readthedocs.io
.. _PEP 621: https://www.python.org/dev/peps/pep-0621/
.. _pipx: https://pipx.pypa.io/stable/
.. _project dependency: https://packaging.python.org/tutorials/managing-dependencies/
.. _plugin: https://ini2toml.readthedocs.io/en/latest/dev-guide.html#plugins
.. _setup-py-upgrade: https://pypi.org/project/setup-cfg-fmt/
.. _setuptools-py2cfg: https://pypi.org/project/setuptools-py2cfg/
.. _setuptools' docs: https://setuptools.pypa.io/en/latest/userguide/quickstart.html#setuppy-discouraged
.. _TOML: https://toml.io/en/
.. _TOML library: https://github.com/sdispater/tomlkit
.. _tomli-w: https://pypi.org/project/tomli-w/
.. _tomlkit: https://tomlkit.readthedocs.io/en/latest/
.. _virtual environment: https://realpython.com/python-virtual-environments-a-primer/
