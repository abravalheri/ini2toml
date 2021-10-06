import re
from collections.abc import Mapping, MutableMapping
from functools import partial, reduce
from itertools import chain
from textwrap import dedent
from typing import Dict, List, Optional, Tuple, TypeVar, Union

from configupdater import ConfigUpdater
from packaging.requirements import Requirement

from ..access import get_nested, pop_nested, set_nested
from ..toml_adapter import InlineTable, table
from ..transformations import (
    Transformer,
    coerce_bool,
    kebab_case,
    split_comment,
    split_kv_pairs,
    split_list,
)
from ..types import Profile, Transformation, Translator

M = TypeVar("M", bound=MutableMapping)

RenameRules = Dict[Tuple[str, ...], Union[Tuple[Union[str, int], ...], None]]
ProcessingRules = Dict[Tuple[str, ...], Transformation]

chain_iter = chain.from_iterable

# Functions that split values from comments and parse those values
split_list_comma = partial(split_list, sep=",", subsplit_dangling=False)
split_list_semi = partial(split_list, sep=";", subsplit_dangling=False)
split_hash_comment = partial(split_comment, comment_prefixes="#")  # avoid splitting `;`
split_bool = partial(split_comment, coerce_fn=coerce_bool)
split_kv_nocomments = partial(split_kv_pairs, comment_prefixes="")

SECTION_SPLITTER = re.compile(r"\.|:")
SETUPTOOLS_COMMAND_SECTIONS = (
    "alias",
    "bdist",
    "sdist",
    "build",
    "install",
    "develop",
    "dist_info",
    "egg_info",
)
SETUPTOOLS_SECTIONS = ("metadata", "options", *SETUPTOOLS_COMMAND_SECTIONS)


def activate(translator: Translator, transformer: Optional[Transformer] = None):
    profile = translator["setup.cfg"]
    plugin = SetuptoolsPEP621(transformer or Transformer())
    plugin.attach_to(profile)
    profile.help_text = plugin.__doc__ or ""


