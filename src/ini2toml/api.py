"""Public API available for general usage.

In addition to the classes and functions "exported" by this module, the following are
also part of the public API:

- The public members of the :mod:`~ini2toml.types` module.
- The public members of the :mod:`~ini2toml.errors` module.
- The ``activate`` function in each submodule of the :obj:`~ini2toml.plugins` package

Please notice there might be classes of similar names exported by both ``api`` and
``types``. When this happens, the classes in ``types`` are not concrete implementations,
but instead act as :class:`protocols <typing.Protocol>` (i.e. abstract descriptions
for checking `structural polymorphism`_ during static analysis).
These should be preferred when writing type hints and signatures.

Plugin authors can also rely on the functions exported by
:mod:`~ini2toml.transformations`.

.. _structural polymorphism: https://www.python.org/dev/peps/pep-0544/
"""
from . import errors, transformations, types
from .base_translator import BaseTranslator
from .translator import Translator

__all__ = ["BaseTranslator", "Translator", "errors", "types", "transformations"]
