from dataclasses import dataclass, field, replace
from typing import List

from .types import CFGProcessor, TextProcessor, TOMLProcessor


@dataclass
class Profile:
    name: str
    help_text: str = ""
    pre_processors: List[TextProcessor] = field(default_factory=list)
    cfg_processors: List[CFGProcessor] = field(default_factory=list)
    toml_processors: List[TOMLProcessor] = field(default_factory=list)
    post_processors: List[TextProcessor] = field(default_factory=list)
    cfg_parser_opts: dict = field(default_factory=dict)
    toml_template: str = ""

    replace = replace
