.. These are examples of badges you might want to add to your README:
   please update the URLs accordingly

    .. image:: https://api.cirrus-ci.com/github/<USER>/cfg2toml.svg?branch=main
        :alt: Built Status
        :target: https://cirrus-ci.com/github/<USER>/cfg2toml
    .. image:: https://readthedocs.org/projects/cfg2toml/badge/?version=latest
        :alt: ReadTheDocs
        :target: https://cfg2toml.readthedocs.io/en/stable/
    .. image:: https://img.shields.io/coveralls/github/<USER>/cfg2toml/main.svg
        :alt: Coveralls
        :target: https://coveralls.io/r/<USER>/cfg2toml
    .. image:: https://img.shields.io/pypi/v/cfg2toml.svg
        :alt: PyPI-Server
        :target: https://pypi.org/project/cfg2toml/
    .. image:: https://img.shields.io/conda/vn/conda-forge/cfg2toml.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/cfg2toml
    .. image:: https://pepy.tech/badge/cfg2toml/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/cfg2toml
    .. image:: https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter
        :alt: Twitter
        :target: https://twitter.com/cfg2toml

.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

|

========
cfg2toml
========


Automatically translates |cfg_ini|_ files into TOML_

.. warning:: This project is under development and currently under the "design
   stage", which means that the contents of this document should be taken
   simply as a wish-list_, and as a project description.


Description
===========

The original purpose of this project is to help migrating ``setup.cfg`` files
to `PEP 621`_, but by extension it can also be used to convert any compatible |cfg_ini|_
file to TOML_.

Please notice, the provided |cfg_ini|_ files should follow the same syntax
supported by Python's |ConfigParser|_ library (here referred to as CFG syntax)
and more specifically abide by |ConfigUpdater|_ restrictions (e.g., no
interpolation or repeated fields).


Usage
=====

First you need to install the package. An easy way to get started is by
using |pipx|_:

    $ pipx install cfg2toml

Now you can use ``cfg2toml`` as a command line:

.. code-block:: bash

    # in you terminal
    $ cfg2toml --help
    $ cfg2toml path/to/cfg/or/ini/file

You can also use ``cfg2toml`` in your Python scripts or projects:

.. code-block:: python

    # in your python code
    from cfg2toml import Translator

    toml_str = Translator().translate(original_contents_str, profile="setup.cfg")

To do so, don't forget to add it to your `virtual environment`_ or specify it as a
`project dependency`_.

More details about ``cfg2toml`` Python API can be found in `our docs`_


How it works
============

Instead of simply converting your |cfg_ini| files into a simple
dictionary/hashtable-like data structure and then serialising this data
structure using a `simple TOML library`_, ``cfg2toml`` works by first parsing
CFG syntax into a abstract syntax tree (AST_) representation and then
converting it into a TOML-equivalent.

This means that ``cfg2toml`` will make an effort to translate the original
file's comments and little details (as much as possible), which would otherwise
be stripped out of the resulting TOML file and lost.

The AST translation works as a 5-stage data pipeline:

1. ``cfg2toml`` parses the |cfg_ini| file contents using |ConfigUpdater|_.
2. The resulting object is ref:`pre-processed <pre-processing>`
3. ``cfg2toml`` automatically converts the `ConfigUpdater's AST`_ into TOML AST
   using atoml_/tomlkit_
4. The resulting object is ref:`post-processed <post-processing>`
5. ``cfg2toml`` convert the TOML object into a string that uses TOML syntax.


Core Concepts
=============

