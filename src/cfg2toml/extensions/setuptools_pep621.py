from collections.abc import Mapping, MutableMapping
from functools import partial, reduce
from typing import Dict, List, Tuple, TypeVar, Union

from configupdater import ConfigUpdater
from tomlkit.container import Container

from ..processing import (
    NOT_GIVEN,
    apply_nested,
    coerce_bool,
    get_nested,
    pop_nested,
    set_nested,
    split_comment,
    split_kv_pairs,
    split_list,
)
from ..translator import Translator

M = TypeVar("M", bound=MutableMapping)
C = TypeVar("C", bound=Container)

RenameRules = Dict[Tuple[str, ...], Union[Tuple[str, ...], None]]


def activate(translator: Translator):
    profile = translator["setup.cfg"]
    profile.pre_processors.append(pre_process)
    profile.post_processors.append(post_process)


def setupcfg_aliases():
    """``setup.cfg`` aliases as defined in:
    https://setuptools.readthedocs.io/en/stable/userguide/declarative_config.html
    """
    return {
        "classifier": "classifiers",
        "summary": "description",
        "platform": "platforms",
        "license-file": "license-files",
        "home-page": "url",
    }


def setupcfg_directives():
    """``setup.cfg`` directives, as defined in:
    https://setuptools.readthedocs.io/en/stable/userguide/declarative_config.html
    """
    return {
        ("metadata", "version"): ("file", "attr"),
        ("metadata", "classifiers"): ("file",),
        ("metadata", "description"): ("file",),
        ("metadata", "long-description"): ("file",),
        ("options", "entry-points"): ("file",),
        ("options", "packages"): ("find", "find_namespace"),
    }


def value_processing():
    """Value type processing, as defined in:
    https://setuptools.readthedocs.io/en/stable/userguide/declarative_config.html
    """
    split_list_comma = partial(split_list, sep=",", subsplit_dangling=False)
    # split_list_comma = partial(split_list, sep=",")
    split_list_semi = partial(split_list, sep=";", subsplit_dangling=False)
    return {
        ("metadata", "classifiers"): split_list_comma,
        # ("metadata", "license_files",): split_list_comma,  # PEP621 => single file
        ("metadata", "keywords"): split_list_comma,
        ("metadata", "provides"): split_list_comma,
        ("metadata", "requires"): split_list_comma,
        ("metadata", "obsoletes"): split_list_comma,
        ("options", "zip-safe"): coerce_bool,
        ("options", "setup-requires"): split_list_semi,
        ("options", "install-requires"): split_list_semi,
        ("options", "tests-require"): split_list_semi,
        ("options", "scripts"): split_list_comma,
        ("options", "eager-resources"): split_list_comma,
        ("options", "dependency-links"): split_list_comma,
        ("options", "include-package-data"): coerce_bool,
        ("options", "packages"): split_list_comma,
        ("options", "package-dir"): split_kv_pairs,
        ("options", "namespace-packages"): split_list_comma,
        ("options", "py-modules"): split_list_comma,
        ("options", "data-files"): split_kv_pairs,
    }
    # Everything else should use split_comment


def pep621_renaming() -> RenameRules:
    """Renames that have a clear correspondence according to PEP 621.
    Rules are applied sequentially and therefore can interfere with the following
    ones. Please notice that renaming is applied after value processing.
    """
    metadata = {
        ("project-urls",): ("urls",),
        ("url",): ("urls", "homepage"),
        ("download-url",): ("urls", "download"),
        ("author",): ("author", 0, "name"),
        ("author-email",): ("author", 0, "email"),
        ("maitainer",): ("author", 0, "name"),
        ("maitainer-email",): ("author", 0, "email"),
        ("long-description", "file"): ("readme", "file"),
        ("long-description",): ("readme", "text"),
        ("long-description-content-type",): ("readme", "content-type"),
        ("license-files",): ("license", "file"),
        ("license",): ("license", "text"),
    }
    options = {
        ("python-requires",): ("requires-python",),
        ("install-requires",): ("dependencies",),
        ("extras-require",): ("optional-dependencies",),
        ("entry-points", "console-scripts"): ("scripts",),
        ("entry-points",): ("entry-points",),
    }
    specific = ["platforms", "provides", "obsoletes"]
    return {
        ("metadata",): ("project",),
        ("options",): ("tool", "setuptools"),
        **{("project", *k): ("project", *v) for k, v in metadata.items()},
        **{("tool", "setuptools", *k): ("project", *v) for k, v in options.items()},
        **{("project", *e): ("tool", "setuptools", *e) for e in specific},
    }


