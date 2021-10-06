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
   Bugs are likely to be found (specially regarding the underlying style
   preserving TOML libraries).


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
    from cfg2toml.api import Translator

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

.. _pipeline:

The AST translation works as a 5-stage data pipeline:

1. The original |cfg_ini| text file is :ref:`pre-processed <text-processing>`.
2. ``cfg2toml`` parses the |cfg_ini| file contents using |ConfigUpdater|_.
3. The resulting object is ref:`cfg-processed <cfg-processing>`.
4. ``cfg2toml`` automatically converts the `ConfigUpdater's AST`_ into TOML AST
   using atoml_/tomlkit_
5. The resulting object is ref:`toml-processed <toml-processing>`.
6. ``cfg2toml`` convert the TOML object into a string that uses TOML syntax.
7. The resulting TOML text file is :ref:`post-processed <text-processing>`.


.. _core-concepts:

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
and allowing third-party :ref:`plugins`, as documented in the next sections.


Profiles
--------

A profile is a simple collection of :ref:`text-processing`,
:ref:`cfg-processing` and :ref:`toml-processing` transformations, responsible
for adjusting or correcting any non-trivial translation between the original
|cfg_ini| file format and the resulting TOML (such as coercing values to
specific data types or changing field names or configuration keys).

This collection of transformations is identified by a string (the profile
name), which *in general* corresponds to a file naming convention.
This is motivated by the tradition of different communities using
specific file names for their use cases.

For example, the Python community uses the ``setup.cfg`` file to store packaging metadata.
Therefore, ``cfg2toml`` built-in profile named ``"setup.cfg"`` is responsible for converting
``"setup.cfg"`` files into `PEP 621`_-compliant TOML documents.

Each profile will correspond to a specific :ref:`pipeline` being selected for
execution.
When using the ``cfg2toml`` command line tool without explicitly specifying a
profile, the |basename|_ of the input file will be used if it is implemented,
falling back to ``"setup.cfg"``.


.. _text-processing:

Pre-processing and Post-processing
----------------------------------

Pre-processing and post-processing are simple text-processing transformations
(i.e. the text contents are transformed from a string object to another string
object). The difference is that pre-processors will receive as input a text
following the CFG syntax, while post-processors will receive as input a text
with the converted result, following the TOML syntax.

Each text-processor is a simple Python function with the following signature:

.. code-block:: python

   def text_process(file_contents: str) -> str:
       ...


CFG-processing
--------------

CFG-processing consists in altering the CFG syntax AST (here represented as a
|ConfigUpdater| Document object) into a modified version of itself.
This is useful when simple changes are required and are better implemented with
the support of |ConfigUpdater| (e.g. changing the name of a section or option
while maintaining the original order).

Each cfg-processor is a simple Python function with the following signature:

.. code-block:: python

   def cfg_process(cfg: ConfigUpdater) -> ConfigUpdater:
       ...

TOML-processing
---------------

TOML-processing allows more powerful transformations, including coercing stored
values to specific types (e.g. a CFG string value to a TOML list) or combining
several CFG options into a nested TOML table.

Each toml-processor is a simple Python function with the following signature:

.. code-block:: python

   def toml_process(cfg: ConfigUpdater, toml: TOMLDocument) -> TOMLDocument:
       ...

Please notice your function **SHOULD NOT** modify the ``cfg`` parameter. This
parameter corresponds to the |dos_ini| document, in the same state as obtained
after :ref:`cfg-processing`.


.. important:: All processors (text, CFG, TOML)
   are called in sequence, so the output of one is
   the input of the following (also working as a pipeline).
   Ideally processor implementations should be idempotent_.


Plugins
-------

Plugins are a way of extending the built-in ``cfg2toml`` functionality, by
adding processors to specific profiles using the Python programming language.

The implementation requirement for a ``cfg2toml`` plugin is to implement a
function that accepts a ``Translator`` object. Using this object, this function
can register new processors for different profiles, as shown in the example bellow.

.. code-block:: python
   from cfg2toml import Translator


   def activate(translator: Translator):
       profile = translator["setup.cfg"]  # profile.name will be ``setup.cfg``
       desc = "Convert 'setup.cfg' files to 'pyproject.toml' based on PEP 621"
       profile.description = desc
       profile.pre_processing += my_pre_processor
       profile.cfg_processing += my_cfg_processor
       profile.toml_processing += my_toml_processor
       profile.post_processing += my_post_processor


.. _profile augmentation:

Profile-independent processing via *profile augmentation*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes it might be useful to implement generic processing tasks that do not
depend on the nature/focus of the file being converted and therefore do not
belong to a specific profile (e.g. fixing trailing spaces, blank lines, ...).
The ``Translator.augment_profiles`` mechanism in ``cfg2toml`` allow plugins
to include such processing tasks, by enabling them to modify the profile after
it is selected.

An example of these - here called **"profile augmentation functions"** - is
shown in the following example:

.. code-block:: python
   from cfg2toml import Translator, Profile


   def activate(translator: Translator):
       translator.augment_profiles(extra_processing, active_by_default=True)


   def strip_trailing_spaces(profile: Profile):
       """Remove trailing spaces from the generated TOML file"""
       profile.post_processing += function_that_removes_trailing_spaces


Customising the CLI help text
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``cfg2toml`` will try to automatically generate a *help text* to be displayed
in the CLI for the registered profiles based on the ``name`` and ``help_text``
properties of the ``Profile`` objects. If ``help_text`` is blank, the profile
will not be featured in the CLI description (i.e. it will be a hidden profile).

``cfg2toml`` will also generate a "on/off"-style CLI option flag (depending on
the ``active_by_default`` value) for each ":ref:`profile augmentation` function".
By default, the name and docstring of the function registered with
``Translator.augment_profiles`` will be used to create the CLI help text, but
this can also be customised via optional keyword arguments ``name`` and
``help_text``.
Differently from profiles, these flags will always be visible in the CLI,
independently of the values of ``help_text``.


Distributing Plugins
~~~~~~~~~~~~~~~~~~~~

To distribute ``cfg2toml`` plugins, it is necessary to create a `Python package`_ with
a ``cfg2toml.processing`` entry-point_.

For the time being, if using setuptools_, this can be achieved by adding the following to your
``setup.cfg`` file:

.. code-block:: cfg

   # in setup.cfg
   [options.entry_points]
   cfg2toml.processing =
       your_plugin = your_package.your_module:your_activate_function

When using a `PEP 621`_-compliant backend, the following can be add to your
``pyproject.toml`` file:

.. code-block:: toml

   # in pyproject.toml
   [project.entry-points]
   "cfg2toml.processing" = {your_plugin = "your_package.your_module:activate"}

It is recommended that plugins created by the community and meant to be
publicly shared are distributed via PyPI_ under a name that adheres to the following convention::

    cfg2tomlext-<your specific name>

with ``<your specific name>`` being the same string identifier used as entry-point.

Please notice plugins are activated in a specific order, which can interfere
with the order that the processors run. They are sorted using Python's built-in
``sorted`` function.

When writing your own plugin, please have a look on `our library of helper
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
