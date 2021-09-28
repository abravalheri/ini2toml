from functools import reduce
from typing import Dict, List, Optional, Union, cast

from configupdater import Comment, ConfigUpdater, Option, Section, Space

from . import types  # Structural/Abstract types
from .extensions import list_from_entry_points as list_all_extensions
from .profile import Profile
from .toml_adapter import Item, Table, TOMLDocument, comment, dumps, loads, nl, table

TOMLContainer = Union[TOMLDocument, Table]


class Translator:
    profiles: Dict[str, types.Profile]
    extensions: List[types.Extension]

    def __init__(
        self,
        profiles: Optional[Dict[str, types.Profile]] = None,
        extensions: Optional[List[types.Extension]] = None,
        cfg_parser_opts: Optional[dict] = None,
    ):
        self.profiles = {} if profiles is None else profiles
        self.extensions = list_all_extensions() if extensions is None else extensions
        self.cfg_parser_opts = cfg_parser_opts or {}

        for activate in self.extensions:
            activate(self)

    def __getitem__(self, profile_name: str) -> types.Profile:
        if profile_name not in self.profiles:
            profile = Profile(profile_name)
            if self.cfg_parser_opts:
                profile = profile.replace(cfg_parser_opts=self.cfg_parser_opts)
            self.profiles[profile_name] = profile
        return self.profiles[profile_name]

    def translate(self, cfg: str, profile_name: str) -> str:
        if profile_name not in self.profiles:
            raise UndefinedProfile(profile_name)

        profile = self[profile_name]
        cfg = reduce(lambda acc, fn: fn(acc), profile.pre_processors, cfg)
        updater = ConfigUpdater(**profile.cfg_parser_opts).read_string(cfg)
        updater = reduce(lambda acc, fn: fn(acc), profile.cfg_processors, updater)
        doc = loads(profile.toml_template)
        translate_cfg(doc, updater)
        doc = reduce(lambda acc, fn: fn(updater, acc), profile.toml_processors, doc)
        toml = dumps(cast(dict, doc)).strip()
        # TODO: atoml/tomlkit is always appending a newline at the end of the document
        #       when a section is replaced (even if it exists before), so we need to
        #       strip()
        return reduce(lambda acc, fn: fn(acc), profile.post_processors, toml)


def translate_cfg(out: TOMLDocument, cfg: ConfigUpdater):
    parser_opts = getattr(cfg, "_parser_opts", {})  # TODO: private attr
    for block in cfg.iter_blocks():
        if isinstance(block, Section):
            translate_section(out, block, parser_opts)
        elif isinstance(block, Comment):
            translate_comment(out, block, parser_opts)
        elif isinstance(block, Space):
            translate_space(out, block, parser_opts)
        else:  # pragma: no cover -- not supposed to happen
            raise InvalidCfgBlock(block)


def translate_section(doc: TOMLDocument, item: Section, parser_opts: dict):
    out = table()
    # Inline comment
    cmt = getattr(item, "_raw_comment", "")  # TODO: private attr
    prefixes = "".join(parser_opts.get("comment_prefixes", "#;"))
    cmt = cmt.strip().lstrip(prefixes).strip()
    if cmt:
        cast(Item, out).comment(cmt.strip().lstrip(prefixes).strip())
    # Children
    for block in item.iter_blocks():
        if isinstance(block, Option):
            translate_option(out, block, parser_opts)
        elif isinstance(block, Comment):
            translate_comment(out, block, parser_opts)
        elif isinstance(block, Space):
            translate_space(out, block, parser_opts)
        else:  # pragma: no cover -- not supposed to happen
            raise InvalidCfgBlock(block)
    doc[item.name] = out


def translate_option(container: Table, item: Option, parser_opts: dict):
    value = item.value
    prefixes = [p for p in parser_opts.get("comment_prefixes", "#;") if p in value]

    # We just process inline comments for single line options
    if not prefixes or len(value.splitlines()) > 1:
        container[item.key] = item.value
        return

    prefix = prefixes[0]  # We can only analyse one...
    value, cmt = (p.strip() for p in value.split(prefix, maxsplit=1))
    container[item.key] = value
    container[item.key].comment(cmt.strip().lstrip(prefix).strip())


def translate_comment(container: TOMLContainer, item: Comment, parser_opts: dict):
    prefixes = "".join(parser_opts.get("comment_prefixes", "#;"))
    for line in str(item).splitlines():
        container.add(comment(str(line).strip().lstrip(prefixes).strip()))


def translate_space(container: TOMLContainer, item: Space, _parser_opts: dict):
    for _ in str(item).splitlines():
        container.add(nl())


class InvalidCfgBlock(ValueError):  # pragma: no cover -- not supposed to happen
    """Something is wrong with the provided CFG AST, the given block is not valid."""

    def __init__(self, block):
        super().__init__(f"{block.__class__}: {block}", {"block_object": block})


class UndefinedProfile(ValueError):
    """The given profile is not registered with ``cfg2toml``.
    Are you sure you have the right extensions installed and loaded?
    """
