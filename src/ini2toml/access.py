"""Functions for item access/manipulation in nested mapping/mutable mapping objects."""
from typing import TYPE_CHECKING, Any, TypeVar

from .types import NOT_GIVEN

if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping, Sequence
else:
    from typing import Mapping, MutableMapping, Sequence

M = TypeVar("M", bound="MutableMapping")


def get_nested(m: Mapping, keys: Sequence[str], default: Any = None) -> Any:
    """Nested version of :meth:`collections.abc.Mapping.get`"""
    value = m
    for k in keys:
        if k not in value:
            return default
        value = value[k]
    return value


def pop_nested(m: MutableMapping, keys: Sequence[str], default: Any = None) -> Any:
    """Nested version of :meth:`collections.abc.MutableMapping.pop`"""
    *path, last = keys
    parent = get_nested(m, path, NOT_GIVEN)
    if parent is NOT_GIVEN:
        return default
    return parent.pop(last, default)


def set_nested(m: M, keys: Sequence[str], value) -> M:
    """Nested version of :meth:`collections.abc.MutableMapping.__setitem__`"""
    last = keys[-1]
    parent = setdefault(m, keys[:-1], {})
    parent[last] = value
    if hasattr(value, "display_name"):
        # Temporary workaround for tomlkit#144 and atoml#24
        j = next((i for i, k in enumerate(keys) if isinstance(k, int)), 0)
        value.display_name = ".".join(keys[j:])
    return m


def setdefault(m: MutableMapping, keys: Sequence[str], default: Any = None) -> Any:
    """Nested version of :meth:`collections.abc.MutableMapping.setdefault`"""
    if len(keys) < 1:
        return m
    if len(keys) == 1:
        return m.setdefault(keys[0], default)
    value = m
    for k in keys[:-1]:
        value = value.setdefault(k, {})
    return value.setdefault(keys[-1], default)