class SetuptoolsPEP621:
    """Convert settings to 'pyproject.toml' based on PEP 621"""

    TOML_TEMPLATE = """\
    [build-system]
    requires = ["setuptools", "wheel"]
    build-backend = "setuptools.build_meta"

    [project]
    """

    def __init__(self, transformer: Transformer):
        self._tr = transformer

    def attach_to(self, profile: Profile):
        profile.cfg_processors.insert(0, self.normalise_keys)
        profile.toml_processors.insert(0, self.pep621_transform)
        profile.toml_template = dedent(self.TOML_TEMPLATE)

    def setupcfg_aliases(self):
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

    def setupcfg_directives(self):
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

    def processing_rules(self) -> ProcessingRules:
        """Value type processing, as defined in:
        https://setuptools.readthedocs.io/en/stable/userguide/declarative_config.html
        """
        return {
            ("metadata", "classifiers"): split_list_comma,
            # ("metadata", "license_files",): split_list_comma,  # PEP621 => single file
            ("metadata", "keywords"): split_list_comma,
            ("metadata", "project-urls"): split_kv_nocomments,
            ("metadata", "provides"): split_list_comma,
            ("metadata", "requires"): split_list_comma,
            ("metadata", "obsoletes"): split_list_comma,
            ("metadata", "long-description-content-type"): split_hash_comment,
            ("options", "zip-safe"): split_bool,
            ("options", "setup-requires"): split_list_semi,
            ("options", "install-requires"): split_list_semi,
            ("options", "tests-require"): split_list_semi,
            ("options", "scripts"): split_list_comma,
            ("options", "eager-resources"): split_list_comma,
            ("options", "dependency-links"): split_list_comma,
            ("options", "include-package-data"): split_bool,
            ("options", "packages"): split_list_comma,
            ("options", "package-dir"): split_kv_pairs,
            ("options", "namespace-packages"): split_list_comma,
            ("options", "py-modules"): split_list_comma,
            ("options", "data-files"): split_kv_pairs,
            ("options", "packages", "find", "exclude"): split_list_comma,
        }
        # See also dynamic_processing_rules
        # Everything else should use split_comment

    def dynamic_processing_rules(self, doc: Mapping) -> ProcessingRules:
        """Dynamically create processing rules, such as :func:`value_processing` based on
        the existing document.
        """
        groups: Dict[Tuple[str, ...], Transformation] = {
            ("options", "entry-points"): split_kv_pairs,
            ("options", "extras-require"): split_list_comma,
        }
        return {(*p, k): fn for p, fn in groups.items() for k in get_nested(doc, p, ())}

    def pep621_renaming(self, _orig: Mapping, doc: M) -> M:
        """Renames that have a clear correspondence according to PEP 621.
        Rules are applied sequentially and therefore can interfere with the following
        ones. Please notice that renaming is applied after value processing.
        """
        # ---- Metadata according to PEP 621 ----
        metadata = doc.pop("metadata", {})
        #  url => urls.homepage
        #  download-url => urls.download
        #  project-urls => urls
        urls = {
            dest: metadata.pop(orig)
            for orig, dest in [("url", "Homepage"), ("download-url", "Download")]
            if orig in metadata
        }
        urls = {**metadata.pop("project-urls", {}), **urls}
        # author OR maintainer => author.name
        # author-email OR maintainer-email => author.email
        keys = ("author", "maintainer")
        names = chain_iter(metadata.pop(k, "").strip().split(",") for k in keys)
        emails = chain_iter(
            metadata.pop(f"{k}-email", "").strip().split(",") for k in keys
        )
        author = [{"name": n, "email": e} for n, e in zip(names, emails) if n]
        # long_description.file => readme.file
        # long_description => readme.text
        # long-description-content-type => readme.content-type
        readme = {}
        if "file" in metadata.get("long-description", {}):
            readme = {"file": metadata.pop("long-description")["file"]}
        elif "long-description" in metadata:
            readme = {"text": metadata.pop("long-description")}
        if "long-description-content-type" in metadata:
            readme["content-type"] = metadata.pop("long-description-content-type")
        if len(list(readme.keys())) == 1 and "file" in readme:
            readme = readme["file"]
        # license-files => license.file
        # license => license.text
        naming = {"license-files": "file", "license": "text"}
        license = {v: metadata.pop(k) for k, v in naming.items() if k in metadata}

        converted = {
            "author": author,
            "readme": readme,
            "license": license,
            "urls": urls,
        }
        metadata.update({k: v for k, v in converted.items() if v})

        # ---- Things in "options" that are covered by PEP 621 ----
        options = doc.pop("options", {})
        naming = {
            "python-requires": "requires-python",
            "install-requires": "dependencies",
            "extras-require": "optional-dependencies",
            "entry-points": "entry-points",
        }
        metadata.update({v: options.pop(k) for k, v in naming.items() if k in options})
        # "entry-points"."console-scripts" => "scripts"
        # "entry-points"."gui-scripts" => "gui-scripts"
        if "console-scripts" in metadata.get("entry-points", {}):
            metadata["scripts"] = metadata["entry-points"].pop("console-scripts")
        if "gui-scripts" in metadata.get("entry-points", {}):
            metadata["gui-scripts"] = metadata["entry-points"].pop("gui-scripts")
        if not metadata.get("entry-points", {}):
            metadata.pop("entry-points", None)

        # ---- setuptools metadata without correspondence in PEP 621 ----
        specific = ["platforms", "provides", "obsoletes"]
        options.update({k: metadata.pop(k) for k in specific if k in metadata})

        # ---- distutils/setuptools command specifics outside of "options" ----
        sections = list(doc.keys())
        extras = {
            k: doc.pop(k)
            for k in sections
            for p in SETUPTOOLS_COMMAND_SECTIONS
            if k.startswith(p) and k != "build-system"
        }
        options.update(extras)

        # ----

        if metadata:
            doc["project"] = metadata
        if options:
            tool = doc.setdefault("tool", {})
            tool["setuptools"] = options

        return doc

    def convert_directives(self, _orig: Mapping, out: M) -> M:
        split_directive = partial(split_kv_pairs, key_sep=":")
        for (section, option), directives in self.setupcfg_directives().items():
            value = out.get(section, {}).get(option, None)
            if not isinstance(value, str):
                continue
            if any(value.strip().startswith(f"{d}:") for d in directives):
                self._tr.apply(out[section], option, split_directive)
        return out

    def separate_subtables(self, _orig: Mapping, out: M) -> M:
        """Setuptools emulate nested sections (e.g.: ``options.extras_require``)"""
        sections = [k for k in out.keys() if k.startswith("options.") or ":" in k]
        for section in sections:
            value = out.pop(section)
            out = set_nested(out, SECTION_SPLITTER.split(section), value)
        return out

    def apply_value_processing(self, _orig: Mapping, out: M) -> M:
        default = {
            (name, option): split_comment
            for name, section in out.items()
            if name in ("metadata", "options")
            for option in section
        }
        fns: dict = {
            **default,
            **self.processing_rules(),
            **self.dynamic_processing_rules(out),
        }
        return reduce(lambda acc, x: self._tr.apply_nested(acc, *x), fns.items(), out)

    def fix_license(self, _orig: Mapping, out: M) -> M:
        value = out.get("project", {}).get("license", None)
        if value and "file" in value:
            value.pop("text", None)  # these fields are mutually exclusive
        return out

    def fix_dynamic(self, orig: Mapping, out: M) -> M:
        potential = ["version", "classifiers", "description"]
        project = out.setdefault("project", {})
        fields = [f for f in potential if isdirective(project.get(f, None))]
        extras: List[str] = []
        if "options" in orig and orig["options"].get("entry-points", "").startswith(
            "file:"
        ):
            fields.append("entry-points")
            extras = ["scripts", "gui-scripts"]
        if not fields:
            return out
        project.setdefault("dynamic", []).extend(fields + extras)
        dynamic = {f: project.pop(f) for f in fields}
        setuptools = out.setdefault("tool", {}).setdefault("setuptools", {})
        setuptools.setdefault("dynamic", {}).update(dynamic)
        return out

    def fix_packages(self, _orig: Mapping, out: M) -> M:
        if "tool" not in out or "packages" not in out["tool"].get("setuptools"):
            return out
        packages = out["tool"]["setuptools"]["packages"]
        if any(f"find{_}namespace" in packages for _ in "_-") and "find" in packages:
            value = packages.pop("find_namespace", packages.pop("find-namespace", None))
            find_namespace = packages.pop("find", {})
            find_namespace.update(value if value and isinstance(value, Mapping) else {})
            packages["find-namespace"] = find_namespace
            _packages_table_toml_workaround(out)
        return out

    def fix_setup_requires(self, _orig: Mapping, out: M) -> M:
        req = out.get("tool", {}).get("setuptools", {}).pop("setup-requires", [])
        build_req = out.setdefault("build-system", {}).setdefault("requires", [])
        existing = {Requirement(r).name: r for r in build_req}
        new = [(Requirement(r).name, r) for r in req]
        # Deduplication
        for name, dep in reversed(new):
            if name in existing:
                build_req.remove(existing[name])
            build_req.insert(0, dep)
        return out

    def ensure_pep518(self, _orig: Mapping, out: M) -> M:
        """PEP 518 specifies that any other tool adding configuration under
        ``pyproject.toml`` should use the ``tool`` table. This means that the only
        top-level keys are ``build-system``, ``project`` and ``tool``
        """
        N = len("tool:")
        allowed = ("build-system", "project", "tool")
        for top_level_key in list(out.keys()):
            key = top_level_key
            if any(top_level_key[:N] == p for p in ("tool:", "tool.")):
                key = top_level_key[N:]
            if top_level_key not in allowed:
                tool = out.setdefault("tool", {})
                tool[key] = out.pop(top_level_key)
        return out

    def cleanup(self, _orig: Mapping, out: M) -> M:
        possible_removals = [
            ("project",),
            ("tool", "setuptools", "packages"),
            ("tool", "setuptools"),
            ("tool",),
        ]
        for keys in possible_removals:
            if not get_nested(out, keys):
                pop_nested(out, keys)
        return out

    def pep621_transform(self, orig: Mapping, out: M) -> M:
        fns = [
            self.convert_directives,
            self.separate_subtables,
            self.apply_value_processing,
            self.pep621_renaming,
            self.fix_license,
            self.fix_dynamic,
            self.fix_packages,
            self.fix_setup_requires,
            self.ensure_pep518,
            self.cleanup,
        ]
        return reduce(lambda acc, fn: fn(orig, acc), fns, out)  # type: ignore

    def normalise_keys(self, cfg: ConfigUpdater) -> ConfigUpdater:
        """Normalise keys in ``setup.cfg``, by replacing aliases with cannonic names
        and replacing the snake case with kebab case.

        .. note:: Although setuptools recently deprecated kebab case in ``setup.cfg``
           ``pyproject.toml`` seems to use it as a convention, so this normalisation
           makes more sense for the translation.
        """
        # Normalise for the same convention as pyproject
        for section in cfg.iter_sections():
            if not any(section.name.startswith(s) for s in SETUPTOOLS_SECTIONS):
                continue
            section.name = kebab_case(section.name)
            for option in section.iter_options():
                option.key = kebab_case(option.key)
        # Normalise aliases
        if "metadata" not in cfg:
            return cfg
        for alias, cannonic in self.setupcfg_aliases().items():
            option = cfg.get("metadata", alias, None)
            if option:
                option.key = cannonic
        return cfg


# ---- Helpers ----


def isdirective(value, valid=("file", "attr")) -> bool:
    return (
        isinstance(value, Mapping)
        and len(value) == 1
        and next(iter(value.keys())) in valid
    )


def _packages_table_toml_workaround(out: M) -> M:
    packages = out.get("tool", {}).get("setuptools", {}).get("packages", {})
    if isinstance(packages, InlineTable):
        replacement = table()
        replacement.update(packages)
        out["tool"]["setuptools"]["packages"] = replacement

    return out