def convert_directives(_orig: ConfigUpdater, out: C) -> C:
    split_directive = partial(split_kv_pairs, key_sep=":")
    for keys, directives in setupcfg_directives().items():
        value = get_nested(out, keys)
        print("keys:", *keys, "value:", value)
        if value and any(value.strip().startswith(f"{d}:") for d in directives):
            out = apply_nested(out, keys, split_directive)
    return out


def apply_value_processing(_orig: ConfigUpdater, out: C) -> C:
    transformations = value_processing()
    for name, section in out.items():
        if name not in ("metadata", "options"):
            continue
        for option in section:
            key = (name, option)
            out = apply_nested(out, key, transformations.get(key, split_comment))
    # Split entry-points
    for entrypoint in out.get("options.entry-points", {}):
        out = apply_nested(out, ("options.entry-points", entrypoint), split_kv_pairs)
    return out


def separate_subtables(_orig: Mapping, out: M) -> M:
    """Setuptools emulate nested sections (e.g.: ``options.extras_require``)"""
    sections = [k for k in out.keys() if k.startswith("options.")]
    for section in sections:
        value = out.pop(section)
        print(f"{section.split('.')=}", f"{value=}")
        out = set_nested(out, section.split("."), value)
    return out


def apply_renaming(_orig: Mapping, out: M) -> M:
    rules = pep621_renaming()
    for src, dest in rules.items():
        value = pop_nested(out, src, NOT_GIVEN)
        if value is not NOT_GIVEN:
            out = set_nested(out, dest, value)
    return out


def fix_license(_orig: Mapping, out: M) -> M:
    value = out.get("project", {}).get("license", None)
    if value and "file" in value:
        value.pop("text", None)  # these fields are mutually exclusive
    return out


def fix_dynamic(orig: Mapping, out: M) -> M:
    potential = ["version", "classifiers", "description"]
    project = out.setdefault("project", {})
    fields = [f for f in potential if isdirective(project.get(f, None))]
    extras: List[str] = []
    if "options" in orig and orig["options"].get("entry-points").startswith("file:"):
        fields.append("entry-points")
        extras = ["scripts", "gui-scripts"]
    if not fields:
        return out
    project.setdefault("dynamic", []).extend(fields + extras)
    dynamic = {f: project.pop(f) for f in fields}
    setuptools = out.setdefault("tool", {}).setdefault("setuptools", {})
    setuptools.setdefault("dynamic", {}).update(dynamic)
    return out


def fix_packages(_orig: Mapping, out: M) -> M:
    setuptools = out.setdefault("tool", {}).setdefault("setuptools", {})
    packages = setuptools.setdefault("packages", {})
    if "find-namespace" in packages and "find" in packages:
        value = packages["find-namespace"]
        find_namespace = value if value and isinstance(value, MutableMapping) else {}
        find_namespace.update(packages.pop("find"))
        packages["find-namespace"] = find_namespace
    return out


def post_process(orig: ConfigUpdater, out: C) -> C:
    transformations = [
        convert_directives,
        apply_value_processing,
        separate_subtables,
        apply_renaming,
        fix_license,
        fix_dynamic,
        fix_packages,
        # fix_setup_requires,
    ]
    return reduce(lambda acc, fn: fn(orig, acc), transformations, out)


def pre_process(cfg: ConfigUpdater) -> ConfigUpdater:
    """Normalise keys in ``setup.cfg``, by replacing aliases with cannonic names
    and replacing the snake case with kebab case.

    .. note:: Although setuptools recently deprecated kebab case in ``setup.cfg``
       ``pyproject.toml`` seems to use it as a convention, so this normalisation makes
       more sense for the translation.
    """
    # Normalise for the same convention as pyproject
    for section in cfg.iter_sections():
        section.name = convert_case(section.name)
        for option in section.iter_options():
            option.key = convert_case(option.key)
    # Normalise aliases
    for alias, cannonic in setupcfg_aliases().items():
        option = cfg.get("metadata", alias)
        if option:
            option.key = cannonic
    return cfg


# ---- Helpers ----


def convert_case(field: str) -> str:
    return field.lower().replace("_", "-")


def isdirective(value, valid=("file", "attr")) -> bool:
    return (
        isinstance(value, Mapping) and len(value) == 1 and next(value.keys()) in valid
    )
