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


Automatically translates .cfg/.ini files into TOML


Description
===========

A longer description of your project goes here...


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

This project has been set up using PyScaffold 4.1rc1.post1.dev19+g4c2abfd. For details and usage
information on PyScaffold see https://pyscaffold.org/.
