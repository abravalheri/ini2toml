from dataclasses import dataclass, field, replace
from typing import List

from .types import PostProcessor, PreProcessor


@dataclass
class Profile:
    name: str
    pre_processors: List[PreProcessor] = field(default_factory=list)
    post_processors: List[PostProcessor] = field(default_factory=list)
    cfg_parser_opts: dict = field(default_factory=dict)
    toml_template: str = ""

    replace = replace