The CFG syntax (as supported by Python's standard library) is not very
expressive or even clearly defined, at least in terms of data types. For
example, while TOML have clear ways of indicating weather values are strings
and numbers (or even more complex lists and associative tables), most of the
times it is up to the CFG syntax user the responsibility of identifying the
correct data type of a stored value and convert it according to the context.

Since, over the time different communities of |cfg_ini| file users
ended up creating different conventions on how to "encode" complex values,
it is very hard for a generic conversion tool to get every single document
right.

``cfg2toml`` address this challenge by relying on a system of :ref:`profiles`
and allowing third-party :ref:`extensions`, as documented in the next sections.


Profiles
--------

A profile is a simple collection of :ref:`pre-processing` and
:ref:`post-processing` transformations, responsible for adjusting or correcting
any non-trivial translation between the original |cfg_ini| file format and the
resulting TOML (such as coercing values to specific data types or changing
field names or configuration keys).

This collection of transformations is identified by a string (the profile
name), which *in general* corresponds to a file naming convention.
This is motivated by the tradition of different communities using
specific file names for their use cases.

For example, the Python community uses the ``setup.cfg`` file to store packaging metadata.
Therefore, ``cfg2toml`` built-in profile named ``"setup.cfg"`` is responsible for converting
``"setup.cfg"`` files into `PEP 621`_-compliant TOML documents.

When using the ``cfg2toml`` command line tool without explicitly specifying a
profile, the |basename|_ of the input file will be used if it is implemented,
falling back to ``"setup.cfg"``.

Pre-processing
--------------

Pre-processing consists in altering the CFG syntax AST (here represented as a
|ConfigUpdater| Document object) into a modified version of itself.
This is useful when simple changes are required (e.g. changing the name of a
section or option).

Each pre-processor is a simple Python function with the following signature:

.. code-block:: python

   def pre_process(cfg: ConfigUpdater) -> ConfigUpdater:
       ...

Pre-processors are called in sequence, so the output of one pre-processor is
the input of the following (also working as a pipeline).
Ideally pre-processor implementations should be idempotent_.

Post-processing
---------------

Post-processing allows more powerful transformations, including coercing stored
values to specific types (e.g. a CFG string value to a TOML list) or combining
several CFG options into a nested TOML table.

Each post-processor is a simple Python function with the following signature:

.. code-block:: python

   def post_process(cfg: ConfigUpdater, toml: TOMLDocument) -> TOMLDocument:
       ...

Please notice your function **SHOULD NOT** modify the ``cfg`` parameter. This
parameter corresponds to the original |dos_ini| document, as originally parsed by
``cfg2toml``.

Post-processors also work as a pipeline and (ideally) implemented in an
idempotent_ fashion.

Extensions
----------

Extensions are a way of augmenting the built-in ``cfg2toml`` functionality, by
adding pre/post-processors to specific profiles using the Python programming
language.

The implementation requirement for a ``cfg2toml`` extension is to implement a
function that accepts a ``Translator`` object. Using this object, this function
can register new pre/post-processors for different profiles, as shown in the
example bellow.


.. code-block:: python
   from cfg2toml import Translator


   def activate(translator: Translator):
       profile = translator["setup.cfg"]
       profile.pre_processing += my_pre_processor
       profile.post_processing += my_post_processor


To distribute ``cfg2toml`` extensions, it is necessary to create a `Python package`_ with
a ``cfg2toml.processing`` entry-point_.

For the time being, if using setuptools_, this can be achieved by adding the following to your
``setup.cfg`` file:

.. code-block:: cfg

   # in setup.cfg
   [options.entry_points]
   cfg2toml.processing =
       your_extension = your_package.your_module:your_activate_function

When using a `PEP 621`_-compliant backend, the following can be add to your
``pyproject.toml`` file:

.. code-block:: toml

   # in pyproject.toml
   [project.entry-points]
   "cfg2toml.processing" = {your_extension = "your_package.your_module:activate"}

It is recommended that extensions created by the community and meant to be
publicly shared are distributed via PyPI_ under a name that adheres to the following convention::

    cfg2tomlext-<your specific name>

with ``<your specific name>`` being the same string identifier used as entry-point.

Please notice extensions are activated in a specific order, which can interfere
with the order that the pre/post-processors run. They are sorted using Python's
built-in ``sorted`` function.

When writing your own extension, please have a look on `our library of helper
functions`_ that implement common operations.


.. |basename| replace:: ``basename``
.. |cfg_ini| replace:: ``.cfg/.ini``
.. |ConfigParser| replace:: ``ConfigParser``
.. |ConfigUpdater| replace:: ``ConfigUpdater``

.. _AST: https://en.wikipedia.org/wiki/Abstract_syntax_tree
.. _atoml: https://github.com/frostming/atoml
.. _basename: https://en.wikipedia.org/wiki/Basename
.. _cfg_ini: https://docs.python.org/3/library/configparser.html#supported-ini-file-structure
.. _ConfigUpdater's AST: https://configupdater.readthedocs.io/en/latest/api/configupdater.html#configupdater.document.Document
.. _ConfigUpdater: https://configupdater.readthedocs.io/en/stable/
.. _entry-point: https://setuptools.readthedocs.io/en/stable/userguide/entry_point.html#entry-points
.. _idempotent: https://en.wikipedia.org/wiki/Idempotence#Computer_science_meaning
.. _our docs: https://cfg2toml.readthedocs.io/en/stable/api/cfg2toml.html
.. _our library of helper functions: https://cfg2toml.readthedocs.io/en/stable/api/cfg2toml.html
.. _PEP 621: https://www.python.org/dev/peps/pep-0621/
.. _pipx: https://pypa.github.io/pipx/
.. _project dependency: https://packaging.python.org/tutorials/managing-dependencies/
.. _PyPI: https://pypi.org
.. _Python package: https://packaging.python.org/
.. _simple TOML library: https://github.com/uiri/toml
.. _TOML: https://toml.io/en/
.. _tomlkit: https://github.com/sdispater/tomlkit
.. _virtual environment: https://realpython.com/python-virtual-environments-a-primer/
.. _wish-list: https://deterministic.space/readme-driven-development.html


.. _pyscaffold-notes:

Making Changes & Contributing
=============================

This project uses `pre-commit`_, please make sure to install it before making any
changes::

    pip install pre-commit
    cd cfg2toml
    pre-commit install

It is a good idea to update the hooks to the latest version::

    pre-commit autoupdate

Don't forget to tell your contributors to also install and use pre-commit.

.. _pre-commit: https://pre-commit.com/

Note
====

This project has been set up using PyScaffold 4.1rc1. For details and usage
information on PyScaffold see https://pyscaffold.org/.
