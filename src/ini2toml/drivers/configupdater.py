from types import MappingProxyType
from typing import Mapping

from configupdater import Comment, ConfigUpdater, Option, Section, Space

from ..errors import InvalidCfgBlock
from ..transformations import remove_prefixes
from ..types import CommentKey, IntermediateRepr, WhitespaceKey

EMPTY: Mapping = MappingProxyType({})
COMMENT_PREFIXES = ("#", ";")


def parse(text: str, opts: Mapping = EMPTY) -> IntermediateRepr:
    cfg = ConfigUpdater(**opts).read_string(text)
    irepr = IntermediateRepr()

    for block in cfg.iter_blocks():
        if isinstance(block, Section):
            translate_section(irepr, block, opts)
        elif isinstance(block, Comment):
            translate_comment(irepr, block, opts)
        elif isinstance(block, Space):
            translate_space(irepr, block, opts)
        else:  # pragma: no cover -- not supposed to happen
            raise InvalidCfgBlock(block)

    return irepr


def translate_section(irepr: IntermediateRepr, item: Section, opts: Mapping):
    out = IntermediateRepr()
    # Inline comment
    cmt = getattr(item, "_raw_comment", "")  # TODO: private attr
    cmt = remove_prefixes(cmt, opts.get("comment_prefixes", COMMENT_PREFIXES))
    if cmt:
        out.inline_comment = cmt
    # Children
    for block in item.iter_blocks():
        if isinstance(block, Option):
            translate_option(out, block, opts)
        elif isinstance(block, Comment):
            translate_comment(out, block, opts)
        elif isinstance(block, Space):
            translate_space(out, block, opts)
        else:  # pragma: no cover -- not supposed to happen
            raise InvalidCfgBlock(block)
    irepr.append(item.name, out)


def translate_option(irepr: IntermediateRepr, item: Option, _opts: Mapping):
    irepr.append(item.key, item.value)


def translate_comment(irepr: IntermediateRepr, item: Comment, opts: Mapping):
    prefixes = opts.get("comment_prefixes", COMMENT_PREFIXES)
    for line in str(item).splitlines():
        irepr.append(CommentKey(), remove_prefixes(line, prefixes))


def translate_space(irepr: IntermediateRepr, item: Space, _opts: Mapping):
    for line in str(item).splitlines(keepends=True):
        irepr.append(WhitespaceKey(), line)
