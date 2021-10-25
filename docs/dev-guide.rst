===============
Developer Guide
===============


This document describes the internal architecture and the main concepts behind
``ini2toml``.

Please notice this document does not target the end users, but instead
people that are involved in the development of the project or that wish to
write ``ini2toml`` plugins.


.. _how-it-works:

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
``"setup.cfg"`` files into :pep:`621`-compliant TOML documents.

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
It respects the :class:`~collections.abc.MutableMapping` protocol, but also
adds some handy position-dependent methods - such as
:meth:`~ini2toml.intermediate_repr.IntermediateRepr.insert`,
:meth:`~ini2toml.intermediate_repr.IntermediateRepr.index`,
:meth:`~ini2toml.intermediate_repr.IntermediateRepr.append`
- and the very useful
:meth:`~ini2toml.intermediate_repr.IntermediateRepr.rename` method.

``IntermediateRepr`` can contain any kind of built-in Python object supported
by TOML_ (e.g. numbers, strings, lists, booleans…) and also a few other
special objects that carry comments along:

- :class:`~ini2toml.intermediate_repr.Commented`: A wrapper around a Python
  built-in value carrying an in-line comment::

    Commented(42, "comment")  # => represents `42 # comment`

- :class:`~ini2toml.intermediate_repr.CommentedList`: A wrapper around a list
  of elements. The elements are organised in groups (that are equivalent to a
  single line in the TOML document), with each group being a ``Commented[list]``.
  For example::

    ir = IntermediateRepr()
    ir["x"] = CommentedList([Commented([0, 1], "comment"), CommentedList([2], "other")])

  is equivalent to the TOML:

  .. code-block:: toml

     x = [
         0, 1, # comment
         2, # other
     ]

- :class:`~ini2toml.intermediate_repr.CommentedKV`: similar to
  ``CommentedList``, but each element is a *key-value pair*.
  For example::

    ir = IntermediateRepr()
    ir["x"] = CommentedKV([Commented([("a", 1), ("b", 2)], "comment")])
    ir["y"] = CommentedKV([
        Commented([("a", 1), ("b", 2)], "comment"),
        Commented([("c", 3)], "other")
    ])

  is equivalent to the TOML:

  .. code-block:: toml

     x = { a = 1, b = 2 } # comment
     [y]
     a = 1
     b = 2 # comment
     c = 3 # other

  Due to TOML limitations, you can only have "one-line" inline-tables,
  therefore ``CommentedKV`` objects with more than one group are automatically
  converted to full-blown TOML tables.

A comment or newline can be added directly to the intermediate representation,
by using a :class:`~ini2toml.intermediate_repr.HiddenKey`::

    ir = IntermediateRepr()
    ir[CommentKey(), "comment"]  # => represents `# comment`
    ir[WhitespaceKey(), ""]  # => represents a `"\n"` in the TOML

Also notice that ``IntermediateRepr`` objects can be nested.


.. _plugins:

Plugins
-------

Plugins are a way of extending the built-in ``ini2toml`` functionality, by
adding processors to specific profiles using the Python programming language.

The implementation requirement for a ``ini2toml`` plugin is a function that
accepts a ``Translator`` object. Using this object it is possible to register
new processors for different profiles, as shown in the example bellow.

.. code-block:: python

   from ini2toml.types import Translator


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

   from ini2toml.types import Translator, Profile


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

For the time being, if using :pypi:`setuptools`, this can be achieved by adding
the following to your ``setup.cfg`` file:

.. code-block:: cfg

   # in setup.cfg
   [options.entry_points]
   ini2toml.processing =
       your_plugin = your_package.your_module:your_activate_function

When using a :pep:`621`-compliant backend, the following can be add to your
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

.. _basename: https://en.wikipedia.org/wiki/Basename
.. _ConfigParser: https://docs.python.org/3/library/configparser.html
.. _ConfigUpdater: https://github.com/pyscaffold/configupdater
.. _ini_cfg: https://docs.python.org/3/library/configparser.html#supported-ini-file-structure
.. _entry-point: https://setuptools.pypa.io/en/stable/userguide/entry_point.html#entry-points
.. _idempotent: https://en.wikipedia.org/wiki/Idempotence#Computer_science_meaning
.. _our docs: https://ini2toml.readthedocs.io/en/stable/api/ini2toml.html
.. _our library of helper functions: https://ini2toml.readthedocs.io/en/stable/api/ini2toml.html
.. _PyPI: https://pypi.org
.. _Python package: https://packaging.python.org/
.. _TOML: https://toml.io/en/
