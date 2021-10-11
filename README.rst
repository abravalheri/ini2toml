.. These are examples of badges you might want to add to your README:
   please update the URLs accordingly

    .. image:: https://api.cirrus-ci.com/github/<USER>/ini2toml.svg?branch=main
        :alt: Built Status
        :target: https://cirrus-ci.com/github/<USER>/ini2toml
    .. image:: https://readthedocs.org/projects/ini2toml/badge/?version=latest
        :alt: ReadTheDocs
        :target: https://ini2toml.readthedocs.io/en/stable/
    .. image:: https://img.shields.io/coveralls/github/<USER>/ini2toml/main.svg
        :alt: Coveralls
        :target: https://coveralls.io/r/<USER>/ini2toml
    .. image:: https://img.shields.io/pypi/v/ini2toml.svg
        :alt: PyPI-Server
        :target: https://pypi.org/project/ini2toml/
    .. image:: https://img.shields.io/conda/vn/conda-forge/ini2toml.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/ini2toml
    .. image:: https://pepy.tech/badge/ini2toml/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/ini2toml
    .. image:: https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter
        :alt: Twitter
        :target: https://twitter.com/ini2toml

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


How it works
============

``ini2toml`` converts your |ini_cfg| files into a data structure with
an intermediate representation and then serialise this data
structure using a TOML library.

.. _pipeline:

This transformation works as a 5-stage data pipeline:

1. The original |ini_cfg| text file is :ref:`pre-processed <text-processing>`.
2. ``ini2toml`` parses the |ini_cfg| file contents using |ConfigParser|_
   (*"lite"* flavour) or |ConfigUpdater|_ (*"full"* flavour) and
   transforms it into an intermediate data structure.
3. This intermediate object is further :ref:`processed <intermediate-processing>`.
4. ``ini2toml`` convert the intermediate representation into a string that uses TOML syntax.
5. The resulting TOML text file is :ref:`post-processed <text-processing>`.


.. _core-concepts:

Core Concepts
=============

