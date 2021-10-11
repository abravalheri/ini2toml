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
    :target: https://ini2toml.readthedocs.io/en/stable/
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

.. warning:: This project is **experimental** and under development
   (so by no means production-ready).
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

Now you can use ``ini2toml`` as a command line:

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

More details about ``ini2toml`` and its Python API can be found in `our docs`_.


.. |ini_cfg| replace:: ``.ini/.cfg``
.. |ConfigParser| replace:: ``ConfigParser``
.. |ConfigUpdater| replace:: ``ConfigUpdater``
.. |pipx| replace:: ``pipx``

.. _ConfigParser: https://docs.python.org/3/library/configparser.html
.. _ConfigUpdater: https://github.com/pyscaffold/configupdater
.. _ini_cfg: https://docs.python.org/3/library/configparser.html#supported-ini-file-structure
.. _our docs: https://ini2toml.readthedocs.io/en/stable/
.. _PEP 621: https://www.python.org/dev/peps/pep-0621/
.. _pipx: https://pypa.github.io/pipx/
.. _project dependency: https://packaging.python.org/tutorials/managing-dependencies/
.. _TOML: https://toml.io/en/
.. _virtual environment: https://realpython.com/python-virtual-environments-a-primer/


.. _pyscaffold-notes:

Making Changes & Contributing
=============================

This project uses `pre-commit`_, please make sure to install it before making any
changes::

    pip install pre-commit
    cd ini2toml
    pre-commit install

It is a good idea to update the hooks to the latest version::

    pre-commit autoupdate

Don't forget to tell your contributors to also install and use pre-commit.

.. _pre-commit: https://pre-commit.com/

Note
====

This project has been set up using PyScaffold 4.1rc1. For details and usage
information on PyScaffold see https://pyscaffold.org/.
