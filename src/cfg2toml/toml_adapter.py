"""This module serves as a compatibility layer between API-compatible
style preserving TOML editing libraries (e.g. atoml and atoml).
It makes it easy to swap between implementations for testing (by means of search and
replace).
"""
from atoml import array, comment, document, dumps, inline_table, item, loads, nl, table
from atoml.items import Array, InlineTable, Item, Table
from atoml.toml_document import TOMLDocument

__all__ = [
    "array",
    "Array",
    "comment",
    "document",
    "dumps",
    "inline_table",
    "InlineTable",
    "item",
    "Item",
    "loads",
    "nl",
    "table",
    "Table",
    "TOMLDocument",
]
