import re
from collections.abc import Mapping
from functools import partial, reduce
from itertools import chain
from typing import Dict, List, Tuple, Type, TypeVar, Union, cast

from ..transformations import (
    apply,
    coerce_bool,
    kebab_case,
    remove_prefixes,
    split_comment,
    split_kv_pairs,
    split_list,
)
from ..types import CommentKey
from ..types import IntermediateRepr as IR
from ..types import Transformation, Translator
from .best_effort import BestEffort

M = TypeVar("M", bound=IR)

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


def activate(translator: Translator):
    plugin = SetuptoolsPEP621()
    profile = translator["setup.cfg"]
    profile.intermediate_processors += [plugin.normalise_keys, plugin.pep621_transform]
    profile.help_text = plugin.__doc__ or ""


class SetuptoolsPEP621:
    """Convert settings to 'pyproject.toml' based on PEP 621"""

    def __init__(self):
        self._be = BestEffort(key_sep="=")

    @staticmethod
    def template(ir_cls: Type[M] = IR) -> M:  # type: ignore
        return ir_cls(
            {
                "metadata": ir_cls(),  # NOTE: will be renamed later
                "build-system": ir_cls(
                    {
                        "requires": ["setuptools", "wheel"],
                        # ^ NOTE: the code ahead assumes no version
                        "build-backend": "setuptools.build_meta",
                    },
                ),
                "tool": ir_cls(),
            }
        )

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
            ("options.packages.find", "include"): split_list_comma,
            ("options.packages.find", "exclude"): split_list_comma,
            ("options.packages.find-namespace", "include"): split_list_comma,
            ("options.packages.find-namespace", "exclude"): split_list_comma,
        }
        # See also dynamic_processing_rules
        # Everything else should use split_comment

    def dynamic_processing_rules(self, doc: IR) -> ProcessingRules:
        """Dynamically create processing rules, such as :func:`value_processing` based on
        the existing document.
        """
        groups = {
            "options.extras-require": split_list_comma,
            "options.package-data": split_list_comma,
            "options.exclude-package-data": split_list_comma,
            # ----
            # "options.entry-points" => moved to project
            # console-scripts and gui-scripts already handled in
            # move_and_split_entrypoints
            "project:entry-points": split_kv_pairs,
        }
        return {
            (g, k): fn
            for g, fn in groups.items()
            for k in doc.get(g, ())
            if isinstance(k, str)
        }

    def merge_and_rename_urls(self, doc: M) -> M:
        #  url => urls.homepage
        #  download-url => urls.download
        #  project-urls => urls
        metadata = cast(IR, doc["metadata"])
        new_urls = (
            f"{dest} = {metadata.pop(orig)}"
            for orig, dest in [("url", "Homepage"), ("download-url", "Download")]
            if orig in metadata
        )
        urls = "\n".join(chain(new_urls, [metadata.get("project-urls", "")]))
        urls = urls.strip()
        if urls:
            keys = ("project-urls", "url", "download-url")
            metadata.replace_first_remove_others(keys, "urls", urls)
        return doc

    def merge_authors_maintainers_and_emails(self, doc: M) -> M:
        # author OR maintainer => author.name
        # author-email OR maintainer-email => author.email
        metadata: IR = doc["metadata"]
        author_ = split_comment(metadata.get("author", ""))
        maintainer_ = split_comment(metadata.get("maintainer", ""))
        names_ = (author_, maintainer_)
        names = chain_iter(n.value_or("").strip().split(",") for n in names_)
        a_email_ = split_comment(metadata.get("author-email", ""))
        m_email_ = split_comment(metadata.get("maintainer-email", ""))
        emails_ = (a_email_, m_email_)
        emails = chain_iter(n.value_or("").strip().split(",") for n in emails_)
        comments = [o.comment for o in chain(names_, emails_) if o.has_comment()]

        combined_ = {e: n for n, e in zip(names, emails) if n}  # deduplicate
        out = [{"name": n, "email": e} for e, n in combined_.items()]
        if out:
            keys = ("author", "maintainer", "author-email", "maintainer-email")
            i = metadata.replace_first_remove_others(keys, "author", out)
            for j, cmt in enumerate(comments):
                metadata.insert(j + i + 1, CommentKey(), cmt)
        return doc

    def merge_and_rename_long_description_and_content_type(self, doc: M) -> M:
        # long_description.file => readme.file
        # long_description => readme.text
        # long-description-content-type => readme.content-type
        metadata: IR = doc["metadata"]
        if "long-description" not in metadata:
            metadata.pop("long-description-content-type", None)
            return doc
        long_desc = metadata["long-description"].strip()
        readme: Dict[str, str] = {}
        if long_desc.startswith("file:"):
            readme = {"file": remove_prefixes(long_desc, ("file:",)).strip()}
        elif long_desc:
            readme = {"text": long_desc}
        if "long-description-content-type" in metadata:
            readme["content-type"] = metadata.pop("long-description-content-type")
        if len(list(readme.keys())) == 1 and "file" in readme:
            metadata["long-description"] = split_comment(readme["file"])
        else:
            readme_ = IR({k: split_comment(v) for k, v in readme.items()})
            metadata["long-description"] = readme_
        metadata.rename("long-description", "readme")
        return doc

    def merge_license_and_files(self, doc: M) -> M:
        # Prepare license before pep621_renaming
        # license-files => license.file
        # license => license.text
        metadata: IR = doc["metadata"]
        naming = {"license-files": "file", "license": "text"}
        items = [
            (v, split_comment(metadata.get(k)))
            for k, v in naming.items()
            if k in metadata
        ]
        if not metadata or not items:
            return doc
        # 'file' and 'text' are mutually exclusive in PEP 621
        license = IR(dict(items[:1]))
        metadata.replace_first_remove_others(list(naming.keys()), "license", license)
        return doc

    def move_and_split_entrypoints(self, doc: M) -> M:
        # This is part of pep621_renaming
        # "entry-points"."console-scripts" => "scripts"
        # "entry-points"."gui-scripts" => "gui-scripts"
        entrypoints: IR = doc.get("options.entry-points", IR())
        if not entrypoints:
            return doc
        doc.rename("options.entry-points", "project:entry-points")
        # ^ use `:` to guarantee it is split later
        keys = (k for k in ("gui-scripts", "console-scripts") if k in entrypoints)
        for key in keys:
            scripts = split_kv_pairs(entrypoints.pop(key))
            doc.append(f"project:{key.replace('console-', '')}", scripts)
        if not entrypoints:
            doc.pop("options.entry-points")
        return doc

    def add_options_in_pep621(self, doc: M) -> M:
        # ---- Things in "options" that are covered by PEP 621 ----
        naming = {
            "python-requires": "requires-python",
            "install-requires": "dependencies",
            "extras-require": "optional-dependencies",
            "entry-points": "entry-points",
        }
        metadata, options = doc["metadata"], doc["options"]
        metadata.update({v: options.pop(k) for k, v in naming.items() if k in options})
        return doc

    def remove_metadata_not_in_pep621(self, doc: M) -> M:
        # ---- setuptools metadata without correspondence in PEP 621 ----
        specific = ["platforms", "provides", "obsoletes"]
        metadata, options = doc["metadata"], doc["options"]
        options.update({k: metadata.pop(k) for k in specific if k in metadata})
        return doc

    def parse_setup_py_command_options(self, doc: M) -> M:
        # ---- distutils/setuptools command specifics outside of "options" ----
        sections = list(doc.keys())
        extras = {
            k: self._be.apply_best_effort_to_section(doc[k])
            for k in sections
            for p in SETUPTOOLS_COMMAND_SECTIONS
            if k.startswith(p) and k != "build-system"
        }
        doc["options"].update(extras)
        return doc

    def convert_directives(self, out: M) -> M:
        for (section, option), directives in self.setupcfg_directives().items():
            value = out.get(section, {}).get(option, None)
            if isinstance(value, str) and any(
                value.strip().startswith(f"{d}:") for d in directives
            ):
                out[section][option] = split_kv_pairs(value, key_sep=":")
        return out

    def separate_subtables(self, out: M) -> M:
        """Setuptools emulate nested sections (e.g.: ``options.extras_require``)"""
        sections = [
            k
            for k in out.keys()
            if isinstance(k, str) and (k.startswith("options.") or ":" in k)
        ]
        for section in sections:
            new_key = SECTION_SPLITTER.split(section)
            if section.startswith("options."):
                new_key = ["tool", "setuptools", *new_key[1:]]
            out.rename(section, tuple(new_key))
        return out

    def apply_value_processing(self, doc: M) -> M:
        default = {
            (name, option): split_comment
            for name, section in doc.items()
            if name in ("metadata", "options")
            for option in section
        }
        transformations: dict = {
            **default,
            **self.processing_rules(),
            **self.dynamic_processing_rules(doc),
        }
        for (section, option), fn in transformations.items():
            value = doc.get(section, {}).get(option, None)
            if value is not None:
                doc[section][option] = fn(value)
        return doc

    def fix_dynamic(self, doc: M) -> M:
        potential = ["version", "classifiers", "description"]
        metadata, options = doc["metadata"], doc["options"]

        fields = [f for f in potential if isdirective(metadata.get(f, None))]
        extras: List[str] = []

        ep = options.pop("entry-points", "")
        if ep.startswith("file:"):
            metadata["entry-points"] = {"file": remove_prefixes(ep, ("file:"))}
            fields.append("entry-points")
            extras = ["scripts", "gui-scripts"]
        if not fields:
            return doc
        metadata.setdefault("dynamic", []).extend(fields + extras)
        dynamic = {f: metadata.pop(f) for f in fields}
        doc.setdefault("options.dynamic", {}).update(dynamic)
        return doc

    def fix_packages(self, doc: M) -> M:
        options = doc["options"]
        packages = options.get("packages", "").strip()
        if not packages:
            return doc
        prefixes = ["find", *[f"find{_}namespace" for _ in "_-"]]
        prefix = next((p for p in prefixes if packages.startswith(f"{p}:")), None)
        if not prefix:
            return doc
        if "options.packages.find" not in doc:
            options["packages"] = split_kv_pairs(packages, key_sep=":")
            return doc
        options.pop("packages")
        prefix = prefix.replace("_", "-")
        doc.rename("options.packages.find", f"options.packages.{prefix}")
        return doc

    def fix_setup_requires(self, doc: M) -> M:
        """Add mandatory dependencies if they are missing"""
        options = doc["options"]
        requirements = options.get("setup-requires", "")
        if not requirements:
            return doc
        req = requirements.splitlines()
        if len(req) > 1:
            joiner = "\n"
        else:
            joiner = "; "
            req = req[0].split(";")
        build_req = doc["build-system"]["requires"]
        req.extend(d for d in build_req if d not in requirements)
        options["setup-requires"] = joiner.join(req)
        return doc

    def move_setup_requires(self, doc: M) -> M:
        options = doc["options"]
        if "setup-requires" in options:
            doc["build-system"]["requires"] = options.pop("setup-requires")
        return doc

    def ensure_pep518(self, doc: M) -> M:
        """PEP 518 specifies that any other tool adding configuration under
        ``pyproject.toml`` should use the ``tool`` table. This means that the only
        top-level keys are ``build-system``, ``project`` and ``tool``
        """
        N = len("tool:")
        allowed = ("build-system", "project", "tool", "metadata", "options")
        for top_level_key in list(doc.keys()):
            key = top_level_key
            if any(top_level_key[:N] == p for p in ("tool:", "tool.")):
                key = top_level_key[N:]
            if top_level_key not in allowed:
                doc.rename(top_level_key, ("tool", key))
        return doc

    def pep621_transform(self, doc: M) -> M:
        """Rules are applied sequentially and therefore can interfere with the following
        ones. Please notice that renaming is applied after value processing.
        """
        transformations = [
            # --- transformations mainly focusing on PEP 621 ---
            self.merge_and_rename_urls,
            self.merge_authors_maintainers_and_emails,
            self.merge_license_and_files,
            self.merge_and_rename_long_description_and_content_type,
            self.move_and_split_entrypoints,
            # --- General fixes
            self.add_options_in_pep621,
            self.remove_metadata_not_in_pep621,
            self.fix_dynamic,
            self.fix_packages,
            self.fix_setup_requires,
            # --- value processing and type changes ---
            self.convert_directives,
            self.apply_value_processing,
            self.parse_setup_py_command_options,
            # --- steps that depend on the values being processed ---
            self.move_setup_requires,
            # --- final steps ---
            self.ensure_pep518,
            self.separate_subtables,
        ]
        out = self.template(doc.__class__)  # type: ignore
        out.update(doc)
        out.setdefault("metadata", IR())
        out.setdefault("options", IR())
        out = reduce(apply, transformations, out)
        out.rename("metadata", "project", ignore_missing=True)
        out.rename("options", ("tool", "setuptools"), ignore_missing=True)
        return out

    def normalise_keys(self, cfg: M) -> M:
        """Normalise keys in ``setup.cfg``, by replacing aliases with cannonic names
        and replacing the snake case with kebab case.

        .. note:: Although setuptools recently deprecated kebab case in ``setup.cfg``
           ``pyproject.toml`` seems to use it as a convention, so this normalisation
           makes more sense for the translation.
        """
        # Normalise for the same convention as pyproject
        for i in range(len(cfg.order)):
            section_name = cfg.order[i]
            if not isinstance(section_name, str):
                continue
            if not any(section_name.startswith(s) for s in SETUPTOOLS_SECTIONS):
                continue
            section = cfg[section_name]
            cfg.rename(section_name, kebab_case(section_name))
            for j in range(len(section.order)):
                option_name = section.order[j]
                if not isinstance(option_name, str):
                    continue
                section.rename(option_name, kebab_case(option_name))
        # Normalise aliases
        metadata = cfg.get("metadata")
        if not metadata:
            return cfg
        for alias, cannonic in self.setupcfg_aliases().items():
            if alias in metadata:
                metadata.rename(alias, cannonic)
        return cfg


# ---- Helpers ----


def isdirective(value, valid=("file", "attr")) -> bool:
    return (
        isinstance(value, Mapping)
        and len(value) == 1
        and next(iter(value.keys())) in valid
    )


# def _packages_table_toml_workaround(out: M) -> M:
#     pkg = out.get("tool", {}).get("setuptools", {}).get("packages", {})
#     if (
#         isinstance(pkg, InlineTable)
#         and cast(Mapping, pkg).get("find")
#         or cast(Mapping, pkg).get("find-namespace")
#     ):
#         replacement = table()
#         cast(MutableMapping, replacement).update(pkg)
#         out["tool"]["setuptools"]["packages"] = replacement

#     return out
