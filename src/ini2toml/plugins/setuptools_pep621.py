import logging
import re
from functools import partial, reduce
from itertools import chain
from typing import Dict, List, Mapping, Sequence, Set, Tuple, Type, TypeVar, Union, cast

from ..transformations import (
    apply,
    coerce_bool,
    deprecated,
    kebab_case,
    remove_prefixes,
    split_comment,
    split_kv_pairs,
    split_list,
)
from ..types import CommentKey, HiddenKey
from ..types import IntermediateRepr as IR
from ..types import Transformation, Translator, WhitespaceKey
from .best_effort import BestEffort

try:
    from setuptools._distutils import command as distutils_commands
except ImportError:  # pragma: no cover
    from distutils import command as distutils_commands

R = TypeVar("R", bound=IR)

RenameRules = Dict[Tuple[str, ...], Union[Tuple[Union[str, int], ...], None]]
ProcessingRules = Dict[Tuple[str, ...], Transformation]


_logger = logging.getLogger(__name__)

chain_iter = chain.from_iterable

# Functions that split values from comments and parse those values
split_directive = partial(split_kv_pairs, key_sep=":")
split_list_comma = partial(split_list, sep=",", subsplit_dangling=False)
split_list_semi = partial(split_list, sep=";", subsplit_dangling=False)
split_hash_comment = partial(split_comment, comment_prefixes="#")  # avoid splitting `;`
split_bool = partial(split_comment, coerce_fn=coerce_bool)
split_kv_nocomments = partial(split_kv_pairs, comment_prefixes="")
split_kv_of_lists = partial(split_kv_pairs, coerce_fn=split_list_comma)

SECTION_SPLITTER = re.compile(r"\.|:")
SETUPTOOLS_SECTIONS = ("metadata", "options")
SKIP_CHILD_NORMALISATION = ("options.entry_points",)
COMMAND_SECTIONS = (
    "global",
    "alias",
    "install",
    "develop",
    "sdist",
    "bdist",
    "bdist_wheel",
    *getattr(distutils_commands, "__all__", []),
)


def activate(translator: Translator):
    plugin = SetuptoolsPEP621()
    profile = translator["setup.cfg"]
    profile.intermediate_processors += [plugin.normalise_keys, plugin.pep621_transform]
    profile.help_text = plugin.__doc__ or ""


