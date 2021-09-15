from contextlib import suppress
from typing import Dict, Mapping, MutableMapping, Tuple, TypeVar, Union

from ..profile import Profile
from ..translator import Translator

M = TypeVar("M", bound=MutableMapping)

RenameRules = Dict[Tuple[str, ...], Union[Tuple[str, ...], None]]


def activate(translator: Translator):
    pass


def add_to_profile(profile: Profile):
    pass


def pep621_renaming() -> RenameRules:
    """Rules are applied sequentially and therefore can interfere with the following
    ones
    """
    metadata = {
        "project-urls": ("urls",),
        "url": ("urls", "homepage"),
        "download-url": ("urls", "download"),
        "author": ("author", 0, "name"),
        "author-email": ("author", 0, "email"),
        "maitainer": ("author", 0, "name"),
        "maitainer-email": ("author", 0, "email"),
        ("long-description", "file"): ("readme", "file"),
        "long-description": ("readme", "text"),
        "long-description-content-type": ("readme", "content-type"),
        "license-files": ("license", "file"),
        "license": ("license", "text"),
    }
    options = {
        "python-requires": ("requires-python"),
        "install-requires": ("dependencies"),
        "extras-require": ("optional-dependencies"),
        ("entry-points", "console-scripts"): ("scripts"),
        ("entry-points"): ("entry-points"),
    }
    specific = ["platforms", "provides", "obsoletes"]

    changes: RenameRules = {
        ("metadata",): ("project",),
        ("options",): ("tool", "setuptools"),
    }
    for orig, dest in metadata.items():
        key = orig if isinstance(orig, tuple) else (orig,)
        changes[("project", *key)] = ("project", dest)
    for orig, dest in options.items():
        key = orig if isinstance(orig, tuple) else (orig,)
        changes[("tool", "setuptools", *key)] = ("project", dest)
    for key in specific:
        changes[("metadata", key)] = ("tool", "setuptools", key)
    return changes


def post_process(orig: Mapping, out: M) -> M:
    transformations = [
        # convert_directives,
        # apply_renaming(pep621_renaming()),
        fix_license,
        fix_dynamic,
        fix_packages,
    ]
    return out


def fix_license(_orig: Mapping, out: M) -> M:
    value = out.get("project", {}).pop("license", None)
    if value and "file" in value:
        value.pop("text", None)  # these fields are mutually exclusive
    return out


def fix_dynamic(orig: Mapping, out: M) -> M:
    project = out.setdefault("project", {})
    potential = ["version", "classifiers", "description"]
    fields = [f for f in potential if isdirective(project.get(f, None))]
    dynamic = project.setdefault("dynamic", [])
    with suppress(KeyError):
        if orig["options"]["entry-points"].startswith("file:"):
            fields.append("entry-points")
            dynamic.extend(["scripts", "gui-scripts"])
    dynamic.extend(fields)
    setuptools = out.setdefault("tool", {}).setdefault("setuptools", {})
    configs = setuptools.setdefault("dynamic", {})
    for field in fields:
        configs[field] = project.pop(field)
    return out


def fix_packages(_orig: Mapping, out: M) -> M:
    setuptools = out.setdefault("tool", {}).setdefault("setuptools", {})
    packages = setuptools.setdefault("packages", {})
    if "find_namespace" in packages and "find" in packages:
        packages["find_namespace"].update(packages.pop("find"))
    return out


def convert_case(field: str) -> str:
    return field.lower().replace("_", "-")


def isdirective(value, valid=("file", "attr")) -> bool:
    return (
        isinstance(value, Mapping) and len(value) == 1 and next(value.keys()) in valid
    )
