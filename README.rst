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

.. warning:: For the time being, if you want to use the *"full"* flavour,
   you will also need a `patched version`_ of the supporting `TOML library`_.
   If you have installed ``ini2toml`` with |pipx|_ as indicated above,
   you can overwrite the dependency with the following command:

   .. code-block:: bash

      $ pipx runpip ini2toml install -I 'git+https://github.com/abravalheri/atoml@all-patches#egg=atoml'

      # OR if you are managing your own virtual environment:
      $ pip install -I 'git+https://github.com/abravalheri/atoml@all-patches#egg=atoml'

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

More details about ``ini2toml`` and its Python API can be found in `our docs`_.


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
.. _patched version: https://github.com/abravalheri/atoml/tree/all-patches
.. _PEP 621: https://www.python.org/dev/peps/pep-0621/
.. _pipx: https://pypa.github.io/pipx/
.. _project dependency: https://packaging.python.org/tutorials/managing-dependencies/
.. _TOML: https://toml.io/en/
.. _TOML library: https://github.com/frostming/atoml
.. _virtual environment: https://realpython.com/python-virtual-environments-a-primer/