class SetuptoolsPEP621:
    """Convert settings to 'pyproject.toml' based on PEP 621"""

    BUILD_REQUIRES = ("setuptools", "wheel")

    def __init__(self):
        self._be = BestEffort(key_sep="=")

    @classmethod
    def template(
        cls,
        ir_cls: Type[R] = IR,  # type: ignore
        build_requires: Sequence[str] = (),
    ) -> R:
        build_system = {
            "requires": [*(build_requires or cls.BUILD_REQUIRES)],
            # ^ NOTE: the code ahead assumes no version
            "build-backend": "setuptools.build_meta",
        }
        tpl = {
            "metadata": ir_cls(),  # NOTE: will be renamed later
            "build-system": ir_cls(build_system),  # type: ignore
            "tool": ir_cls(),
        }
        return ir_cls(tpl)  # type: ignore

    def setupcfg_aliases(self):
        """``setup.cfg`` aliases as defined in:
        https://setuptools.pypa.io/en/stable/userguide/declarative_config.html
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
        https://setuptools.pypa.io/en/stable/userguide/declarative_config.html
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
        https://setuptools.pypa.io/en/stable/userguide/declarative_config.html
        """
        return {
            ("metadata", "classifiers"): split_list_comma,
            # => ("metadata", "license_files",): in PEP621 should be a single file
            ("metadata", "keywords"): split_list_comma,
            # => ("metadata", "project-urls") => merge_and_rename_urls
            # ("metadata", "long-description-content-type") =>
            #     merge_and_rename_long_description_and_content_type
            # ---- the following options are originally part of `metadata`,
            #      but we move it to "options" because they are not part of PEP 621
            ("options", "provides"): split_list_comma,
            ("options", "requires"): split_list_comma,
            ("options", "obsoletes"): split_list_comma,
            ("options", "platforms"): split_list_comma,
            # ----
            ("options", "zip-safe"): split_bool,
            ("options", "setup-requires"): split_list_semi,
            ("options", "install-requires"): split_list_semi,
            ("options", "tests-require"): split_list_semi,
            ("options", "script-files"): split_list_comma,
            # ^ --> We rename scripts to script-files
            ("options", "eager-resources"): split_list_comma,
            ("options", "dependency-links"): split_list_comma,
            ("options", "include-package-data"): split_bool,
            ("options", "packages"): split_list_comma,
            ("options", "package-dir"): split_kv_pairs,
            ("options", "namespace-packages"): split_list_comma,
            ("options", "py-modules"): split_list_comma,
            ("options", "data-files"): deprecated("data-files", split_kv_of_lists),
            ("options.packages.find", "include"): split_list_comma,
            ("options.packages.find", "exclude"): split_list_comma,
            ("options.packages.find-namespace", "include"): split_list_comma,
            ("options.packages.find-namespace", "exclude"): split_list_comma,
        }
        # See also dependent_processing_rules
        # Everything else should use split_comment

    def dependent_processing_rules(self, doc: IR) -> ProcessingRules:
        """Dynamically create processing rules, such as :func:`value_processing` based
        on the existing document.
        """
        groups: Mapping[str, Transformation] = {
            "options.extras-require": split_list_semi,
            "options.package-data": split_list_comma,
            "options.exclude-package-data": split_list_comma,
            "options.data-files": split_list_comma,
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

    def merge_and_rename_urls(self, doc: R) -> R:
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
            urls_kv = split_kv_nocomments(urls)
            keys = ("project-urls", "url", "download-url")
            metadata.replace_first_remove_others(keys, "urls", urls_kv)
        return doc

    def merge_authors_maintainers_and_emails(self, doc: R) -> R:
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

    def merge_and_rename_long_description_and_content_type(self, doc: R) -> R:
        # long_description.file => readme.file
        # long_description => readme.text
        # long-description-content-type => readme.content-type
        metadata: IR = doc["metadata"]
        if "long-description" not in metadata:
            metadata.pop("long-description-content-type", None)
            return doc
        long_desc = metadata["long-description"].strip()
        readme: dict = {}
        if long_desc.startswith("file:"):
            readme = {"file": remove_prefixes(long_desc, ("file:",)).strip()}
        elif long_desc:
            readme = {"text": long_desc}
        content_type = metadata.pop("long-description-content-type", None)
        if content_type:
            readme["content-type"] = split_hash_comment(content_type)
        if len(list(readme.keys())) == 1 and "file" in readme:
            metadata["long-description"] = split_comment(readme["file"])
        else:
            readme_ = IR({k: split_comment(v) for k, v in readme.items()})
            metadata["long-description"] = readme_
        metadata.rename("long-description", "readme")
        return doc

    def merge_license_and_files(self, doc: R) -> R:
        # Prepare license before pep621_renaming
        # license-files => license.file
        # license => license.text
        metadata: IR = doc["metadata"]
        naming = {"license-files": "file", "license": "text"}
        items = [
            (v, split_comment(metadata[k])) for k, v in naming.items() if k in metadata
        ]
        if not metadata or not items:
            return doc
        # 'file' and 'text' are mutually exclusive in PEP 621
        license = IR(dict(items[:1]))
        metadata.replace_first_remove_others(list(naming.keys()), "license", license)
        return doc

    def move_and_split_entrypoints(self, doc: R) -> R:
        # This is part of pep621_renaming
        # "entry-points"."console-scripts" => "scripts"
        # "entry-points"."gui-scripts" => "gui-scripts"
        entrypoints: IR = doc.get("options.entry-points", IR())
        if not entrypoints:
            return doc
        doc.rename("options.entry-points", "project:entry-points")
        # ^ use `:` to guarantee it is split later
        script_keys = ["console-scripts", "gui-scripts"]
        script_keys += [k.replace("-", "_") for k in script_keys]
        keys = (k for k in script_keys if k in entrypoints)
        for key in keys:
            scripts = split_kv_pairs(entrypoints.pop(key)).to_ir()
            new_key = key.replace("_", "-").replace("console-", "")
            doc.append(f"project:{new_key}", scripts)
        if not entrypoints or all(isinstance(k, WhitespaceKey) for k in entrypoints):
            doc.pop("project:entry-points")
        return doc

    def move_options_missing_in_pep621(self, doc: R) -> R:
        # ---- Things in "options" that are covered by PEP 621 ----
        # First we handle simple options
        naming = {
            "python-requires": "requires-python",
            "install-requires": "dependencies",
            "entry-points": "entry-points",
        }
        metadata, options = doc["metadata"], doc["options"]
        metadata.update({v: options.pop(k) for k, v in naming.items() if k in options})

        # Then we handle entire sections:
        naming = {"extras-require": "optional-dependencies"}
        for src, target in naming.items():
            doc.rename(f"options.{src}", f"project:{target}", ignore_missing=True)
        return doc

    def rename_script_files(self, doc: R) -> R:
        # setuptools define a ``options.scripts`` parameters that refer to
        # script files, not created via enty-points
        # To avoid confution with PEP621 scripts (generated via entry-points)
        # let's rename this field to `script-files`
        doc["options"].rename("scripts", "script-files", ignore_missing=True)
        return doc

    def remove_metadata_not_in_pep621(self, doc: R) -> R:
        # ---- setuptools metadata without correspondence in PEP 621 ----
        specific = ["platforms", "provides", "obsoletes"]
        metadata, options = doc["metadata"], doc["options"]
        options.update({k: metadata.pop(k) for k in specific if k in metadata})
        return doc

    def parse_setup_py_command_options(self, doc: R) -> R:
        # ---- distutils/setuptools command specifics outside of "options" ----
        sections = list(doc.keys())
        commands = _distutils_commands()
        for k in sections:
            if isinstance(k, str) and k in commands:
                section = self._be.apply_best_effort_to_section(doc[k])
                for option in section:
                    if isinstance(option, str):
                        section.rename(option, self.normalise_key(option))
                doc[k] = section
                doc.rename(k, ("distutils", k))
        return doc

    def convert_directives(self, out: R) -> R:
        for (section, option), directives in self.setupcfg_directives().items():
            value = out.get(section, {}).get(option, None)
            if isinstance(value, str) and any(
                value.strip().startswith(f"{d}:") for d in directives
            ):
                out[section][option] = split_directive(value)
        return out

    def split_subtables(self, out: R) -> R:
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

    def apply_value_processing(self, doc: R) -> R:
        default = {
            (name, option): split_comment
            for name, section in doc.items()
            if name in ("metadata", "options")
            for option in section
            if isinstance(option, (str, tuple))
        }
        transformations: dict = {
            **default,
            **self.processing_rules(),
            **self.dependent_processing_rules(doc),
        }
        for (section, option), fn in transformations.items():
            value = doc.get(section, {}).get(option, None)
            if value is not None:
                doc[section][option] = fn(value)
        return doc

    def fix_dynamic(self, doc: R) -> R:
        potential = ["version", "classifiers", "description"]
        metadata, options = doc["metadata"], doc["options"]

        fields = [f for f in potential if isdirective(metadata.get(f, None))]
        dynamic = {f: split_directive(metadata.pop(f, None)) for f in fields}
        if "version" not in metadata and "version" not in dynamic:
            msg = (
                "No `version` was found in `[metadata]`, `ini2toml` will assume it is "
                "defined by tools like `setuptools-scm` or in `setup.py`. "
                "Automatically adding it to `dynamic` (in accordance with PEP 621)"
            )
            _logger.debug(msg)
            fields.insert(0, "version")

        extras: List[str] = []
        ep = options.pop("entry-points", None)
        if isdirective(ep, valid=("file",)):
            fields.append("entry-points")
            dynamic["entry-points"] = split_directive(ep)
            extras = ["scripts", "gui-scripts"]
        if not fields:
            return doc
        metadata.setdefault("dynamic", []).extend(fields + extras)

        if dynamic:
            doc.setdefault("options.dynamic", IR()).update(dynamic)
            # ^ later `options.dynamic` is converted to `tool.setuptools.dynamic`
        return doc

    def fix_packages(self, doc: R) -> R:
        options = doc["options"]
        packages = options.get("packages", "").strip()
        if not packages:
            return doc
        prefixes = ["find", *[f"find{_}namespace" for _ in "_-"]]
        prefix = next((p for p in prefixes if packages.startswith(f"{p}:")), None)
        if not prefix:
            return doc
        kebab_prefix = prefix.replace("_", "-")
        options["packages"] = {kebab_prefix: {}}
        if "options.packages.find" in doc:
            options.pop("packages")
            doc.rename("options.packages.find", f"options.packages.{kebab_prefix}")
        return doc

    def fix_setup_requires(self, doc: R) -> R:
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

    def move_setup_requires(self, doc: R) -> R:
        options = doc["options"]
        if "setup-requires" in options:
            doc["build-system"]["requires"] = options.pop("setup-requires")
        return doc

    def ensure_pep518(self, doc: R) -> R:
        """PEP 518 specifies that any other tool adding configuration under
        ``pyproject.toml`` should use the ``tool`` table. This means that the only
        top-level keys are ``build-system``, ``project`` and ``tool``
        """
        allowed = ("build-system", "project", "tool", "metadata", "options")
        allowed_prefixes = ("options.", "project:")
        for k in list(doc.keys()):
            key = k
            rest: Sequence = ()
            if isinstance(k, tuple):
                key, *rest = k
            if isinstance(key, HiddenKey):
                continue
            if not (key in allowed or any(key.startswith(p) for p in allowed_prefixes)):
                doc.rename(k, ("tool", key, *rest))
        return doc

    def pep621_transform(self, doc: R) -> R:
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
            self.rename_script_files,
            self.remove_metadata_not_in_pep621,
            self.fix_packages,
            self.fix_setup_requires,
            self.fix_dynamic,
            # --- value processing and type changes ---
            self.convert_directives,
            self.apply_value_processing,
            self.parse_setup_py_command_options,
            # --- steps that depend on the values being processed ---
            self.move_setup_requires,
            self.move_options_missing_in_pep621,
            # --- final steps ---
            self.split_subtables,
            self.ensure_pep518,
        ]
        out = self.template(doc.__class__)
        out.update(doc)
        out.setdefault("metadata", IR())
        out.setdefault("options", IR())
        out = reduce(apply, transformations, out)
        out.rename("metadata", "project", ignore_missing=True)
        out.rename("options", ("tool", "setuptools"), ignore_missing=True)
        return out

    def normalise_keys(self, cfg: R) -> R:
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
            if any(section_name.startswith(s) for s in SKIP_CHILD_NORMALISATION):
                continue
            for j in range(len(section.order)):
                option_name = section.order[j]
                if not isinstance(option_name, str):
                    continue
                section.rename(option_name, self.normalise_key(option_name))
        # Normalise aliases
        metadata = cfg.get("metadata")
        if not metadata:
            return cfg
        for alias, cannonic in self.setupcfg_aliases().items():
            if alias in metadata:
                metadata.rename(alias, cannonic)
        return cfg

    def normalise_key(self, key: str) -> str:
        """Normalise a single key for option"""
        return kebab_case(key)


# ---- Helpers ----


def isdirective(value, valid=("file", "attr")) -> bool:
    return isinstance(value, str) and any(value.startswith(f"{p}:") for p in valid)


def _distutils_commands() -> Set[str]:
    try:
        from . import iterate_entry_points

        commands = [ep.name for ep in iterate_entry_points("distutils.commands")]
    except Exception:
        commands = []
    return {*commands, *COMMAND_SECTIONS}