The INI syntax (as supported by Python's standard library) is not very
expressive or even clearly defined, at least in terms of data types. For
example, while TOML have clear ways of indicating whether values are strings
and numbers (or even more complex lists and associative tables), most of the
times it is up to the INI syntax user the responsibility of identifying the
correct data type of a stored value and convert it according to the context.

Since, over the time different communities of |ini_cfg| file users
ended up creating different conventions on how to "encode" complex values,
it is very hard for a generic conversion tool to get every single document
right.

``ini2toml`` address this challenge by relying on a system of :ref:`profiles`
and allowing third-party :ref:`plugins`, as documented in the next sections.


.. _profiles:

Profiles
--------

A profile is a simple collection of :ref:`text <text-processing>` and
:ref:`intermediate representation <intermediate-processing>` transformations,
responsible for adjusting or correcting any non-trivial translation between the
original |ini_cfg| file format and the resulting TOML (such as converting
values to specific data types or changing field names or configuration keys).

This collection of transformations is identified by a string (the profile
name), which *in general* corresponds to a file naming convention.
This is motivated by the tradition of different communities using
specific file names for their use cases.

For example, the Python community uses the ``setup.cfg`` file to store packaging metadata.
Therefore, ``ini2toml`` built-in profile named ``"setup.cfg"`` is responsible for converting
``"setup.cfg"`` files into `PEP 621`_-compliant TOML documents.

Each profile will correspond to a specific :ref:`pipeline <pipeline>` being
selected for execution.
When using the ``ini2toml`` command line tool without explicitly specifying a
profile, the |basename|_ of the input file will be used if it is implemented,
falling back to ``"setup.cfg"``.


.. _text-processing:

Pre-processing and Post-processing
----------------------------------

Pre-processing and post-processing are simple text-processing transformations
(i.e. the text contents are transformed from a string object to another string
object). The difference is that pre-processors will receive as input a text
following the INI syntax, while post-processors will receive as input a text
with the converted result, following the TOML syntax.

Each text-processor is a simple Python function with the following signature:

.. code-block:: python

   def text_process(file_contents: str) -> str:
       ...


.. important:: All processors are called in sequence, so the output of one is
   the input of the following (also working as a pipeline). Ideally processor
   implementations should be idempotent_.


.. _intermediate-processing:

Intermediate representation processing
--------------------------------------

Processing the intermediate representation allows more powerful
transformations, including converting stored values to specific types (e.g. a
INI string value to a TOML list) or combining several INI options into a nested
TOML table.

Each intermediate-processor is a simple Python function with the following signature:

.. code-block:: python

   def intermediate_process(intermediate: IntermediateRepr) -> IntermediateRepr:
       ...

:class:`~ini2toml.intermediate_repr.IntermediateRepr` is a special kind of
Python object with characteristics of both :obj:`dict` and :obj:`list`.
It respects :class:`~collections.abc.MutableMapping` protocol, but also adds
some handy position-dependent methods - such as
:meth:`~ini2toml.intermediate_repr.IntermediateRepr.insert`,
:meth:`~ini2toml.intermediate_repr.IntermediateRepr.index`,
:meth:`~ini2toml.intermediate_repr.IntermediateRepr.append`
- and the very useful
:meth:`~ini2toml.intermediate_repr.IntermediateRepr.rename` method.


.. _plugins:

Plugins
-------

Plugins are a way of extending the built-in ``ini2toml`` functionality, by
adding processors to specific profiles using the Python programming language.

The implementation requirement for a ``ini2toml`` plugin is a function that
accepts a ``Translator`` object. Using this object it is possible to register
new processors for different profiles, as shown in the example bellow.

.. code-block:: python

   from ini2toml import Translator


   def activate(translator: Translator):
       profile = translator["setup.cfg"]  # profile.name will be ``setup.cfg``
       desc = "Convert 'setup.cfg' files to 'pyproject.toml' based on PEP 621"
       profile.description = desc
       profile.pre_processing += my_pre_processor
       profile.intermediate_processing += my_intermediate_processor
       profile.post_processing += my_post_processor


.. _profile augmentation:

Profile-independent processing via *profile augmentation*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes it might be useful to implement generic processing tasks that do not
depend on the nature/focus of the file being converted and therefore do not
belong to a specific profile (e.g. removing trailing newline, blank lines, ...).
The :meth:`~ini2toml.translator.Translator.augment_profiles` mechanism in
``ini2toml`` allow plugins to include such processing tasks, by enabling them
to modify the profile after it is selected.

An example of these - here called **"profile augmentation functions"** - is
shown in the following example:

.. code-block:: python

   from ini2toml import Translator, Profile


   def activate(translator: Translator):
       translator.augment_profiles(extra_processing, active_by_default=True)


   def strip_trailing_newline(profile: Profile):
       """Remove trailing newline from the generated TOML file"""
       profile.post_processing.append(str.strip)


Customising the CLI help text
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``ini2toml`` will try to automatically generate a *help text* to be displayed
in the CLI for the registered profiles based on the ``name`` and ``help_text``
properties of the ``Profile`` objects. If ``help_text`` is blank, the profile
will not be featured in the CLI description (i.e. it will be a hidden profile).

``ini2toml`` will also generate a "on/off"-style CLI option flag (depending on
the ``active_by_default`` value) for each ":ref:`profile-augmentation <profile
augmentation>` function".
By default, the name and docstring of the function registered with
:meth:`~ini2toml.translator.Translator.augment_profiles`
will be used to create the CLI help text, but this can also be customised via
optional keyword arguments ``name`` and ``help_text``.
Differently from profiles, these flags will always be visible in the CLI,
independently of the values of ``help_text``.


Distributing Plugins
~~~~~~~~~~~~~~~~~~~~

To distribute ``ini2toml`` plugins, it is necessary to create a `Python package`_ with
a ``ini2toml.processing`` entry-point_.

For the time being, if using setuptools_, this can be achieved by adding the following to your
``setup.cfg`` file:

.. code-block:: cfg

   # in setup.cfg
   [options.entry_points]
   ini2toml.processing =
       your_plugin = your_package.your_module:your_activate_function

When using a `PEP 621`_-compliant backend, the following can be add to your
``pyproject.toml`` file:

.. code-block:: toml

   # in pyproject.toml
   [project.entry-points]
   "ini2toml.processing" = {your_plugin = "your_package.your_module:activate"}

It is recommended that plugins created by the community and meant to be
publicly shared are distributed via PyPI_ under a name that adheres to the following convention::

    ini2toml-contrib-<your specific name>

with ``<your specific name>`` being the same string identifier used as entry-point.

Please notice plugins are activated in a specific order, which can interfere
with the order that the processors run. They are sorted using Python's built-in
``sorted`` function.

When writing your own plugin, please have a look on `our library of helper
functions`_ that implement common operations.


.. |basename| replace:: ``basename``
.. |ini_cfg| replace:: ``.ini/.cfg``
.. |ConfigParser| replace:: ``ConfigParser``
.. |ConfigUpdater| replace:: ``ConfigUpdater``
.. |pipx| replace:: ``pipx``

.. _AST: https://en.wikipedia.org/wiki/Abstract_syntax_tree
.. _atoml: https://github.com/frostming/atoml
.. _basename: https://en.wikipedia.org/wiki/Basename
.. _ConfigParser: https://docs.python.org/3/library/configparser.html
.. _ConfigUpdater: https://github.com/pyscaffold/configupdater
.. _ini_cfg: https://docs.python.org/3/library/configparser.html#supported-ini-file-structure
.. _entry-point: https://setuptools.readthedocs.io/en/stable/userguide/entry_point.html#entry-points
.. _idempotent: https://en.wikipedia.org/wiki/Idempotence#Computer_science_meaning
.. _our docs: https://ini2toml.readthedocs.io/en/stable/api/ini2toml.html
.. _our library of helper functions: https://ini2toml.readthedocs.io/en/stable/api/ini2toml.html
.. _PEP 621: https://www.python.org/dev/peps/pep-0621/
.. _pipx: https://pypa.github.io/pipx/
.. _project dependency: https://packaging.python.org/tutorials/managing-dependencies/
.. _PyPI: https://pypi.org
.. _Python package: https://packaging.python.org/
.. _setuptools: https://setuptools.readthedocs.io/en/stable/
.. _TOML library: https://github.com/hukkin/tomli-w
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
